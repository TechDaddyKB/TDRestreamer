"""One bounded TechDaddy M0 qualification attempt; default is local-only.

The broadcast option is covered by the owner's standing M0 test authorization.
It does not retain the stream key, negotiated response, or ingest playpath.
"""

import argparse
import hashlib
import json
import os
import platform
import re
import secrets
import signal
import socket
import subprocess as sp
import sys
import threading
import time
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from m0_socket_bridge import serve_tcp_to_unix
from m0_twitch_config import inspect_config

SOURCE = "rtsp://127.0.0.1:18556/dual/m0-local-synthetic-source-key"
LOCAL_DESTINATION = "rtmp://127.0.0.1:19351/dual"
TWITCH_DESTINATION = "rtmps://ingest.global-contribute.live-video.net/app"
NEGOTIATION_URL = "https://ingest.twitch.tv/api/v3/GetClientConfiguration"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc_now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def check_host_ports():
    for port in (18556, 18557, 19351):
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(("127.0.0.1", port))


def start_process(args, log_path, input_line=None):
    with log_path.open("wb") as output:
        process = sp.Popen(
            args,
            stdin=sp.PIPE if input_line is not None else sp.DEVNULL,
            stdout=output,
            stderr=sp.STDOUT,
            start_new_session=True,
            shell=False,
        )
    if input_line is not None:
        process.stdin.write(input_line.encode())
        process.stdin.close()
    return process


def stop_process(process):
    if process is None or process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=8)
    except sp.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=3)


def wait_source(process, log_path):
    deadline = time.monotonic() + 100
    while time.monotonic() < deadline:
        require(process.poll() is None, "isolated source exited before ready")
        for line in log_path.read_text(errors="replace").splitlines():
            if line.startswith("M0_SOURCE_READY "):
                path = Path(line.removeprefix("M0_SOURCE_READY "))
                require(path.parent.parent == ROOT / "runtime" and path.name == "rtsp.sock",
                        "unexpected source bridge path")
                require(path.is_socket() and path.stat().st_mode & 0o777 == 0o600,
                        "source bridge is not a private socket")
                return path
        time.sleep(0.25)
    raise RuntimeError("isolated source did not become ready")


def ffprobe(url, timeout=12):
    result = sp.run(
        ["ffprobe", "-v", "error", "-rtsp_transport", "tcp", "-i", url,
         "-show_streams", "-of", "json"],
        stdout=sp.PIPE, stderr=sp.DEVNULL, timeout=timeout, check=False,
    )
    if result.returncode:
        return None
    return json.loads(result.stdout)["streams"]


def check_six_streams(streams):
    expected = [
        ("video", "h264", 640, 360),
        ("video", "h264", 284, 160),
        ("video", "h264", 720, 1280),
        ("video", "h264", 360, 640),
        ("audio", "aac", None, None),
        ("audio", "aac", None, None),
    ]
    actual = [
        (s.get("codec_type"), s.get("codec_name"), s.get("width"), s.get("height"))
        for s in streams
    ]
    require(actual == expected, "six-stream order or geometry changed")


def wait_stream(url, process, deadline_seconds=18):
    deadline = time.monotonic() + deadline_seconds
    while time.monotonic() < deadline:
        require(process.poll() is None, "copy publisher exited before RTSP probe")
        streams = ffprobe(url)
        if streams is not None:
            check_six_streams(streams)
            return
        time.sleep(0.5)
    raise RuntimeError("copy publisher did not reach local sink")


def copy_diagnostics(path):
    log = path.read_text(errors="replace")
    result = {}
    for name, length in (("startup_missing_timestamps", 6),
                         ("keyframes", 4), ("first_key_pts_ms", 4),
                         ("bpm_ts", 4), ("bpm_sm", 4), ("bpm_erm", 4),
                         ("keyframes_with_bpm", 4), ("dropped_bpm", 4),
                         ("first_ready_pts_ms", 4),
                         ("first_output_key_pts_ms", 4)):
        match = re.search(rf"^{name}=(-?\d+(?:,-?\d+){{{length - 1}}})$", log, re.M)
        require(match is not None, f"copy diagnostic {name} missing")
        result[name] = [int(value) for value in match.group(1).split(",")]
    match = re.search(r"^enhanced_primary_tags=(\d+)$", log, re.M)
    require(match is not None, "copy diagnostic enhanced_primary_tags missing")
    result["enhanced_primary_tags"] = int(match.group(1))
    return result


