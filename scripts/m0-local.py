#!/usr/bin/env python3
"""Run M0 against real isolated OBS and authenticated MediaMTX, with no external route."""

import array
import hashlib
import http.server
import json
import math
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess as sp
import sys
import threading
import time
from m0_protocols import qualify, require

os.umask(0o077)
ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "runtime" / "m0"
GATEWAY_BIN = ROOT / ".tools/mediamtx/mediamtx"
OBS_PATH = "a/obs"
RELAY_PATH = "a/relay"
WORK.mkdir(parents=True, exist_ok=True)
WORK.chmod(0o700)
if "--isolated" not in sys.argv:
    # The executable is fixed; the path arguments are passed without shell parsing.
    exit_status = sp.call(
        [
            "unshare",
            "--user",
            "--map-root-user",
            "--net",
            sys.executable,
            str(Path(__file__).resolve()),
            "--isolated",
        ],
        shell=False,
    )
    raise SystemExit(exit_status)
initial_links = json.loads(sp.check_output(["ip", "-j", "link", "show"]))
require(
    [link["ifname"] for link in initial_links] == ["lo"],
    "refusing a namespace with non-loopback links",
)
require(
    not json.loads(sp.check_output(["ip", "-j", "-6", "route", "show"])),
    "refusing IPv6 routes",
)
routes = json.loads(sp.check_output(["ip", "-j", "route", "show"]))
require(not routes, "refusing to run with an external route")
sp.run(["ip", "link", "set", "lo", "up"], check=True)
# An unconnected dummy interface gives WebRTC an ICE candidate without external egress.
sp.run(["ip", "link", "add", "m0dummy", "type", "dummy"], check=True)
sp.run(["ip", "addr", "add", "192.0.2.1/24", "dev", "m0dummy"], check=True)
sp.run(["ip", "link", "set", "m0dummy", "up"], check=True)
processes = []
files = []
auth_events = []
passwords = {
    name: secrets.token_urlsafe(24)
    for name in [
        "publisher",
        "publisher-b",
        "reader-a",
        "reader-b",
        "expired",
        "srt-encryption",
    ]
}
PUBLISH_ACTIONS = frozenset(["publish", "read"])
AUTH_SCOPES = {
    "publisher": ("a/", PUBLISH_ACTIONS),
    "publisher-b": ("b/", PUBLISH_ACTIONS),
    "reader-a": ("a/", frozenset(["read"])),
    "reader-b": ("b/", frozenset(["read"])),
}
report = {
    "status": "running",
    "external_routes": routes,
    "tests": {},
    "limitations": [
        "No external broadcasting or cloud calls authorized",
        "Twitch H/V and platform live/VOD acceptance remain unverified",
        "Standalone feasibility harness, not application media integration",
        "Denied credential fixture does not prove clock-based expiry or active-session revocation",
        "Single horizontal OBS video input; no dual-video or combined-canvas qualification",
        "Browser audio is negotiated but not sample-analyzed; no latency, synchronization or soak qualification",
    ],
}


class Auth(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        # HTTP request logging is deliberately disabled to avoid credential leaks.
        pass

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        user = request.get("user")
        password = request.get("password")
        path = request.get("path", "")
        action = request.get("action")
        allow = (
            user in passwords
            and secrets.compare_digest(password or "", passwords.get(user, ""))
            and user != "expired"
        )
        scope = AUTH_SCOPES.get(user)
        allow = (
            allow
            and scope is not None
            and action in scope[1]
            and path.startswith(scope[0])
        )
        auth_events.append(
            {
                "user": user,
                "path": path,
                "action": action,
                "protocol": request.get("protocol"),
                "allowed": bool(allow),
            }
        )
        self.send_response(200 if allow else 403)
        self.end_headers()


auth = http.server.ThreadingHTTPServer(("127.0.0.1", 18999), Auth)
threading.Thread(target=auth.serve_forever, daemon=True).start()


def run(args, timeout=30):
    # Audited: argv contains fixed tools and local synthetic fixture values, never shell code.
    p = sp.Popen(  # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit
        args, stdout=sp.PIPE, stderr=sp.PIPE, start_new_session=True, shell=False
    )
    try:
        out, err = p.communicate(timeout=timeout)
    except sp.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        p.communicate()
        raise RuntimeError(f"{args[0]} exceeded {timeout}s") from None
    if p.returncode:
        detail = err.decode(errors="replace")[-2500:]
        for secret in passwords.values():
            detail = detail.replace(secret, "[redacted]")
        raise RuntimeError(f"{args[0]} failed: " + detail)
    return out


def start(name, args, env=None):
    f = (WORK / (name + ".log")).open("w")
    files.append(f)
    # Audited: same fixed-tool argv boundary as run(); shell parsing stays disabled.
    p = sp.Popen(  # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit
        args,
        stdout=f,
        stderr=sp.STDOUT,
        cwd=WORK,
        env=env,
        start_new_session=True,
        shell=False,
    )
    processes.append(p)
    return p


def wait_port(port, process):
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError(
                f"process exited before port {port}: inspect runtime/m0 logs"
            )
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"port {port} did not open")


