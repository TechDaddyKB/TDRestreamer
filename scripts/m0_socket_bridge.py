"""Private Unix-socket bridge for the isolated M0 RTSP source.

Only the host-side listener binds TCP, and only on 127.0.0.1. The OBS-side
process remains in a network namespace with no external route.
"""

import select
import socket
import time


def forward(left, right, stop):
    with left, right:
        left.settimeout(1)
        right.settimeout(1)
        while not stop():
            readable, _, _ = select.select((left, right), (), (), 0.25)
            for source in readable:
                try:
                    data = source.recv(65536)
                    if not data:
                        return
                    target = right if source is left else left
                    target.sendall(data)
                except (OSError, TimeoutError):
                    return


def serve_unix_to_tcp(path, stop, seconds=300):
    deadline = time.monotonic() + seconds
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
        listener.bind(str(path))
        path.chmod(0o600)
        listener.listen(2)
        listener.settimeout(0.25)
        print(f"M0_SOURCE_READY {path}", flush=True)
        while not stop() and time.monotonic() < deadline:
            try:
                client, _ = listener.accept()
            except socket.timeout:
                continue
            try:
                upstream = socket.create_connection(("127.0.0.1", 18555), timeout=2)
            except OSError:
                client.close()
                continue
            forward(client, upstream, stop)
    path.unlink(missing_ok=True)


def serve_tcp_to_unix(path, stop, ready):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 18556))
        listener.listen(2)
        listener.settimeout(0.25)
        ready.set()
        while not stop():
            try:
                client, _ = listener.accept()
            except socket.timeout:
                continue
            try:
                upstream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                upstream.settimeout(2)
                upstream.connect(str(path))
            except OSError:
                client.close()
                continue
            forward(client, upstream, stop)
