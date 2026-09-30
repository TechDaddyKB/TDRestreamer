"""Bounded synthetic OBS-to-Twitch reference broadcast in an isolated profile."""

import argparse
import importlib.util
import json
import os
import secrets
import shutil
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from twitch_live import (TWITCH_DESTINATION, channel_live, keyring_stream_key,
                         negotiate, twitch_app_token, utc_now)

spec = importlib.util.spec_from_file_location("m0_dual_canvas", ROOT / "scripts/m0-dual-canvas.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def check_free_port(port):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", port))


def create_assets(lab, work):
    for name, size, color in (("horizontal", "640x360", "red"),
                              ("vertical", "360x640", "blue")):
        lab.run(["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i",
                 f"color=c={color}:s={size}:r=30,drawtext=text={name.upper()}:"
                 "fontcolor=white:fontsize=32:x=40:y=100", "-t", "3",
                 "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                 str(work / f"{name}.mp4")])
    for name, hz in (("live", 440), ("vod", 880)):
        lab.run(["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i",
                 f"sine=frequency={hz}:sample_rate=48000", "-t", "3",
                 str(work / f"{name}.wav")])


def create_obs_profile(work, config):
    cfgdir = work / "config/obs-studio"
    profile = cfgdir / "basic/profiles/M0"
    profile.mkdir(parents=True)
    (profile / "service.json").write_text(json.dumps({
        "type": "rtmp_custom", "settings": {
            "server": TWITCH_DESTINATION, "key": "obs", "use_auth": False,
        },
    }))
    (cfgdir / "global.ini").write_text("[General]\nLastVersion=536870912\n")
    vertical = cfgdir / "plugin_config/vertical-canvas"
    vertical.mkdir(parents=True)
    (vertical / "config.json").write_text(json.dumps({"canvas": [{
        "current_scene": "Vertical Scene", "width": 1080, "height": 1920,
        "backtrack": False, "streaming_match_main": False,
        "recording_match_main": False,
    }]}))
    (cfgdir / "user.ini").write_text(
        "[General]\nFirstRun=true\nEnableCustomServerVodTrack=true\n"
        "[Basic]\nProfile=M0\nProfileDir=M0\nSceneCollection=M0\n"
        "SceneCollectionFile=M0\nConfigOnNewProfile=false\n")
    (profile / "basic.ini").write_text(
        "[General]\nName=M0\n[Output]\nMode=Advanced\n"
        "[Video]\nBaseCX=640\nBaseCY=360\nOutputCX=640\nOutputCY=360\nFPSCommon=30\n"
        "[Audio]\nSampleRate=48000\nChannelSetup=Stereo\n"
        "[AdvOut]\nEncoder=obs_x264\nAudioEncoder=ffmpeg_aac\nTrackIndex=1\n"
        "VodTrackEnabled=true\nVodTrackIndex=2\nApplyServiceSettings=false\n"
        "RecType=Standard\nRecEncoder=none\n"
        "[Stream1]\nEnableMultitrackVideo=true\n"
        "MultitrackVideoConfigOverrideEnabled=true\nMultitrackVideoConfigOverride="
        + json.dumps({"text": json.dumps(config)}, separators=(",", ":")) + "\n")
    password = secrets.token_urlsafe(24)
    ws = cfgdir / "plugin_config/obs-websocket"
    ws.mkdir(parents=True)
    (ws / "config.json").write_text(json.dumps({
        "server_enabled": True, "server_port": 19447, "auth_required": True,
        "server_password": password, "first_load": False, "alerts_enabled": False,
    }))
    (work / "controller.json").write_text(json.dumps({
        "password": password, "server": TWITCH_DESTINATION,
        **{name: str(work / f"{name}.{ext}") for name, ext in (
            ("horizontal", "mp4"), ("vertical", "mp4"),
            ("live", "wav"), ("vod", "wav"))},
    }))


def obs_environment(work):
    (work / "xdg").mkdir(mode=0o700)
    env = dict(os.environ, DISPLAY=":199", XAUTHORITY="/dev/null",
               GDK_BACKEND="x11", GDK_SCALE="1", QT_SCALE_FACTOR="1",
               QT_QPA_PLATFORM="xcb", XDG_CONFIG_HOME=str(work / "config"),
               XDG_CACHE_HOME=str(work / "cache"),
               XDG_RUNTIME_DIR=str(work / "xdg"), LIBGL_ALWAYS_SOFTWARE="1",
               PULSE_SERVER="unix:/nonexistent", QTWEBENGINE_DISABLE_SANDBOX="1")
    for key in ("WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "QT_QPA_PLATFORMTHEME",
                "QT_IM_MODULE", "OBS_PLUGINS_PATH", "OBS_PLUGINS_DATA_PATH"):
        env.pop(key, None)
    return env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broadcast", action="store_true", required=True)
    parser.add_argument("--seconds", type=int, default=90)
    args = parser.parse_args()
    require(1 <= args.seconds <= 300, "duration must be 1..300 seconds")
    os.umask(0o077)
    check_free_port(19447)
    require(not Path("/tmp/.X199-lock").exists() and
            not Path("/tmp/.X11-unix/X199").exists(), "Xvfb display :199 is occupied")
    run_id = secrets.token_hex(6)
    work = Path("/dev/shm") / ("tdrestreamer-obs-control-" + run_id)
    work.mkdir(mode=0o700)
    report_dir = ROOT / "runtime" / ("m0-obs-control-" + run_id)
    report_dir.mkdir(mode=0o700)
    report = {"status": "running", "recorded_at": utc_now(),
              "mode": "direct_obs_control", "seconds_cap": args.seconds,
              "synthetic_identity": {"horizontal": "red", "vertical": "blue",
                                     "live_hz": 440, "vod_hz": 880}}
    lab = fixture.Lab(work)
    stage = "account_preflight"
    try:
        client_id, token = twitch_app_token()
        require(not channel_live(client_id, token), "TechDaddy is already live")
        _, kbps, config = negotiate(keyring_stream_key(), include_config=True)
        report["negotiated_nominal_kbps"] = kbps
        stage = "synthetic_fixture"
        create_assets(lab, work)
        create_obs_profile(work, config)
        stage = "obs_start"
        display = lab.start("xvfb", ["Xvfb", ":199", "-screen", "0", "1280x720x24",
                                      "-nolisten", "tcp", "-ac"])
        lab.display_ready(display)
        obs = lab.start("obs", ["obs", "--multi", "--disable-missing-files-check",
                                "--profile", "M0", "--collection", "M0"],
                        obs_environment(work))
        lab.port(19447, obs)
        result = lab.run(["node", str(ROOT / "tests/m0/dual-canvas.mjs"),
                          "--obs-control", run_id], timeout=55)
        report["obs_initial_status"] = json.loads(result)
        stage = "twitch_delivery"
        report["broadcast_start_utc"] = utc_now()
        print("M0_DIRECT_OBS_BROADCAST_STARTED", flush=True)
        deadline = time.monotonic() + args.seconds
        report["helix_live_observed"] = False
        while time.monotonic() < deadline and obs.poll() is None:
            try:
                report["helix_live_observed"] |= channel_live(client_id, token)
            except Exception:
                report["helix_read_failed"] = True
            time.sleep(5)
        report["obs_exited_early"] = obs.poll() is not None
        stage = "obs_stop"
        stop_result = lab.run(["node", str(ROOT / "tests/m0/obs-control-stop.mjs"),
                               run_id], timeout=20) if obs.poll() is None else b"{}"
        report["obs_stop_status"] = json.loads(stop_result)
        report["broadcast_end_utc"] = utc_now()
        report["status"] = "direct_obs_delivered" if report["helix_live_observed"] \
            else "direct_obs_not_live"
    except Exception as error:
        report["status"] = "failed"
        report["error_type"] = type(error).__name__
        report["error_stage"] = stage
        raise
    finally:
        lab.close()
        if "client_id" in locals() and "token" in locals():
            try:
                offline_deadline = time.monotonic() + 30
                while channel_live(client_id, token) and time.monotonic() < offline_deadline:
                    time.sleep(2)
                report["helix_offline_after_stop"] = not channel_live(client_id, token)
            except Exception:
                report["helix_offline_check_failed"] = True
        shutil.rmtree(work)
        (report_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(f"M0_EVIDENCE {report_dir / 'report.json'}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
