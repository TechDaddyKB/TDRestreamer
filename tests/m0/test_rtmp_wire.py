"""Verify bounded RTMP media summaries across handshake and chunk boundaries."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from m0_rtmp_wire import Inspector


def message(csid, kind, body, timestamp=0):
    return (bytes([csid]) + timestamp.to_bytes(3, "big") +
            len(body).to_bytes(3, "big") + bytes([kind]) +
            (1).to_bytes(4, "little") + body)


class WireInspectorTest(unittest.TestCase):
    def test_media_summary_omits_commands_and_payload(self):
        inspector = Inspector()
        command = b"private-stream-key"
        wire = (bytes(3073) + message(3, 20, command) +
                message(4, 9, b"\x17\x01\x00\x00\x00" + b"secret-payload", 33))
        for offset in range(0, len(wire), 7):
            inspector.feed(wire[offset:offset + 7])
        report = inspector.report()
        self.assertEqual(report["message_types"], {"20": 1, "9": 1})
        self.assertEqual(report["first_media_messages"][0]["timestamp_ms"], 33)
        self.assertNotIn("private-stream-key", str(report))
        self.assertNotIn("secret-payload", str(report))

    def test_chunked_message(self):
        inspector = Inspector()
        set_size = message(2, 1, (4).to_bytes(4, "big"))
        body = b"\x96\x01avc1\x01abcdef"
        header = bytes([4]) + (11).to_bytes(3, "big") + len(body).to_bytes(3, "big") + b"\x09" + (1).to_bytes(4, "little")
        wire = bytes(3073) + set_size + header + body[:4]
        for offset in range(4, len(body), 4):
            wire += b"\xc4" + body[offset:offset + 4]
        inspector.feed(wire)
        self.assertEqual(inspector.report()["first_media_messages"][0]["bytes"], len(body))

    def test_reused_headers_and_extended_timestamp(self):
        inspector = Inspector()
        body = b"\xaf\x01"
        first = message(4, 8, body, 0xFFFFFF)
        first = first[:12] + (0x1000000).to_bytes(4, "big") + first[12:]
        fmt1 = b"\x44\x00\x00\x21" + len(body).to_bytes(3, "big") + b"\x08" + body
        fmt2 = b"\x84\x00\x00\x22" + body
        fmt3 = b"\xc4" + body
        inspector.feed(bytes(3073) + first + fmt1 + fmt2 + fmt3)
        self.assertEqual([m["timestamp_ms"] for m in inspector.media],
                         [0x1000000, 0x1000021, 0x1000043, 0x1000065])

    def test_extended_chunk_stream_ids(self):
        inspector = Inspector()
        regular = message(4, 9, b"\x17")
        extended_one = b"\x00\x06" + regular[1:]
        extended_two = b"\x01\x01\x01" + regular[1:]
        inspector.feed(bytes(3073) + extended_one + extended_two)
        self.assertEqual(inspector.messages["9"], 2)

    def test_invalid_control_and_missing_header(self):
        with self.assertRaisesRegex(ValueError, "initial header"):
            Inspector().feed(bytes(3073) + b"\xc4")
        with self.assertRaisesRegex(ValueError, "out of bounds"):
            Inspector().feed(bytes(3073) + message(2, 1, bytes(4)))

    def test_media_sample_is_bounded(self):
        inspector = Inspector()
        inspector.feed(bytes(3073) + message(4, 9, b"\x17") * 100)
        self.assertEqual(inspector.messages["9"], 100)
        self.assertEqual(len(inspector.media), 96)


if __name__ == "__main__":
    unittest.main()
