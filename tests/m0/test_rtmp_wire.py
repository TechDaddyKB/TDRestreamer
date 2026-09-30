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


if __name__ == "__main__":
    unittest.main()
