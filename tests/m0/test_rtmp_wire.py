"""Verify bounded RTMP media summaries across handshake and chunk boundaries."""

import sys
import struct
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

    def test_fmt_zero_time_is_reused_by_next_fmt_three_message(self):
        inspector = Inspector()
        inspector.feed(bytes(3073) + message(4, 9, b"\x17", 42) + b"\xc4\x27")
        self.assertEqual([m["timestamp_ms"] for m in inspector.media], [42, 84])

    def test_invalid_control_and_missing_header(self):
        inspector = Inspector()
        missing_header = bytes(3073) + b"\xc4"
        with self.assertRaisesRegex(ValueError, "initial header"):
            inspector.feed(missing_header)
        inspector = Inspector()
        invalid_control = bytes(3073) + message(2, 1, bytes(4))
        with self.assertRaisesRegex(ValueError, "out of bounds"):
            inspector.feed(invalid_control)

    def test_media_sample_is_bounded(self):
        inspector = Inspector()
        inspector.feed(bytes(3073) + message(4, 9, b"\x17") * 100)
        self.assertEqual(inspector.messages["9"], 100)
        self.assertEqual(len(inspector.media), 96)

    def test_control_summary_records_field_names_without_values(self):
        inspector = Inspector()
        connect = (b"\x02\x00\x07connect" + b"\x00" * 8 +
                   b"\x00\x03app\x02\x00\x12private-stream-key" +
                   b"\x00\x05tcUrl\x02\x00\x12private-stream-key")
        metadata = (b"\x00\x07encoder\x00\x09framerate\x00" +
                    struct.pack(">d", 30.0))
        inspector.feed(bytes(3073) + message(3, 20, connect) +
                       message(4, 18, metadata))
        summary = inspector.report()
        self.assertEqual(summary["first_message_types"], [20, 18])
        self.assertEqual(summary["control_fields"][0],
                         {"type": 20, "command": "connect", "fields": ["app", "tcUrl"],
                          "numeric": {}})
        self.assertEqual(summary["control_fields"][1]["fields"],
                         ["encoder", "framerate"])
        self.assertEqual(summary["control_fields"][1]["numeric"], {"framerate": 30.0})
        self.assertNotIn("private-stream-key", str(summary))


if __name__ == "__main__":
    unittest.main()
