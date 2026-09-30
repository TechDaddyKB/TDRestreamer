"""Bounded, credential-free summary of client-to-server RTMP media messages."""

from collections import Counter


class Inspector:
    def __init__(self):
        self.buffer = bytearray()
        self.handshake = 3073
        self.chunk_size = 128
        self.streams = {}
        self.messages = Counter()
        self.media = []

    def feed(self, data):
        self.buffer.extend(data)
        while self.handshake:
            take = min(self.handshake, len(self.buffer))
            del self.buffer[:take]
            self.handshake -= take
            if self.handshake:
                return
        while self.buffer:
            first = self.buffer[0]
            fmt, csid = first >> 6, first & 63
            prefix = 1 + (1 if csid == 0 else 2 if csid == 1 else 0)
            if len(self.buffer) < prefix:
                return
            if csid == 0:
                csid = self.buffer[1] + 64
            elif csid == 1:
                csid = self.buffer[1] + self.buffer[2] * 256 + 64
            state = self.streams.get(csid)
            length = (11, 7, 3, 0)[fmt]
            if state is None and fmt != 0:
                raise ValueError("RTMP chunk without initial header")
            if len(self.buffer) < prefix + length:
                return
            header = self.buffer[prefix:prefix + length]
            raw_time = int.from_bytes(header[:3], "big") if length else state["raw_time"]
            extended = raw_time == 0xFFFFFF
            end_header = prefix + length + (4 if extended else 0)
            if len(self.buffer) < end_header:
                return
            time_value = int.from_bytes(self.buffer[prefix + length:end_header], "big") if extended else raw_time
            if fmt == 0:
                state = {"time": time_value, "delta": 0,
                         "size": int.from_bytes(header[3:6], "big"),
                         "type": header[6], "stream_id": int.from_bytes(header[7:11], "little"),
                         "raw_time": raw_time, "body": bytearray()}
                self.streams[csid] = state
            elif fmt in (1, 2):
                state["delta"] = time_value
                state["time"] += time_value
                state["raw_time"] = raw_time
                if fmt == 1:
                    state["size"] = int.from_bytes(header[3:6], "big")
                    state["type"] = header[6]
                state["body"].clear()
            elif not state["body"]:
                state["time"] += state["delta"]
            remaining = state["size"] - len(state["body"])
            take = min(self.chunk_size, remaining)
            if len(self.buffer) < end_header + take:
                return
            state["body"].extend(self.buffer[end_header:end_header + take])
            del self.buffer[:end_header + take]
            if len(state["body"]) == state["size"]:
                self._message(state)
                state["body"].clear()

    def _message(self, state):
        kind = state["type"]
        self.messages[str(kind)] += 1
        body = state["body"]
        if kind == 1 and len(body) == 4:
            value = int.from_bytes(body, "big")
            if not 1 <= value <= 1024 * 1024:
                raise ValueError("RTMP chunk size out of bounds")
            self.chunk_size = value
        if kind in (8, 9) and len(self.media) < 96:
            self.media.append({"type": "audio" if kind == 8 else "video",
                               "timestamp_ms": state["time"], "bytes": len(body),
                               "header_hex": bytes(body[:8]).hex()})

    def report(self):
        return {"message_types": dict(self.messages),
                "first_media_messages": self.media}
