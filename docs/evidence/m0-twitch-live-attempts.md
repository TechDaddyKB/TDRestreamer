# M0 Twitch negotiation and bounded publish attempts

Observed 2026-09-30 UTC. **M0 did not pass.** The owner separately approved at
most two public synthetic TechDaddy broadcasts of five minutes each, at no more
than 6 Mbps aggregate nominal media bitrate. Both attempts were used. This
approval did not cover a third attempt, any cloud deployment, or account-setting
changes.

## Negotiation and local control

The TechDaddy dashboard showed Dual Format eligible before the run. A stream key
was copied into the local Secret Service keyring without printing it. A request
following OBS 32.2.2's `2025-01-25` GoLive schema received HTTP 200. Requests
without GPU information and with only two total video tracks returned explicit
errors. With the actual RTX 4090 capability and four requested video tracks,
Twitch supplied a configuration with:

| OBS output order | Canvas | H.264 size |
|---:|---|---:|
| 0 | Horizontal | 640 × 360 |
| 1 | Horizontal | 284 × 160 |
| 2 | Vertical | 720 × 1280 |
| 3 | Vertical | 360 × 640 |

It also specified AAC live track 0 and AAC VOD track 1. The four video and two
audio bitrate settings totaled **4,720 kbps**. The response offered RTMP and
RTMPS ingest and passed the [offline config guard](../../scripts/m0_twitch_config.py).
This is account-specific negotiation evidence, not delivery evidence.

Using the returned encoder settings and a loopback-only OBS override, a separate
synthetic OBS profile published four H.264 video and two AAC audio streams through
MediaMTX RTSP. An FFmpeg enhanced-RTMP copy publisher preserved all six streams
at a second loopback sink. Decoded samples retained red horizontal and blue
vertical source identity; live/VOD audio retained distinct 440/880 Hz tones.
This control used the negotiated ladder, but the sink was local.

## External attempts and result

| Attempt | Started UTC | Publisher | Result |
|---|---|---|---|
| 1 | 20:00:28 | FFmpeg copy to Twitch RTMPS using the negotiated endpoint and configuration ID | Exited almost immediately; no remote diagnostic was retained |
| 2 | 20:04:44 | Same media with explicit FFmpeg RTMP app/playpath options, first verified at a local sink | Exited during RTMPS writing; sanitized stderr showed a TLS broken pipe |

Neither attempt produced a Helix live-stream result. After each failure, the
harness stopped OBS, MediaMTX and FFmpeg. A final check found the channel offline,
no test listeners, and no video in Video Producer's current All Videos view.
No horizontal/vertical viewer playback or live/VOD audio behavior was observed.
The broken pipe does not identify whether Twitch rejected authentication,
metadata, track packaging or some other part of the publish path.

The exploratory live runners and their raw reports remain private/ignored. Their
source was not committed, so the live observations are a **diagnostic record**, not
a reproducible passing qualification artifact. A later
[reproducible local ladder fixture](m0-twitch-ladder-local.md) uses the sanitized
encoder settings but cannot establish Twitch ingest acceptance. The negotiated response, which
contained an ingest credential, was removed from temporary memory storage after
the attempts. No stream key, response, endpoint authentication or unredacted
publisher log is committed.

## M0 blocker

The appliance copy-publisher has not demonstrated Twitch Enhanced Broadcasting
delivery. Its FLV/RTMP wire behavior must be compared with OBS's negotiated
publisher path, and a reproducible bounded live harness must be retained before a
further live qualification. Any additional broadcast requires separate owner
approval. Do not infer Twitch H/V support or live/VOD correctness from the
successful negotiation and local fixture.
