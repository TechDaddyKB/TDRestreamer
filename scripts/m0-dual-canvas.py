"""Real two-canvas OBS -> MediaMTX -> RTSP -> FFmpeg -> enhanced RTMP fixture.

Synthetic local configuration only: never Twitch negotiation or platform evidence.
"""

import array
import hashlib
import json
import math
import os
import secrets
import shutil
import signal
import socket
import subprocess as sp
import sys
import time
from pathlib import Path

from m0_dual_checks import check_pixels, check_streams
from m0_flv_checks import check_flv_track_ids
from m0_protocols import require
from m0_twitch_config import local_obs_config

ROOT = Path(__file__).resolve().parents[1]
AITUM_SHA256 = "484c9663d00f3a2c2322600e6178833b7edde71019c2537b6eb35cf81e71e346"
SYSTEM_AITUM_SHA256 = "1e95048920211bff715fd14eace90da5e51e450b75db0dc0bc97c6ffe05676eb"
OUTPUT_PIPE = "pipe:1"
MODULES = (
    "obs-websocket",
    "obs-outputs",
    "obs-x264",
    "obs-ffmpeg",
    "image-source",
    "obs-transitions",
    "rtmp-services",
    "obs-filters",
    "text-freetype2",
)


class Lab:
    def __init__(self, work):
        self.work, self.processes, self.files = work, [], []

    def check_command(self, args):
        require(
            args
            and args[0]
            in {
                "ffmpeg",
                "ffprobe",
                "node",
                "Xvfb",
                "bwrap",
                "obs",
                str(ROOT / ".tools/mediamtx/mediamtx"),
            },
            "unexpected fixture executable",
        )

    def run(self, args, timeout=25):
        # Fixed executables and synthetic argv; no shell or user-supplied commands.
        self.check_command(args)
        p = sp.Popen(  # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit
            args, stdout=sp.PIPE, stderr=sp.PIPE, start_new_session=True, shell=False
        )
        try:
            out, err = p.communicate(timeout=timeout)
        except sp.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.communicate()
            raise RuntimeError(f"{Path(args[0]).name} timed out") from None
        if p.returncode:
            (self.work / f"{Path(args[0]).name}-failure.log").write_bytes(err)
        require(
            p.returncode == 0,
            f"{Path(args[0]).name} failed (status {p.returncode}); inspect private failure log",
        )
        return out

    def start(self, name, args, env=None):
        self.check_command(args)
        log = (self.work / f"{name}.log").open("w")
        self.files.append(log)
        # Audited: same allowlisted executable/synthetic argv boundary as run().
        p = sp.Popen(  # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit
            args,
            stdout=log,
            stderr=sp.STDOUT,
            cwd=self.work,
            env=env,
            start_new_session=True,
            shell=False,
        )
        self.processes.append(p)
        return p

    def port(self, port, process):
        for _ in range(150):
            require(process.poll() is None, f"process exited before port {port}")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError(f"port {port} did not open")

    def display_ready(self, process):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            require(process.poll() is None, "isolated X server exited")
            try:
                result = sp.run(
                    ["xdpyinfo", "-display", ":199"],
                    env=dict(os.environ, XAUTHORITY="/dev/null"),
                    stdout=sp.DEVNULL,
                    stderr=sp.DEVNULL,
                    timeout=1,
                    shell=False,
                    check=False,
                )
                if result.returncode == 0:
                    return
            except sp.TimeoutExpired:
                pass
            time.sleep(0.1)
        raise RuntimeError("isolated X display did not become ready")

    def close(self):
        for p in reversed(self.processes):
            if p.poll() is None:
                os.killpg(p.pid, signal.SIGTERM)
                try:
                    p.wait(timeout=5)
                except sp.TimeoutExpired:
                    os.killpg(p.pid, signal.SIGKILL)
                    p.wait()
        for log in self.files:
            log.close()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def loaded_system_modules(log_path):
    lines = log_path.read_text().splitlines()
    marker = "info:   Loaded Modules:"
    require(marker in lines, "OBS module list absent")
    start = lines.index(marker) + 1
    names = []
    for line in lines[start:]:
        if not line.startswith("info:     "):
            break
        name = line.removeprefix("info:     ")
        require(name.endswith(".so") and "/" not in name, "unexpected OBS module name")
        names.append(name)
    require("obs-nvenc.so" in names and "vertical-canvas.so" in names,
            "required OBS module absent")
    root = Path("/usr/lib/obs-plugins")
    return {name: digest(root / name) for name in sorted(set(names))}


