"""Fail-closed checks for an OBS 32.2.2 Twitch GoLive configuration.

The response may contain a stream key. Callers must keep it in private runtime
storage and must never log the input or the returned configuration.
"""

from copy import deepcopy

SCHEMA_VERSION = "2025-01-25"


class UnsupportedConfiguration(ValueError):
    """The response cannot be relayed by the qualified M0 copy path."""


def _require(condition, reason):
    if not condition:
        raise UnsupportedConfiguration(reason)


def inspect_config(config):
    """Return credential-free track mapping or reject an unqualified response."""
    _require(isinstance(config, dict), "configuration_shape")
    meta = config.get("meta")
    _require(isinstance(meta, dict), "meta_shape")
    _require(all(isinstance(meta.get(k), str) for k in ("service", "config_id")), "meta_fields")
    _require(meta.get("schema_version") == SCHEMA_VERSION, "schema_version")
    status = config.get("status")
    _require(status is None or (isinstance(status, dict) and status.get("result") == "success"), "status")

    endpoints = config.get("ingest_endpoints")
    _require(isinstance(endpoints, list) and endpoints, "endpoints")
    _require(
        any(
            isinstance(e, dict)
            and e.get("protocol") in ("RTMP", "RTMPS")
            and isinstance(e.get("url_template"), str)
            and e["url_template"].startswith(e["protocol"].lower() + "://")
            for e in endpoints
        ),
        "rtmp_endpoint",
    )

    videos = config.get("encoder_configurations")
    _require(isinstance(videos, list) and len(videos) >= 2, "video_count")
    mapping = []
    seen_canvases = set()
    for index, video in enumerate(videos):
        _require(isinstance(video, dict), "video_shape")
        canvas = video.get("canvas_index")
        width, height = video.get("width"), video.get("height")
        _require(type(canvas) is int and canvas in (0, 1), "canvas_index")
        _require(type(width) is int and width > 0, "video_width")
        _require(type(height) is int and height > 0, "video_height")
        _require(width > height if canvas == 0 else height > width, "orientation")
        seen_canvases.add(canvas)
        mapping.append(
            {
                "output_index": index,
                "canvas_index": canvas,
                "orientation": "horizontal" if canvas == 0 else "vertical",
                "width": width,
                "height": height,
            }
        )
    _require(seen_canvases == {0, 1}, "both_canvases")

    audio = config.get("audio_configurations")
    _require(isinstance(audio, dict), "audio_shape")
    tracks = []
    for output_index, role in enumerate(("live", "vod")):
        group = audio.get(role)
        _require(isinstance(group, list) and len(group) == 1, f"{role}_count")
        entry = group[0]
        _require(isinstance(entry, dict), f"{role}_shape")
        _require(entry.get("codec") == "aac", f"{role}_codec")
        _require(type(entry.get("track_id")) is int and entry["track_id"] == output_index,
                 f"{role}_track_id")
        tracks.append({"output_index": output_index, "role": role})

    return {"video": mapping, "audio": tracks, "schema_version": SCHEMA_VERSION}


def local_obs_config(config, port, local_key):
    """Replace every external ingest endpoint with one isolated loopback sink."""
    mapping = inspect_config(config)
    _require(type(port) is int and 1024 <= port <= 65535, "local_port")
    _require(isinstance(local_key, str) and len(local_key) >= 24, "local_key")
    local = {
        "meta": {
            name: config["meta"][name]
            for name in ("service", "schema_version", "config_id")
        },
        "ingest_endpoints": [
            {
                "protocol": "RTMP",
                "url_template": f"rtmp://127.0.0.1:{port}/dual/{{stream_key}}",
                "authentication": local_key,
            }
        ],
        "encoder_configurations": deepcopy(config["encoder_configurations"]),
        "audio_configurations": deepcopy(config["audio_configurations"]),
    }
    return local, mapping