def rtsp(path, user="publisher"):
    return f"rtsp://{user}:{passwords[user]}@127.0.0.1:18554/{path}"


def probe(path, user="publisher"):
    return json.loads(
        run(
            [
                "ffprobe",
                "-v",
                "error",
                "-rtsp_transport",
                "tcp",
                "-i",
                rtsp(path, user),
                "-show_streams",
                "-of",
                "json",
            ],
            15,
        )
    )["streams"]


def tone(path, index, hz):
    samples = array.array(
        "h",
        run(
            [
                "ffmpeg",
                "-nostdin",
                "-v",
                "error",
                "-rtsp_transport",
                "tcp",
                "-i",
                rtsp(path),
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
                "pipe:1",
            ],
            15,
        ),
    )

    def power(freq):
        return (
            abs(
                sum(
                    v
                    * complex(
                        math.cos(2 * math.pi * freq * n / 48000),
                        math.sin(2 * math.pi * freq * n / 48000),
                    )
                    for n, v in enumerate(samples)
                )
            )
            ** 2
        )

    ratio = power(hz) / max(1, power(880 if hz == 440 else 440))
    require(ratio > 100, f"wrong audio track {index}: ratio {ratio}")
    return {"expected_hz": hz, "opposite_tone_power_ratio": round(ratio, 2)}