def observe(lab, path, ladder=False):
    source = ["-rtsp_transport", "tcp", "-i", f"rtsp://127.0.0.1:18555/dual/{path}"]
    streams = json.loads(
        lab.run(["ffprobe", "-v", "error", *source, "-show_streams", "-of", "json"])
    )["streams"]
    (lab.work / f"{path}-streams.json").write_text(json.dumps(streams, indent=2) + "\n")
    expected = None
    if ladder:
        expected = [
            ("video", "h264", 640, 360),
            ("video", "h264", 284, 160),
            ("video", "h264", 720, 1280),
            ("video", "h264", 360, 640),
            ("audio", "aac", None, None),
            ("audio", "aac", None, None),
        ]
    check_streams(streams, expected)
    result = {
        "streams": [
            {k: s[k] for k in ("codec_type", "codec_name", "width", "height") if k in s}
            for s in streams
        ],
        "video_identity": [],
        "audio_identity": [],
    }
    video_colors = [(0, 0), (1, 0), (2, 2), (3, 2)] if ladder else [(0, 0), (1, 2)]
    for index, channel in video_colors:
        pixels = lab.run(
            [
                "ffmpeg",
                "-nostdin",
                "-v",
                "error",
                *source,
                "-map",
                f"0:v:{index}",
                "-vf",
                "crop=32:32:0:0,scale=1:1",
                "-frames:v",
                "10",
                "-pix_fmt",
                "rgb24",
                "-f",
                "rawvideo",
                OUTPUT_PIPE,
            ]
        )
        result["video_identity"].append(check_pixels(pixels, channel))
    for index, hz in [(0, 440), (1, 880)]:
        pcm = lab.run(
            [
                "ffmpeg",
                "-nostdin",
                "-v",
                "error",
                *source,
                "-map",
                f"0:a:{index}",
                "-t",
                "1",
                "-ar",
                "48000",
                "-ac",
                "1",
                "-f",
                "s16le",
                OUTPUT_PIPE,
            ]
        )
        samples = array.array("h", pcm)
        require(len(samples) >= 24000, "insufficient decoded audio")

        def power(frequency, samples=samples):
            return (
                abs(
                    sum(
                        v
                        * complex(
                            math.cos(2 * math.pi * frequency * n / 48000),
                            math.sin(2 * math.pi * frequency * n / 48000),
                        )
                        for n, v in enumerate(samples)
                    )
                )
                ** 2
            )

        ratio = power(hz) / max(1, power(880 if hz == 440 else 440))
        require(ratio > 100, f"wrong audio identity at index {index}")
        result["audio_identity"].append(
            {"expected_hz": hz, "opposite_power_ratio": round(ratio, 2)}
        )
    return result


