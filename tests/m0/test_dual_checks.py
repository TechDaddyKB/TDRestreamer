"""Negative controls for dual-canvas evidence; real media runs separately."""

import sys
import subprocess
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from m0_dual_checks import check_pixels, check_streams
from m0_flv_checks import check_flv_track_ids


def flv_tag(kind, payload):
    header = bytes([kind]) + len(payload).to_bytes(3, "big") + bytes(7)
    return header + payload + (len(payload) + 11).to_bytes(4, "big")


def four_track_flv():
    return b"FLV\x01\x05\0\0\0\x09\0\0\0\0" + b"".join(
        flv_tag(kind, payload)
        for kind, payload in [
            (9, b"\x17\x00\0"),
            (9, b"\x27\x01\0"),
            (9, b"\x96\x00avc1\x01\0"),
            (9, b"\xa6\x01avc1\x01\0"),
            (8, b"\xaf\x00\0"),
            (8, b"\xaf\x01\0"),
            (8, b"\x95\x00mp4a\x01\0"),
            (8, b"\x95\x01mp4a\x01\0"),
        ]
    )


class DualChecks(unittest.TestCase):
    def test_flv_track_ids_require_both_codecs_and_packets(self):
        sample = four_track_flv()
        self.assertEqual(check_flv_track_ids(sample)["video"]["1"], [0, 1])
        self.assertEqual(
            check_flv_track_ids(
                sample.replace(b"\xa6\x01avc1\x01", b"\xa6\x03avc1\x01")
            )["video"]["1"],
            [0, 3],
        )
        for invalid in (
            sample[:-1],
            sample.replace(b"avc1\x01", b"avc1\x02"),
            sample.replace(b"mp4a\x01", b"mp4a\x02"),
            sample.replace(b"\x96\x00avc1\x01", b"\x96\x00avc1\x00"),
            sample.replace(b"\x95\x00mp4a\x01", b"\x95\x00mp4a\x00"),
            sample.replace(b"\x96\x00avc1\x01", b"\x96\x01avc1\x01"),
            sample.replace(b"\x95\x01mp4a\x01", b"\x95\x02mp4a\x01"),
            sample.replace(b"\x96\x00avc1\x01", b"\x96\x00hvc1\x01"),
            sample + flv_tag(9, b"\x12\x00\0"),
            sample + flv_tag(8, b"\x2f\x00\0"),
        ):
            with self.assertRaises(RuntimeError):
                check_flv_track_ids(invalid)

    def test_controller_rejects_path_arguments_before_reading(self):
        controller = Path(__file__).with_name("dual-canvas.mjs")
        for value in ("../outside", "/etc/passwd", "a" * 11, "a" * 13, "g" * 12):
            result = subprocess.run(
                ["node", str(controller), value],
                capture_output=True,
                text=True,
                timeout=5,
                shell=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Invalid fixture run ID", result.stderr)

    def test_wrong_orientation_and_missing_audio_rejected(self):
        streams = [
            {"codec_type": "video", "codec_name": "h264", "width": 640, "height": 360},
            {"codec_type": "video", "codec_name": "h264", "width": 360, "height": 640},
            {"codec_type": "audio", "codec_name": "aac"},
            {"codec_type": "audio", "codec_name": "aac"},
        ]
        check_streams(streams)
        for invalid in (
            streams[1::-1] + streams[2:],
            streams[:-1],
            [streams[0], streams[2], streams[1], streams[3]],
        ):
            with self.assertRaises(RuntimeError):
                check_streams(invalid)

    def test_swapped_black_or_truncated_video_rejected(self):
        red = bytes([250, 0, 0]) * 10
        self.assertEqual(len(check_pixels(red, 0)), 10)
        for invalid in (bytes([0, 0, 250]) * 10, bytes(30), red[:-1]):
            with self.assertRaises(RuntimeError):
                check_pixels(invalid, 0)


if __name__ == "__main__":
    unittest.main()