def require_broadcast_ready(diagnostics):
    require(all(count > 0 for count in diagnostics["keyframes"]),
            "local publisher did not observe every video keyframe")
    require(all(count > 0 for count in diagnostics["keyframes_with_bpm"]),
            "local publisher lacks IVS BPM metadata before every keyframe")
    require(diagnostics["enhanced_primary_tags"] > 0,
            "local publisher did not emit enhanced primary H.264 tags")
    first = diagnostics["first_output_key_pts_ms"]
    require(max(first) - min(first) <= 15,
            "local publisher video IDRs are not timestamp-aligned")


def build_copy(work):
    source = ROOT / "tests/m0/twitch_copy.c"
    binary = work / "twitch-copy"
    result = sp.run(
        ["gcc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
         "-o", str(binary), str(source), "-lavformat", "-lavcodec", "-lavutil"],
        stdout=sp.DEVNULL, stderr=sp.PIPE, timeout=20, check=False,
    )
    require(result.returncode == 0, "bounded copy publisher did not compile")
    return binary


def keyring_stream_key():
    key = sp.check_output(
        ["secret-tool", "lookup", "service", "tdrestreamer", "account", "twitch-m0",
         "kind", "stream-key"], stderr=sp.DEVNULL, timeout=5,
    ).decode().strip()
    require(re.fullmatch(r"[A-Za-z0-9_-]{40,256}", key) is not None,
            "keyring stream-key shape changed")
    return key


def twitch_app_token():
    def lookup(kind):
        return sp.check_output(
            ["secret-tool", "lookup", "service", "tdrestreamer", "account",
             "twitch-m0", "kind", kind], stderr=sp.DEVNULL, timeout=5,
        ).decode().strip()

    client_id = lookup("client-id")
    client_secret = lookup("client-secret")
    require(re.fullmatch(r"[A-Za-z0-9]{20,}", client_id) is not None and
            re.fullmatch(r"[A-Za-z0-9_-]{20,}", client_secret) is not None,
            "Twitch app credential shape changed")
    body = urlencode({"client_id": client_id, "client_secret": client_secret,
                      "grant_type": "client_credentials"}).encode()
    request = Request("https://id.twitch.tv/oauth2/token", data=body,
                      headers={"Content-Type": "application/x-www-form-urlencoded"},
                      method="POST")
    with urlopen(request, timeout=15) as response:
        require(response.status == 200, "Twitch app token request failed")
        token = json.loads(response.read(128_000)).get("access_token")
    require(isinstance(token, str) and len(token) >= 20, "Twitch app token missing")
    return client_id, token


def channel_live(client_id, token):
    request = Request(
        "https://api.twitch.tv/helix/streams?user_login=TechDaddy",
        headers={"Client-Id": client_id, "Authorization": "Bearer " + token},
    )
    with urlopen(request, timeout=10) as response:
        require(response.status == 200, "Twitch live-state read failed")
        data = json.loads(response.read(128_000)).get("data")
    require(isinstance(data, list), "Twitch live-state response changed")
    return any(str(item.get("user_login", "")).lower() == "techdaddy" for item in data)


