"""Count IVS BPM UUIDs in one loopback OBS RTMP hop without retaining media."""

import json
import select
import signal
import socket
import sys
from pathlib import Path

UUIDS = {
    "bpm_ts": bytes.fromhex("0aecffe752724e2fa62fd19cd61a93b5"),
    "bpm_sm": bytes.fromhex("ca60e71c6a8b4388a377151df7bf8ac2"),
    "bpm_erm": bytes.fromhex("f1fbc1d5101e4fb5a61eb8ce3c07b8c0"),
}
STOP = False


def stop(*_):
    global STOP
    STOP = True


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: m0_rtmp_tap.py <private-report-path>")
    report_path = Path(sys.argv[1])
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    report = {"connections": 0, "upstream_bytes": 0,
              "uuid_counts": {name: 0 for name in UUIDS}}
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 19350))
        listener.listen(4)
        listener.settimeout(0.5)
        while not STOP:
            try:
                client, _ = listener.accept()
            except socket.timeout:
                continue
            report["connections"] += 1
            with client, socket.create_connection(("127.0.0.1", 19351), timeout=3) as target:
                previous = b""
                while not STOP:
                    readable, _, _ = select.select([client, target], [], [], 0.5)
                    for source in readable:
                        data = source.recv(65536)
                        if not data:
                            break
                        if source is client:
                            report["upstream_bytes"] += len(data)
                            combined = previous + data
                            for name, marker in UUIDS.items():
                                report["uuid_counts"][name] += sum(
                                    combined[i:i + len(marker)] == marker
                                    for i in range(max(0, len(previous) - len(marker) + 1),
                                                   len(combined) - len(marker) + 1)
                                )
                            previous = combined[-15:]
                            target.sendall(data)
                        else:
                            client.sendall(data)
                    else:
                        continue
                    break
    report_path.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