try:
    report["harness_sha256"] = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in [
            Path(__file__).resolve(),
            ROOT / "scripts/m0_protocols.py",
            ROOT / "tests/m0/obs-control.mjs",
            ROOT / "tests/m0/preview.mjs",
            ROOT / "tests/m0/toolchain.json",
            ROOT / "web/package-lock.json",
        ]
    }
    report["python_optimized"] = bool(sys.flags.optimize)
    report["recorded_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    report["gateway"] = run([str(GATEWAY_BIN), "--version"]).decode().strip()
    report["gateway_sha256"] = hashlib.sha256((GATEWAY_BIN).read_bytes()).hexdigest()
    report["ffmpeg"] = run(["ffmpeg", "-version"]).decode().splitlines()[0]
    pins = json.loads((ROOT / "tests/m0/toolchain.json").read_text())
    require(report["gateway"] == pins["mediamtx_version"], "MediaMTX version mismatch")
    require(
        report["gateway_sha256"] == pins["linux_amd64_binary_sha256"],
        "MediaMTX binary checksum mismatch (this fixture is pinned to Linux amd64)",
    )
    require(
        report["ffmpeg"].split()[2] == pins["ffmpeg_version"], "FFmpeg version mismatch"
    )
    report["isolation"] = {
        "links": json.loads(run(["ip", "-j", "link", "show"])),
        "routes": json.loads(run(["ip", "-j", "route", "show"])),
        "ipv6_routes": json.loads(run(["ip", "-j", "-6", "route", "show"])),
    }
    run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "1",
            "-subj",
            "/CN=M0 isolated lab",
            "-addext",
            "subjectAltName=IP:127.0.0.1",
            "-keyout",
            str(WORK / "server.key"),
            "-out",
            str(WORK / "server.crt"),
        ]
    )
    config = """logLevel: warn
moq: false
rtmpEncryption: optional
rtmpsAddress: 127.0.0.1:19360
rtmpServerKey: server.key
rtmpServerCert: server.crt
rtspAddress: 127.0.0.1:18554
rtspTransports: [tcp]
rtmpAddress: 127.0.0.1:19350
hlsAddress: 127.0.0.1:18888
hlsVariant: fmp4
hlsAllowOrigins: ['http://127.0.0.1:18090']
webrtcAddress: 127.0.0.1:18889
webrtcLocalUDPAddress: 0.0.0.0:18189
webrtcIPsFromInterfaces: false
webrtcAdditionalHosts: [192.0.2.1]
webrtcICEServers2: []
webrtcAllowOrigins: ['http://127.0.0.1:18090']
srtAddress: 127.0.0.1:18890
authMethod: http
authHTTPAddress: http://127.0.0.1:18999/auth
authHTTPExclude: []
pathDefaults:
  srtPublishPassphrase: SRT_ENCRYPTION_PLACEHOLDER
paths:
  all_others:
"""
    config = config.replace("SRT_ENCRYPTION_PLACEHOLDER", passwords["srt-encryption"])
    (WORK / "mediamtx.yml").write_text(config)
    gateway = start("gateway", [str(GATEWAY_BIN), str(WORK / "mediamtx.yml")])
    wait_port(18554, gateway)
    for hz, name in [(440, "live"), (880, "vod")]:
        run(
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
                "10",
                "-y",
                str(WORK / f"{name}.wav"),
            ]
        )
    run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=640x360:rate=30",
            "-t",
            "5",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            "-y",
            str(WORK / "pattern.mp4"),
        ]
    )
    config_home = WORK / ("config-" + secrets.token_hex(6))
    cfgdir = config_home / "obs-studio"
    profile = cfgdir / "basic/profiles/M0"
    profile.mkdir(parents=True, exist_ok=True)
    (cfgdir / "global.ini").write_text("[General]\nLastVersion=536870912\n")
    (cfgdir / "user.ini").write_text(
        "[General]\nFirstRun=true\nEnableCustomServerVodTrack=true\n[Basic]\nProfile=M0\nProfileDir=M0\nSceneCollection=M0\nSceneCollectionFile=M0\nConfigOnNewProfile=false\n"
    )
    (profile / "basic.ini").write_text("""[General]
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
Track1Bitrate=128
Track2Bitrate=128
RecType=Standard
RecEncoder=none
[Stream1]
EnableMultitrackVideo=false
""")
    (profile / "streamEncoder.json").write_text(
        json.dumps(
            {
                "rate_control": "CBR",
                "bitrate": 1000,
                "keyint_sec": 1,
                "preset": "ultrafast",
                "profile": "baseline",
                "tune": "zerolatency",
            }
        )
    )
    plugin = cfgdir / "plugin_config/obs-websocket"
    plugin.mkdir(parents=True, exist_ok=True)
    ws_password = secrets.token_urlsafe(24)
    (plugin / "config.json").write_text(
        json.dumps(
            {
                "server_enabled": True,
                "server_port": 19445,
                "auth_required": True,
                "server_password": ws_password,
                "first_load": False,
                "alerts_enabled": False,
            }
        )
    )
    configfile = WORK / "controller.json"
    configfile.write_text(
        json.dumps(
            {
                "password": ws_password,
                "publishPassword": passwords["publisher"],
                "readerPassword": passwords["reader-a"],
                "otherPassword": passwords["reader-b"],
                "expiredPassword": passwords["expired"],
                "video": str(WORK / "pattern.mp4"),
                "live": str(WORK / "live.wav"),
                "vod": str(WORK / "vod.wav"),
            }
        )
    )
    configfile.chmod(0o600)
    display = start(
        "xvfb",
        ["Xvfb", ":197", "-screen", "0", "1280x720x24", "-nolisten", "tcp", "-ac"],
    )
    time.sleep(0.5)
    env = os.environ.copy()
    env.update(
        {
            "XAUTHORITY": "/dev/null",
            "DISPLAY": ":197",
            "GDK_BACKEND": "x11",
            "GDK_SCALE": "1",
            "QT_SCALE_FACTOR": "1",
            "QT_QPA_PLATFORM": "xcb",
            "XDG_CONFIG_HOME": str(config_home),
            "XDG_CACHE_HOME": str(WORK / "cache"),
            "XDG_RUNTIME_DIR": str(WORK / "xdg"),
            "LIBGL_ALWAYS_SOFTWARE": "1",
            "PULSE_SERVER": "unix:/nonexistent",
            "QTWEBENGINE_DISABLE_SANDBOX": "1",
        }
    )
    Path(env["XDG_RUNTIME_DIR"]).mkdir(exist_ok=True, mode=0o700)
    for key in [
        "WAYLAND_DISPLAY",
        "DBUS_SESSION_BUS_ADDRESS",
        "QT_QPA_PLATFORMTHEME",
        "QT_IM_MODULE",
    ]:
        env.pop(key, None)
    obs = start(
        "obs",
        [
            "obs",
            "--multi",
            "--only-bundled-plugins",
            "--disable-missing-files-check",
            "--profile",
            "M0",
            "--collection",
            "M0",
        ],
        env,
    )
    wait_port(19445, obs)
    report["obs"] = json.loads(
        run(
            [
                "node",
                str(ROOT / "tests/m0/obs-control.mjs"),
            ],
            40,
        )
    )
    require(report["obs"]["obsVersion"] == pins["obs_version"], "OBS version mismatch")
    require(
        report["obs"]["websocketVersion"] == pins["obs_websocket_version"],
        "obs-websocket version mismatch",
    )
    tracks = probe(OBS_PATH)
    report["tests"]["obs_tracks"] = {
        "codecs": [x["codec_name"] for x in tracks],
        "audio_tracks": sum(x["codec_type"] == "audio" for x in tracks),
    }
    require(
        report["tests"]["obs_tracks"]["audio_tracks"] == 2,
        "OBS VOD track was not preserved",
    )
    report["tests"]["obs_audio_identity"] = [
        tone(OBS_PATH, 0, 440),
        tone(OBS_PATH, 1, 880),
    ]
    for path, codec in [("a/webrtc", "libopus"), ("a/hls", "aac")]:
        start(
            path.split("/")[1],
            [
                "ffmpeg",
                "-nostdin",
                "-v",
                "error",
                "-rtsp_transport",
                "tcp",
                "-i",
                rtsp(OBS_PATH),
                "-map",
                "0:v:0",
                "-map",
                "0:a:0",
                "-c:v",
                "copy",
                "-c:a",
                codec,
                "-f",
                "rtsp",
                "-rtsp_transport",
                "tcp",
                rtsp(path),
            ],
        )
    time.sleep(3)
    report["tests"]["preview"] = json.loads(
        run(
            [
                "node",
                str(ROOT / "tests/m0/preview.mjs"),
            ],
            100,
        )
    )
    relay_url = (
        "rtmp://127.0.0.1:19350/a/relay?user=publisher&pass=" + passwords["publisher"]
    )
    start(
        "relay",
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-rtsp_transport",
            "tcp",
            "-i",
            rtsp(OBS_PATH),
            "-map",
            "0",
            "-c",
            "copy",
            "-rtmp_enhanced_codecs",
            "avc1,mp4a",
            "-f",
            "flv",
            relay_url,
        ],
    )
    for attempt in range(20):
        try:
            relay_tracks = probe(RELAY_PATH)
            break
        except RuntimeError:
            if attempt == 19:
                raise
            time.sleep(0.5)
    require(
        sum(x["codec_type"] == "audio" for x in relay_tracks) == 2,
        "relay lost an OBS audio track",
    )
    report["tests"]["obs_enhanced_publisher"] = {
        "codecs": [x["codec_name"] for x in relay_tracks],
        "audio_identity": [tone(RELAY_PATH, 0, 440), tone(RELAY_PATH, 1, 880)],
    }
    report["tests"]["secure_transports"] = qualify(
        WORK, passwords, start, rtsp, probe, tone, auth_events
    )
    report["status"] = "passed_local_obs_preview_transports"
except Exception as error:
    report["status"] = "failed"
    report["error_type"] = type(error).__name__
    raise
finally:
    for p in reversed(processes):
        if p.poll() is None:
            os.killpg(p.pid, signal.SIGTERM)
            try:
                p.wait(timeout=5)
            except sp.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
                p.wait()
    auth.shutdown()
    auth.server_close()
    for f in files:
        f.close()
    report["auth_events"] = auth_events
    (WORK / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