def negotiate(key, include_config=False):
    mem = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        fields = line.split()
        if fields[0] in ("MemTotal:", "MemAvailable:"):
            mem[fields[0]] = int(fields[1]) * 1024
    cpu = os.cpu_count() or 1
    gpu = sp.check_output(
        ["nvidia-smi", "--query-gpu=name,pci.device_id,memory.total,driver_version",
         "--format=csv,noheader,nounits"], stderr=sp.DEVNULL, timeout=5,
    ).decode().splitlines()[0].split(",")
    name, pci, mib, driver = (x.strip() for x in gpu)
    fps = {"numerator": 30, "denominator": 1}
    payload = {
        "service": "IVS", "schema_version": "2025-01-25", "authentication": key,
        "client": {"name": "obs-studio", "version": "32.2.2", "supported_codecs": ["h264"]},
        "capabilities": {
            "cpu": {"physical_cores": max(1, cpu // 2), "logical_cores": cpu,
                    "speed": None, "name": None},
            "memory": {"total": mem["MemTotal:"], "free": mem["MemAvailable:"]},
            "gaming_features": None,
            "system": {"version": platform.version(), "name": "Linux", "build": 0,
                       "release": platform.release(), "revision": "", "bits": 64,
                       "arm": False, "armEmulation": False},
            "gpu": [{"model": name, "vendor_id": int(pci[6:10], 16),
                     "device_id": int(pci[2:6], 16),
                     "dedicated_video_memory": int(mib) * 1024 * 1024,
                     "shared_system_memory": 0, "driver_version": driver}],
        },
        "preferences": {
            "maximum_aggregate_bitrate": 6000, "maximum_video_tracks": 4,
            "vod_track_audio": True, "composition_gpu_index": None,
            "audio_samples_per_sec": 48000, "audio_channels": 2,
            "audio_max_buffering_ms": 0, "audio_fixed_buffering": False,
            "canvases": [
                {"width": 640, "height": 360, "canvas_width": 640, "canvas_height": 360,
                 "framerate": fps},
                {"width": 1080, "height": 1920, "canvas_width": 1080,
                 "canvas_height": 1920, "framerate": fps},
            ],
        },
    }
    request = Request(
        NEGOTIATION_URL, data=json.dumps(payload, separators=(",", ":")).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urlopen(request, timeout=10) as response:
        require(response.status == 200, "Twitch negotiation HTTP status changed")
        config = json.loads(response.read(512_000))
    inspect_config(config)
    fixture = json.loads((ROOT / "tests/m0/twitch-ladder-local.json").read_text())
    require(config["encoder_configurations"] == fixture["encoder_configurations"]
            and config["audio_configurations"] == fixture["audio_configurations"],
            "negotiated encoder ladder differs from qualified fixture")
    endpoint = next((item for item in config["ingest_endpoints"]
                     if item.get("protocol") == "RTMPS"), None)
    require(endpoint is not None and
            endpoint.get("url_template") == TWITCH_DESTINATION + "/{stream_key}",
            "Twitch RTMPS endpoint changed")
    authentication = endpoint.get("authentication")
    require(isinstance(authentication, str) and len(authentication) >= 24 and
            re.fullmatch(r"[A-Za-z0-9_.%=&-]+", authentication) is not None,
            "Twitch ingest authentication shape changed")
    config_id = config["meta"]["config_id"]
    require(isinstance(config_id, str) and re.fullmatch(r"[A-Za-z0-9-]{8,80}", config_id),
            "Twitch config ID changed")
    bitrates = [v["settings"]["bitrate"] for v in config["encoder_configurations"]]
    bitrates += [a["settings"]["bitrate"] for role in ("live", "vod")
                 for a in config["audio_configurations"][role]]
    require(all(type(value) is int and value > 0 for value in bitrates)
            and sum(bitrates) <= 6000, "Twitch negotiated bitrate cap exceeded")
    result = (authentication + "?clientConfigId=" + quote(config_id, safe=""),
              sum(bitrates))
    return (*result, config) if include_config else result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broadcast", action="store_true",
                        help="one bounded public Twitch attempt")
    parser.add_argument("--seconds", type=int, default=300)
    args = parser.parse_args()
    require(1 <= args.seconds <= 300, "broadcast duration must be 1..300 seconds")
    os.umask(0o077)
    check_host_ports()
    work = ROOT / "runtime" / ("m0-twitch-" + secrets.token_hex(6))
    work.mkdir(mode=0o700)
    report = {"status": "running", "recorded_at": utc_now(),
              "mode": "one_approved_broadcast" if args.broadcast else "local_only",
              "limits": {"duration_seconds": args.seconds, "nominal_kbps": 6000}}
    processes = []
    bridge_stop = threading.Event()
    bridge = None
    try:
        binary = build_copy(work)
        report["copy_binary_sha256"] = digest(binary)
        report["source_sha256"] = {
            str(path.relative_to(ROOT)): digest(path)
            for path in (ROOT / "tests/m0/twitch_copy.c",
                         ROOT / "scripts/m0-dual-canvas.py",
                         ROOT / "scripts/m0_socket_bridge.py",
                         Path(__file__))
        }
        config = work / "mediamtx.yml"
        config.write_text("""logLevel: debug
moq: false
rtspAddress: 127.0.0.1:18557
rtspTransports: [tcp]
rtmpAddress: 127.0.0.1:19351
hls: false
webrtc: false
srt: false
paths:
  all_others:
""")
        gateway = start_process(
            [str(ROOT / ".tools/mediamtx/mediamtx"), str(config)], work / "gateway.log")
        processes.append(gateway)
        source = start_process(
            [sys.executable, str(ROOT / "scripts/m0-dual-canvas.py"),
             "--twitch-ladder", "--bridge-source"], work / "source.log")
        processes.append(source)
        socket_path = wait_source(source, work / "source.log")
        ready = threading.Event()
        bridge_errors = []

        def run_bridge():
            try:
                serve_tcp_to_unix(socket_path, bridge_stop.is_set, ready)
            except OSError as error:
                bridge_errors.append(type(error).__name__)
                ready.set()

        bridge = threading.Thread(target=run_bridge, daemon=True)
        bridge.start()
        require(ready.wait(3) and not bridge_errors, "host loopback bridge failed")
        wait_stream(SOURCE, source)
        local = start_process(
            [str(binary), SOURCE, LOCAL_DESTINATION, "45"], work / "local-copy.log",
            input_line="local\n")
        processes.append(local)
        wait_stream("rtsp://127.0.0.1:18557/dual/local", local)
        stop_process(local)
        require(local.returncode == 0, "local copy publisher did not stop cleanly")
        report["local_copy"] = "six_streams_passed"
        diagnostics = copy_diagnostics(work / "local-copy.log")
        report["local_copy_diagnostics"] = diagnostics
        if not args.broadcast:
            report["status"] = "passed_local_bridge"
            return 0

        require_broadcast_ready(diagnostics)

        client_id, token = twitch_app_token()
        require(not channel_live(client_id, token), "TechDaddy is already live")
        playpath, nominal_kbps = negotiate(keyring_stream_key())
        report["negotiated_nominal_kbps"] = nominal_kbps
        remote = start_process(
            [str(binary), SOURCE, TWITCH_DESTINATION, str(args.seconds)],
            work / "remote-copy.log", input_line=playpath + "\n")
        processes.append(remote)
        report["broadcast_start_utc"] = utc_now()
        print("M0_TWITCH_BROADCAST_STARTED", flush=True)
        deadline = time.monotonic() + args.seconds + 10
        next_live_check = time.monotonic() + 10
        report["helix_live_observed"] = False
        while remote.poll() is None and time.monotonic() < deadline:
            require(source.poll() is None and bridge.is_alive(),
                    "isolated source or bridge ended during broadcast")
            if time.monotonic() >= next_live_check:
                try:
                    report["helix_live_observed"] |= channel_live(client_id, token)
                except Exception:
                    report["helix_read_failed"] = True
                next_live_check = time.monotonic() + 10
            time.sleep(0.5)
        require(remote.poll() is not None, "broadcast publisher exceeded hard stop")
        report["broadcast_end_utc"] = utc_now()
        report["publisher_exit_code"] = remote.returncode
        require(remote.returncode == 0, "Twitch copy publisher failed")
        report["status"] = "publisher_completed_unverified_delivery"
        return 0
    except Exception as error:
        report["status"] = "failed"
        report["error_type"] = type(error).__name__
        report["error_stage"] = str(error)[:160]
        raise
    finally:
        for process in reversed(processes):
            stop_process(process)
        bridge_stop.set()
        if bridge is not None:
            bridge.join(timeout=3)
        if args.broadcast and "client_id" in locals() and "token" in locals():
            try:
                offline_deadline = time.monotonic() + 30
                while channel_live(client_id, token) and time.monotonic() < offline_deadline:
                    time.sleep(2)
                report["helix_offline_after_stop"] = not channel_live(client_id, token)
            except Exception:
                report["helix_offline_check_failed"] = True
        (work / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(f"M0_EVIDENCE {work / 'report.json'}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
