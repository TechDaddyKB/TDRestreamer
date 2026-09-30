"""Inspect bounded enhanced-FLV track headers from the local publisher muxer.

Track 0 uses legacy H.264/AAC headers; track 1 carries explicit enhanced-FLV
track IDs. This observes local muxer bytes, not Twitch's interpretation of them.
"""

from m0_protocols import require


def _observe_video(payload, observed):
    if payload[0] & 0x80 and payload[0] & 0x0F == 6:
        require(len(payload) >= 7, "truncated enhanced video header")
        require(payload[1] >> 4 == 0, "unsupported video multitrack mode")
        require(
            payload[2:6] == b"avc1" and payload[6] == 1,
            "video track ID or codec changed",
        )
        observed[("video", 1)].add(payload[1] & 0x0F)
    elif not payload[0] & 0x80:
        require(payload[0] & 0x0F == 7, "unexpected legacy video codec")
        require(len(payload) >= 2, "truncated legacy video header")
        observed[("video", 0)].add(payload[1])
    else:
        require(False, "unexpected enhanced video header")


def _observe_audio(payload, observed):
    if payload[0] == 0x95:
        require(len(payload) >= 7, "truncated enhanced audio header")
        require(payload[1] >> 4 == 0, "unsupported audio multitrack mode")
        require(
            payload[2:6] == b"mp4a" and payload[6] == 1,
            "audio track ID or codec changed",
        )
        observed[("audio", 1)].add(payload[1] & 0x0F)
    elif payload[0] >> 4 == 10:
        require(len(payload) >= 2, "truncated legacy audio header")
        observed[("audio", 0)].add(payload[1])
    else:
        require(False, "unexpected audio codec or header")


def _require_tracks(observed):
    for kind in ("video", "audio"):
        for track in (0, 1):
            require(
                {0, 1}.issubset(observed[(kind, track)])
                or (
                    kind == "video"
                    and track == 1
                    and {0, 3}.issubset(observed[(kind, track)])
                ),
                f"missing {kind} sequence or coded frames for track {track}",
            )


def check_flv_track_ids(data):
    require(13 <= len(data) <= 8 * 1024 * 1024, "FLV sample size out of bounds")
    require(data[:3] == b"FLV" and data[3] == 1, "invalid FLV header")
    offset = int.from_bytes(data[5:9], "big")
    require(9 <= offset <= len(data) - 4, "invalid FLV data offset")
    require(data[offset : offset + 4] == b"\0\0\0\0", "invalid first tag size")
    position = offset + 4
    observed = {(kind, track): set() for kind in ("video", "audio") for track in (0, 1)}
    while position < len(data):
        require(len(data) - position >= 15, "truncated FLV tag")
        tag_type = data[position]
        size = int.from_bytes(data[position + 1 : position + 4], "big")
        end = position + 11 + size
        require(end + 4 <= len(data) and size > 0, "truncated FLV payload")
        require(
            int.from_bytes(data[end : end + 4], "big") == size + 11,
            "invalid previous-tag size",
        )
        payload = data[position + 11 : end]
        if tag_type == 9:
            _observe_video(payload, observed)
        elif tag_type == 8:
            _observe_audio(payload, observed)
        position = end + 4
    require(position == len(data), "FLV tag boundary mismatch")
    _require_tracks(observed)
    return {
        kind: {str(track): sorted(observed[(kind, track)]) for track in (0, 1)}
        for kind in ("video", "audio")
    }
