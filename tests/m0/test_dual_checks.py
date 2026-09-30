"""Negative controls for dual-canvas evidence; real media runs separately."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from m0_dual_checks import check_pixels, check_streams


class DualChecks(unittest.TestCase):
    def test_wrong_orientation_and_missing_audio_rejected(self):
        streams = [
            {"codec_type": "video", "codec_name": "h264", "width": 640, "height": 360},
            {"codec_type": "video", "codec_name": "h264", "width": 360, "height": 640},
            {"codec_type": "audio", "codec_name": "aac"},
            {"codec_type": "audio", "codec_name": "aac"},
        ]
        check_streams(streams)
        for invalid in (streams[1::-1] + streams[2:], streams[:-1]):
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
