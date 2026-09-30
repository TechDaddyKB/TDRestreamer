"""Contract checks for the local OBS/Twitch negotiation handoff."""

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from m0_twitch_config import UnsupportedConfiguration, inspect_config, local_obs_config


def example():
    return {
        "meta": {"service": "IVS", "schema_version": "2025-01-25", "config_id": "fixture"},
        "status": {"result": "success"},
        "ingest_endpoints": [
            {"protocol": "RTMPS", "url_template": "rtmps://example.invalid/app/{stream_key}",
             "authentication": "remote-secret"}
        ],
        "encoder_configurations": [
            {"type": "obs_x264", "canvas_index": 0, "width": 640, "height": 360},
            {"type": "obs_x264", "canvas_index": 1, "width": 360, "height": 640},
        ],
        "audio_configurations": {
            "live": [{"codec": "aac", "track_id": 0, "channels": 2}],
            "vod": [{"codec": "aac", "track_id": 1, "channels": 2}],
        },
    }


class ConfigTests(unittest.TestCase):
    def test_ordered_hv_and_audio_mapping(self):
        config = example()
        local, mapping = local_obs_config(config, 19351, "local-only-key-longer-than-24")
        self.assertEqual([v["orientation"] for v in mapping["video"]],
                         ["horizontal", "vertical"])
        self.assertEqual([a["role"] for a in mapping["audio"]], ["live", "vod"])
        self.assertEqual(len(local["ingest_endpoints"]), 1)
        self.assertEqual(local["ingest_endpoints"][0]["protocol"], "RTMP")
        self.assertIn("127.0.0.1:19351", local["ingest_endpoints"][0]["url_template"])
        self.assertNotIn("remote-secret", str(local))
        self.assertIn("remote-secret", str(config))

    def test_rejects_misleading_or_unrelayable_responses(self):
        changes = [
            lambda c: c["meta"].update(schema_version="new"),
            lambda c: c.update(status="success"),
            lambda c: c["status"].update(result="warning"),
            lambda c: c["ingest_endpoints"][0].update(protocol="RTMP"),
            lambda c: c["encoder_configurations"].pop(),
            lambda c: c["encoder_configurations"][1].update(canvas_index=0),
            lambda c: c["encoder_configurations"][1].update(width=640, height=360),
            lambda c: c["audio_configurations"].pop("vod"),
            lambda c: c["audio_configurations"]["vod"][0].update(track_id=0),
            lambda c: c["audio_configurations"]["live"][0].update(track_id=False),
            lambda c: c["audio_configurations"]["live"][0].update(codec="opus"),
        ]
        for change in changes:
            config = copy.deepcopy(example())
            change(config)
            with self.subTest(change=change), self.assertRaises(UnsupportedConfiguration):
                inspect_config(config)


if __name__ == "__main__":
    unittest.main()
