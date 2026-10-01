# M0 Twitch negotiation and bounded publish attempts

Observed 2026-09-30 through 2026-10-01 UTC. **M0 did not pass.** The owner initially approved at
most two public synthetic TechDaddy broadcasts of five minutes each, at no more
than 6 Mbps aggregate nominal media bitrate. Both attempts were used. This
approval did not cover a third attempt. The owner later authorized any further
broadcast testing needed for this goal. Cloud deployment and account-setting
changes remain outside that authorization.

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
| 3 | 21:21:31 | [Bounded libavformat publisher](m0-twitch-copy-candidate.md), after a passing route-free local six-stream bridge control | RTMPS media write returned EOF after about two seconds; [sanitized report](m0-twitch-third-attempt.json) records Helix never live and channel offline after stop |
| 4 | 22:00:44 | Same publisher after BPM-aware startup and aligned outgoing first IDRs | RTMPS media write returned broken pipe after about three seconds; [sanitized report](m0-twitch-fourth-attempt.json) records Helix never live and channel offline after stop |
| 5 | 22:09:18 | Same startup with primary H.264 converted to enhanced single-track `avc1` FLV tags | RTMPS media write returned EOF after about four seconds; [sanitized report](m0-twitch-fifth-attempt.json) records Helix never live and channel offline after stop |
| 6 | 22:44:07 | [Direct isolated OBS control](m0-twitch-obs-control.md), 90 seconds | Helix live and public red horizontal playback; 1:30 VOD with 880 Hz audio |
| 7 | 22:48:14 | Same direct OBS control, 150 seconds | Helix live; dashboard showed horizontal and vertical renditions, red H and blue V viewer previews; graceful stop and offline check passed |
| 8 | 23:01:37 | Direct OBS control, 30-second smoke after WebSocket password-handoff change | Helix live, graceful OBS stop and offline check passed; [sanitized report](m0-twitch-obs-control-smoke.json) |
| 9 | 23:31:05 | Copy publisher with first outgoing keyframes rebased to 0 ms after a passing local six-stream control | RTMPS write returned broken pipe after four seconds; Helix never live and channel offline after cleanup. The [wire comparison](m0-rtmp-wire-comparison.json) retains sanitized local header evidence |
| 10 | 2026-10-01 00:18:26 | Copy publisher with BPM SEI NALs merged into each first IDR, after local six-stream and decoded identity controls | RTMPS write failed after five seconds; Helix never live and channel returned offline. [Sanitized report](m0-twitch-sei-merge.json) |
| 11 | 2026-10-01 00:42:04 | Direct OBS control, 300-second cap, with public live HLS audio sample | Helix live; public horizontal 256×144 rendition showed red video and 440 Hz audio at 40 and 80 seconds after a pre-roll ad; 880 Hz was below displayed precision. Graceful stop and offline check passed. [Control](m0-twitch-obs-control-live-audio.json), [audio analysis](m0-twitch-live-audio.json) |

None of the seven **copy-publisher** attempts produced a Helix live-stream result.
After each copy failure, the harness stopped OBS, MediaMTX and FFmpeg. Direct
OBS attempts 6 and 7 then proved that the same channel and negotiated ladder
can go live and deliver H/V scenes. The [control record](m0-twitch-obs-control.md)
also establishes an 880 Hz VOD sample and 440 Hz live audio in a public
horizontal rendition.
The copy disconnects do not identify which ingest requirement was rejected.
The local wire comparison found that the earlier copy path first emitted coded
video without an IDR and placed its first IDRs at 2000 ms, while OBS began with
IDRs at 0 ms. The revised copy path places all four first IDRs at 0 ms, but
still emits coded non-key video before them at that timestamp and differs from
OBS in audio setup packets. Attempt 9 demonstrates that timestamp rebasing
alone did not fix Twitch ingest. Attempt 10 then moved the BPM SEI NALs into
the initial key packet for each rendition, so the local wire started coded
video with IDRs at 0 ms while retaining the three BPM UUIDs per track. The
full local ladder decoded the expected colors and separate audio tones. This
also failed at Twitch ingest, so the initial keyframe ordering was not the
sole rejection cause.

The first two exploratory live runners and their raw reports remain private/ignored. Their
source was not committed, so those observations are a **diagnostic record**, not
a reproducible passing qualification artifact. A later
[reproducible local ladder fixture](m0-twitch-ladder-local.md) uses the sanitized
encoder settings but cannot establish Twitch ingest acceptance. The negotiated response, which
contained an ingest credential, was removed from temporary memory storage after
the first two attempts. The retained bounded runner keeps no negotiated response. No stream key, response, endpoint authentication or unredacted
publisher log is committed.

## M0 blocker

The appliance copy-publisher has not demonstrated Twitch Enhanced Broadcasting
delivery. Its remaining FLV/RTMP wire behavior and per-track negotiated settings
must be compared with the successful direct OBS publisher path before a further
copy-path live qualification. The owner has authorized further necessary
broadcast tests. Direct OBS H/V delivery and VOD audio do not establish that
the appliance relay behaves correctly.
