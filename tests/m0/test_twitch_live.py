"""Fail-closed controls for the bounded Twitch qualification runner."""

import json
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import twitch_live


FIXTURE = Path(__file__).with_name("twitch-ladder-local.json")


class Response:
    status = 200

    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, limit):
        return self.body[:limit]


def account_response():
    config = json.loads(FIXTURE.read_text())
    config["meta"] = {"service": "IVS", "schema_version": "2025-01-25",
                      "config_id": "11111111-2222-3333-4444-555555555555"}
    config["ingest_endpoints"] = [{
        "protocol": "RTMPS",
        "url_template": twitch_live.TWITCH_DESTINATION + "/{stream_key}",
        "authentication": "a" * 40,
    }]
    return config


class NegotiationControls(unittest.TestCase):
    def negotiate(self, config):
        with patch.object(twitch_live.sp, "check_output", return_value=b"GPU, 0x268410DE, 24564, 610.57.04\n"), \
             patch.object(twitch_live, "urlopen", return_value=Response(json.dumps(config).encode())):
            return twitch_live.negotiate("synthetic-key")

    def test_qualified_response_selects_one_endpoint_within_cap(self):
        playpath, bitrate = self.negotiate(account_response())
        self.assertEqual(bitrate, 4720)
        self.assertEqual(playpath, "a" * 40 + "?clientConfigId=11111111-2222-3333-4444-555555555555")

    def test_changed_endpoint_ladder_or_bitrate_fails_before_publish(self):
        for change in ("endpoint", "ladder", "bitrate"):
            config = deepcopy(account_response())
            if change == "endpoint":
                config["ingest_endpoints"][0]["url_template"] = "rtmps://other.invalid/app/{stream_key}"
            elif change == "ladder":
                config["encoder_configurations"][0]["width"] = 800
            else:
                config["encoder_configurations"][0]["settings"]["bitrate"] = 7000
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                self.negotiate(config)

    def test_broadcast_preflight_rejects_missing_bpm_and_unaligned_idrs(self):
        diagnostics = {"keyframes": [2] * 4, "bpm_ts": [2] * 4,
                       "bpm_sm": [2] * 4, "bpm_erm": [2] * 4,
                       "keyframes_with_bpm": [2] * 4,
                       "enhanced_primary_tags": 10,
                       "first_output_key_pts_ms": [2000] * 4}
        twitch_live.require_broadcast_ready(diagnostics)
        diagnostics["keyframes_with_bpm"][2] = 0
        with self.assertRaisesRegex(RuntimeError, "BPM"):
            twitch_live.require_broadcast_ready(diagnostics)
        diagnostics["keyframes_with_bpm"][2] = 2
        diagnostics["first_output_key_pts_ms"][3] = 2049
        with self.assertRaisesRegex(RuntimeError, "IDRs"):
            twitch_live.require_broadcast_ready(diagnostics)


if __name__ == "__main__":
    unittest.main()
