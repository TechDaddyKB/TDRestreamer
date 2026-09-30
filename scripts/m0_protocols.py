"""Additional real transport checks used by the isolated M0 harness."""

import socket
import ssl
import subprocess
import time
from urllib.parse import urlencode

HOST = "127.0.0.1"
TLS_PATH = "a/tls"
SRT_PATH = "a/srt"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def check_tls(certificate):
    context = ssl.create_default_context(cafile=str(certificate))
    with (
        socket.create_connection((HOST, 19360), timeout=3) as raw,
        context.wrap_socket(raw, server_hostname=HOST) as tls,
    ):
        result = {"version": tls.version(), "cipher": tls.cipher()[0]}
    for name, ctx, hostname in [
        ("untrusted_certificate", ssl.create_default_context(), HOST),
        ("wrong_hostname", context, "wrong.invalid"),
    ]:
        try:
            with (
                socket.create_connection((HOST, 19360), timeout=3) as raw,
                ctx.wrap_socket(raw, server_hostname=hostname),
            ):
                raise RuntimeError(f"TLS accepted {name}")
        except ssl.SSLCertVerificationError:
            result[name] = "rejected"
    return result


def wait_stream(path, process, probe):
    for attempt in range(30):
        if process.poll() is not None:
            raise RuntimeError(f"{path} publisher exited; inspect protected local log")
        try:
            return probe(path)
        except RuntimeError:
            if attempt == 29:
                raise
            time.sleep(0.5)
    raise RuntimeError(f"{path} did not become ready")


def verify_tracks(path, process, probe, tone):
    tracks = wait_stream(path, process, probe)
    require(
        sum(t["codec_type"] == "audio" for t in tracks) == 2,
        "transport lost an audio track",
    )
    return {
        "codecs": [t["codec_name"] for t in tracks],
        "audio_identity": [tone(path, 0, 440), tone(path, 1, 880)],
    }


def srt_url(path, passphrase, passwords, user="publisher"):
    params = {
        "streamid": f"publish:{path}:{user}:{passwords[user]}",
        "pkt_size": 1316,
        "connect_timeout": 2000,
        "timeout": 3000000,
        "enforced_encryption": 1,
        "pbkeylen": 32,
    }
    if passphrase is not None:
        params["passphrase"] = passphrase
    return "srt://127.0.0.1:18890?" + urlencode(params)


def verify_srt_denials(work, passwords, auth_events):
    result = {}
    # Valid muxing and a known reachable endpoint: only credentials vary.
    for name, phrase, user in [
        ("missing_encryption", None, "publisher"),
        ("wrong_encryption", "deliberately-wrong-test-passphrase", "publisher"),
        ("wrong_tenant", passwords["srt-encryption"], "reader-b"),
    ]:
        path = "a/denied-" + name
        args = [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-re",
            "-i",
            str(work / "pattern.mp4"),
            "-t",
            "1",
            "-c",
            "copy",
            "-f",
            "mpegts",
            srt_url(path, phrase, passwords, user),
        ]
        # Fixed executable and generated local URLs passed as argv without a shell.
        outcome = subprocess.run(  # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit
            args, capture_output=True, timeout=10, shell=False
        )
        require(outcome.returncode != 0, f"SRT accepted {name}")
        error = outcome.stderr.decode(errors="replace").lower()
        require(
            "input/output error" in error or "connection" in error,
            "unrelated SRT failure",
        )
        if name == "wrong_tenant":
            require(
                any(
                    e["path"] == path and e["protocol"] == "srt" and not e["allowed"]
                    for e in auth_events
                ),
                "auth boundary not reached",
            )
        result[name] = {"exit_code": outcome.returncode, "rejected": True}
    return result


def qualify(work, passwords, start, rtsp, probe, tone, auth_events):
    result = {"tls": check_tls(work / "server.crt")}
    source = [
        "ffmpeg",
        "-nostdin",
        "-v",
        "error",
        "-rtsp_transport",
        "tcp",
        "-i",
        rtsp("a/obs"),
        "-map",
        "0",
        "-c",
        "copy",
    ]
    tls_url = "rtmps://127.0.0.1:19360/a/tls?" + urlencode(
        {"user": "publisher", "pass": passwords["publisher"]}
    )
    tls_publisher = start(
        "tls-publisher",
        source
        + [
            "-tls_verify",
            "1",
            "-ca_file",
            str(work / "server.crt"),
            "-rtmp_enhanced_codecs",
            "avc1,mp4a",
            "-f",
            "flv",
            tls_url,
        ],
    )
    result["rtmps"] = verify_tracks(TLS_PATH, tls_publisher, probe, tone)
    encrypted_publisher = start(
        "srt-publisher",
        source
        + ["-f", "mpegts", srt_url(SRT_PATH, passwords["srt-encryption"], passwords)],
    )
    result["encrypted_srt"] = verify_tracks(SRT_PATH, encrypted_publisher, probe, tone)
    result["encrypted_srt"]["denials"] = verify_srt_denials(
        work, passwords, auth_events
    )
    return result
