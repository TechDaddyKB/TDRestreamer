"""Fail-closed assertions for the real dual-canvas media fixture."""

from m0_protocols import require


def check_streams(streams, expected=None):
    if expected is None:
        expected = [
            ("video", "h264", 640, 360),
            ("video", "h264", 360, 640),
            ("audio", "aac", None, None),
            ("audio", "aac", None, None),
        ]
    require(
        [
            (s.get("codec_type"), s.get("codec_name"), s.get("width"), s.get("height"))
            for s in streams
        ]
        == expected,
        "complete stream order, count, codec or geometry changed",
    )


def check_pixels(rgb, channel):
    require(len(rgb) == 30, "expected ten decoded RGB samples")
    require(channel in (0, 2), "unknown video identity")
    samples = [rgb[i : i + 3] for i in range(0, len(rgb), 3)]
    require(
        all(
            s[channel] > 200 and all(s[c] < 40 for c in range(3) if c != channel)
            for s in samples
        ),
        "decoded video identity changed",
    )
    return [list(s) for s in samples]
