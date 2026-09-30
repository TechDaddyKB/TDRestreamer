"""Fail-closed assertions for the real dual-canvas media fixture."""

from m0_protocols import require


def check_streams(streams):
    videos = [s for s in streams if s.get("codec_type") == "video"]
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    require(len(streams) == 4, "expected exactly two video and two audio tracks")
    require(
        [(s.get("codec_name"), s.get("width"), s.get("height")) for s in videos]
        == [("h264", 640, 360), ("h264", 360, 640)],
        "horizontal/vertical video order, codec or geometry changed",
    )
    require(
        [s.get("codec_name") for s in audios] == ["aac", "aac"], "audio tracks changed"
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
