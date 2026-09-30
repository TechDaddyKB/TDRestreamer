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
        self._consume_handshake()
        if self.handshake:
            return
        while self.buffer:
            if not self._consume_chunk():
                return

    def _consume_handshake(self):
        take = min(self.handshake, len(self.buffer))
        del self.buffer[:take]
        self.handshake -= take

    def _chunk_identity(self):
        first = self.buffer[0]
        fmt, csid = first >> 6, first & 63
        prefix = 1
        if csid == 0:
            prefix = 2
        elif csid == 1:
            prefix = 3
        if len(self.buffer) < prefix:
            return None
        if csid == 0:
            csid = self.buffer[1] + 64
        elif csid == 1:
            csid = self.buffer[1] + self.buffer[2] * 256 + 64
        return fmt, csid, prefix

    def _chunk_header(self, fmt, csid, prefix):
        state = self.streams.get(csid)
        length = (11, 7, 3, 0)[fmt]
        if state is None:
            if fmt != 0:
                raise ValueError("RTMP chunk without initial header")
            state = {"raw_time": 0}
        if len(self.buffer) < prefix + length:
            return None
        header = self.buffer[prefix:prefix + length]
        raw_time = int.from_bytes(header[:3], "big") if length else state["raw_time"]
        end = prefix + length + (4 if raw_time == 0xFFFFFF else 0)
        if len(self.buffer) < end:
            return None
        time_value = (int.from_bytes(self.buffer[prefix + length:end], "big")
                      if raw_time == 0xFFFFFF else raw_time)
        return state, header, raw_time, time_value, end

    def _update_state(self, fmt, csid, state, header, raw_time, time_value):
        if fmt == 0:
            state = {"time": time_value, "delta": 0,
                     "size": int.from_bytes(header[3:6], "big"),
                     "type": header[6], "raw_time": raw_time,
                     "body": bytearray()}
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
        return state

    def _consume_chunk(self):
        identity = self._chunk_identity()
        if identity is None:
            return False
        fmt, csid, prefix = identity
        parsed = self._chunk_header(fmt, csid, prefix)
        if parsed is None:
            return False
        state, header, raw_time, time_value, end = parsed
        size = int.from_bytes(header[3:6], "big") if fmt in (0, 1) else state["size"]
        have = len(state["body"]) if fmt == 3 else 0
        take = min(self.chunk_size, size - have)
        if len(self.buffer) < end + take:
            return False
        state = self._update_state(fmt, csid, state, header, raw_time, time_value)
        state["body"].extend(self.buffer[end:end + take])
        del self.buffer[:end + take]
        if len(state["body"]) == state["size"]:
            self._message(state)
            state["body"].clear()
        return True

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