def main():
    os.umask(0o077)
    ladder = "--twitch-ladder" in sys.argv
    require(
        set(sys.argv[1:]) <= {"--isolated", "--twitch-ladder"},
        "unknown fixture option",
    )
    if "--isolated" not in sys.argv:
        return sp.call(
            [
                "unshare",
                "--user",
                "--map-root-user",
                "--net",
                sys.executable,
                str(Path(__file__).resolve()),
                "--isolated",
                *(["--twitch-ladder"] if ladder else []),
            ],
            shell=False,
        )
    links = json.loads(sp.check_output(["ip", "-j", "link"]))
    routes = {
        family: json.loads(sp.check_output(["ip", "-j", family, "route"]))
        for family in ("-4", "-6")
    }
    require(
        [link["ifname"] for link in links] == ["lo"], "refusing non-loopback interfaces"
    )
    require(not any(routes.values()), "refusing external routes")
    sp.run(["ip", "link", "set", "lo", "up"], check=True)
    work = ROOT / "runtime" / ("m0-dual-" + secrets.token_hex(6))
    work.mkdir(parents=True, mode=0o700)
    lab = Lab(work)
    report = {
        "status": "running",
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "isolation": {
            "initial_interfaces": [x["ifname"] for x in links],
            "routes": routes,
        },
        "tests": {},
        "limitations": [
            (
                "Local synthetic configuration with sanitized account-negotiated encoder settings"
                if ladder else "Local synthetic configuration, not a Twitch negotiation response"
            ),
            (
                "No platform broadcasting, OAuth, cloud calls, preview or soak qualification"
                if ladder else "No platform broadcasting, OAuth, cloud calls, preview, GPU or soak qualification"
            ),
            "Standalone feasibility, not application integration; anonymous loopback fixture sinks",
            "Pixel/color, audio identity and local FLV headers only; no timing, motion, latency or A/V sync qualification",
            "FLV sample is not a capture of the later RTMP publisher connection",
        ],
    }
    try:
        pins = json.loads((ROOT / "tests/m0/toolchain.json").read_text())
        gateway_bin = ROOT / ".tools/mediamtx/mediamtx"
        aitum = ROOT / ".tools/aitum-vertical/vertical-canvas.so"
        if ladder:
            require(digest(Path("/usr/lib/obs-plugins/vertical-canvas.so")) == SYSTEM_AITUM_SHA256,
                    "installed Aitum binary checksum mismatch")
        else:
            require(digest(aitum) == AITUM_SHA256,
                    "Aitum official Linux binary checksum mismatch")
        require(
            digest(gateway_bin) == pins["linux_amd64_binary_sha256"],
            "MediaMTX checksum mismatch",
        )
        report["ffmpeg"] = lab.run(["ffmpeg", "-version"]).decode().splitlines()[0]
        require(
            report["ffmpeg"].split()[2] == pins["ffmpeg_version"],
            "FFmpeg version mismatch",
        )
        report["gateway"] = lab.run([str(gateway_bin), "--version"]).decode().strip()
        require(
            report["gateway"] == pins["mediamtx_version"], "MediaMTX version mismatch"
        )
        source_files = [
            Path(__file__).resolve(),
            ROOT / "scripts/m0_dual_checks.py",
            ROOT / "scripts/m0_flv_checks.py",
            ROOT / "scripts/m0_protocols.py",
            ROOT / "tests/m0/dual-canvas.mjs",
            ROOT / "tests/m0/obs-rpc.mjs",
            ROOT / "tests/m0/toolchain.json",
        ]
        if ladder:
            source_files.extend(
                [
                    ROOT / "scripts/m0_twitch_config.py",
                    ROOT / "tests/m0/twitch-ladder-local.json",
                ]
            )
        report["harness_sha256"] = {
            str(p.relative_to(ROOT)): digest(p)
            for p in source_files
        }
        report["python_optimized"] = bool(sys.flags.optimize)
        if not ladder:
            modules = work / "modules"
            modules.mkdir()
            module_data = work / "module-data"
            module_data.mkdir()
            report["module_sha256"] = {}
            for name in MODULES:
                source = Path("/usr/lib/obs-plugins") / f"{name}.so"
                shutil.copyfile(source, modules / source.name)
                report["module_sha256"][source.name] = digest(source)
                data = Path("/usr/share/obs/obs-plugins") / name
                if data.is_dir():
                    shutil.copytree(data, module_data / name)
            shutil.copyfile(aitum, modules / "vertical-canvas.so")
            shutil.copytree(
                ROOT / ".tools/aitum-vertical/data", module_data / "vertical-canvas"
            )
            report["module_sha256"]["vertical-canvas.so"] = digest(aitum)
        for name, size, color in [
            ("horizontal", "640x360", "red"),
            ("vertical", "360x640", "blue"),
        ]:
            lab.run(
                [
                    "ffmpeg",
                    "-nostdin",
                    "-v",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    f"color=c={color}:s={size}:r=30,drawtext=text={name.upper()}:fontcolor=white:fontsize=32:x=40:y=100",
                    "-t",
                    "3",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "ultrafast",
                    "-pix_fmt",
                    "yuv420p",
                    str(work / f"{name}.mp4"),
                ]
            )
        for name, hz in [("live", 440), ("vod", 880)]:
            lab.run(
                [
                    "ffmpeg",
                    "-nostdin",
                    "-v",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    f"sine=frequency={hz}:sample_rate=48000",
                    "-t",
                    "3",
                    str(work / f"{name}.wav"),
                ]
            )
        gateway_config = work / "mediamtx.yml"
        gateway_config.write_text("""logLevel: warn
moq: false
rtspAddress: 127.0.0.1:18555
rtspTransports: [tcp]
rtmpAddress: 127.0.0.1:19351
hls: false
webrtc: false
srt: false
paths:
  all_others:
""")
        gateway = lab.start("gateway", [str(gateway_bin), str(gateway_config)])
        lab.port(18555, gateway)
        cfgdir = work / "config/obs-studio"
        profile = cfgdir / "basic/profiles/M0"
        profile.mkdir(parents=True)
        # The service must exist before OBS constructs its multitrack output handler.
        (profile / "service.json").write_text(
            json.dumps(
                {
                    "type": "rtmp_custom",
                    "settings": {
                        "server": "rtmp://127.0.0.1:19351/dual",
                        "key": "obs",
                        "use_auth": False,
                    },
                }
            )
        )
        (cfgdir / "global.ini").write_text("[General]\nLastVersion=536870912\n")
        vertical_config = cfgdir / "plugin_config/vertical-canvas"
        vertical_config.mkdir(parents=True)
        (vertical_config / "config.json").write_text(
            json.dumps(
                {
                    "canvas": [
                        {
                            "current_scene": "Vertical Scene",
                            "width": 1080,
                            "height": 1920,
                            "backtrack": False,
                            "streaming_match_main": False,
                            "recording_match_main": False,
                        }
                    ]
                }
            )
        )
        (cfgdir / "user.ini").write_text(
            "[General]\nFirstRun=true\nEnableCustomServerVodTrack=true\n[Basic]\nProfile=M0\nProfileDir=M0\nSceneCollection=M0\nSceneCollectionFile=M0\nConfigOnNewProfile=false\n"
        )
        settings = {
            "rate_control": "CBR",
            "bitrate": 1000,
            "keyint_sec": 1,
            "preset": "ultrafast",
            "profile": "baseline",
            "tune": "zerolatency",
        }
        configuration = {
            "meta": {
                "service": "local-fixture",
                "schema_version": "2025-01-25",
                "config_id": "local-only",
            },
            "ingest_endpoints": [
                {
                    "protocol": "RTMP",
                    "url_template": "rtmp://127.0.0.1:19351/dual/{stream_key}",
                }
            ],
            "encoder_configurations": [
                {
                    "type": "obs_x264",
                    "width": w,
                    "height": h,
                    "canvas_index": i,
                    "settings": settings,
                    "framerate": {"numerator": 30, "denominator": 1},
                }
                for i, (w, h) in enumerate([(640, 360), (360, 640)])
            ],
            "audio_configurations": {
                name: [
                    {
                        "codec": "aac",
                        "track_id": i,
                        "channels": 2,
                        "settings": {"bitrate": 128},
                    }
                ]
                for i, name in enumerate(["live", "vod"])
            },
        }
        source_key = "obs"
        if ladder:
            fixture = json.loads((ROOT / "tests/m0/twitch-ladder-local.json").read_text())
            source_key = "m0-local-synthetic-source-key"
            configuration, report["ladder_mapping"] = local_obs_config(
                fixture, 19351, source_key
            )
        (profile / "basic.ini").write_text(
            """[General]
Name=M0
[Output]
Mode=Advanced
[Video]
BaseCX=640
BaseCY=360
OutputCX=640
OutputCY=360
FPSCommon=30
[Audio]
SampleRate=48000
ChannelSetup=Stereo
[AdvOut]
Encoder=obs_x264
AudioEncoder=ffmpeg_aac
TrackIndex=1
VodTrackEnabled=true
VodTrackIndex=2
ApplyServiceSettings=false
RecType=Standard
RecEncoder=none
[Stream1]
EnableMultitrackVideo=true
MultitrackVideoConfigOverrideEnabled=true
MultitrackVideoConfigOverride="""
            + json.dumps({"text": json.dumps(configuration)}, separators=(",", ":"))
            + "\n"
        )
        password = secrets.token_urlsafe(24)
        ws = cfgdir / "plugin_config/obs-websocket"
        ws.mkdir(parents=True)
        (ws / "config.json").write_text(
            json.dumps(
                {
                    "server_enabled": True,
                    "server_port": 19447,
                    "auth_required": True,
                    "server_password": password,
                    "first_load": False,
                    "alerts_enabled": False,
                }
            )
        )
        controller = work / "controller.json"
        controller.write_text(
            json.dumps(
                {
                    "password": password,
                    **{
                        name: str(work / f"{name}.{ext}")
                        for name, ext in [
                            ("horizontal", "mp4"),
                            ("vertical", "mp4"),
                            ("live", "wav"),
                            ("vod", "wav"),
                        ]
                    },
                }
            )
        )
        require(
            not Path("/tmp/.X199-lock").exists()
            and not Path("/tmp/.X11-unix/X199").exists(),
            "isolated X display :199 is already occupied",
        )
        display = lab.start(
            "xvfb",
            ["Xvfb", ":199", "-screen", "0", "1280x720x24", "-nolisten", "tcp", "-ac"],
        )
        lab.display_ready(display)
        (work / "xdg").mkdir(mode=0o700)
        env = dict(
            os.environ,
            DISPLAY=":199",
            XAUTHORITY="/dev/null",
            GDK_BACKEND="x11",
            GDK_SCALE="1",
            QT_SCALE_FACTOR="1",
            QT_QPA_PLATFORM="xcb",
            XDG_CONFIG_HOME=str(work / "config"),
            XDG_CACHE_HOME=str(work / "cache"),
            XDG_RUNTIME_DIR=str(work / "xdg"),
            LIBGL_ALWAYS_SOFTWARE="1",
            PULSE_SERVER="unix:/nonexistent",
            QTWEBENGINE_DISABLE_SANDBOX="1",
        )
        for key in [
            "WAYLAND_DISPLAY",
            "DBUS_SESSION_BUS_ADDRESS",
            "QT_QPA_PLATFORMTHEME",
            "QT_IM_MODULE",
        ]:
            env.pop(key, None)
        if ladder:
            obs_args = [
                "obs", "--multi", "--disable-missing-files-check",
                "--profile", "M0", "--collection", "M0",
            ]
        else:
            obs_args = [
                "bwrap",
                "--die-with-parent",
                "--ro-bind",
                "/",
                "/",
                "--bind",
                str(work),
                str(work),
                "--ro-bind",
                str(modules),
                "/usr/lib/obs-plugins",
                "--ro-bind",
                str(module_data),
                "/usr/share/obs/obs-plugins",
                "--",
                "obs",
                "--multi",
                "--disable-missing-files-check",
                "--profile",
                "M0",
                "--collection",
                "M0",
            ]
        obs = lab.start("obs", obs_args, env)
        lab.port(19447, obs)
        if ladder:
            report["loaded_module_sha256"] = loaded_system_modules(work / "obs.log")
        report["obs"] = json.loads(
            lab.run(
                [
                    "node",
                    str(ROOT / "tests/m0/dual-canvas.mjs"),
                    work.name.removeprefix("m0-dual-"),
                ],
                55,
            )
        )
        require(
            report["obs"]["obsVersion"] == pins["obs_version"], "OBS version mismatch"
        )
        require(
            report["obs"]["websocketVersion"] == pins["obs_websocket_version"],
            "WebSocket version mismatch",
        )
        report["tests"]["obs_ingest_rtsp"] = observe(lab, source_key, ladder)
        flv = lab.run(
            [
                "ffmpeg",
                "-nostdin",
                "-v",
                "error",
                "-rtsp_transport",
                "tcp",
                "-i",
                f"rtsp://127.0.0.1:18555/dual/{source_key}",
                "-t",
                "2",
                "-map",
                "0",
                "-c",
                "copy",
                "-f",
                "flv",
                OUTPUT_PIPE,
            ],
        )
        report["tests"]["flv_track_ids"] = check_flv_track_ids(
            flv, video_tracks=4 if ladder else 2
        )
        relay = lab.start(
            "relay",
            [
                "ffmpeg",
                "-nostdin",
                "-v",
                "error",
                "-rtsp_transport",
                "tcp",
                "-i",
                f"rtsp://127.0.0.1:18555/dual/{source_key}",
                "-map",
                "0",
                "-c",
                "copy",
                *([] if ladder else ["-rtmp_enhanced_codecs", "avc1,mp4a"]),
                "-f",
                "flv",
                "rtmp://127.0.0.1:19351/dual/relay",
            ],
        )
        time.sleep(3)
        require(relay.poll() is None, "copy publisher exited")
        report["tests"]["enhanced_copy_publisher"] = observe(lab, "relay", ladder)
        report["status"] = (
            "passed_local_twitch_ladder" if ladder else "passed_local_dual_canvas"
        )
    except Exception as error:
        report["status"] = "failed"
        report["error_type"] = type(error).__name__
        raise
    finally:
        lab.close()
        (work / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
        print(f"Evidence: {work / 'report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
