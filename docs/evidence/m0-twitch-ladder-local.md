# M0 local test of the Twitch-negotiated ladder

Run: 2026-09-30 UTC. Source: `python3 scripts/m0-dual-canvas.py --twitch-ladder`.
The [unaltered report](m0-twitch-ladder-local.json) has status
`passed_local_twitch_ladder`; the default two-rendition fixture also passed
after the harness change. The [fixture configuration](../../tests/m0/twitch-ladder-local.json)
retains the encoder and audio settings from the account-specific GoLive response.
Its service, configuration ID and ingest endpoint are synthetic. It contains no
Twitch key or ingest authorization.

The harness created a user/network namespace, confirmed its only interface was
loopback and that both route tables were empty, then used OBS 32.2.2 with the
installed RTX 4090 NVENC encoder and Aitum vertical canvas. NVENC could not
initialize under the fixture's `bwrap` filesystem sandbox, so this mode ran OBS
directly in the network namespace with a private XDG configuration. The report
hashes the 30 installed OBS modules listed as loaded and verifies each binary's
mapped path through the OBS process, including the installed Aitum binary.
It sent synthetic
red horizontal video, blue vertical video, and separate 440 Hz live / 880 Hz VOD
audio to a loopback MediaMTX instance. FFmpeg copied the RTSP output to a second
loopback enhanced-RTMP sink. No Twitch or cloud endpoint was contacted.

The same isolated fixture also built the [bounded libavformat copy publisher](../../tests/m0/twitch_copy.c)
and sent all six streams to a separate loopback sink. The retained report records
its stream order, decoded identities, and two discarded startup packets per video
track that lacked timestamps. No subsequent timestamp gap was observed. The
[host bridge control](m0-twitch-copy-candidate.md) tests the complete local
runner that would supply the later broadcast.

The publisher now waits until all three BPM markers precede an IDR on each
track before opening its output. In the retained run it observed ten keyframes
per track, nine with a complete preceding BPM set, and started at the first
complete set. Its first outgoing keyframe PTS was 2000 ms on all four tracks.
The local sink decoded all four colors and both tones after this startup.

A loopback RTMP tap before MediaMTX counted 128 occurrences of each BPM UUID
from OBS in the retained run. The markers were also found downstream when
all video packets were scanned.

The OBS ingest and copy sink each exposed H.264 video in output order
640×360, 284×160, 720×1280, 360×640, followed by two AAC audio tracks. All
four video outputs retained their expected decoded color, both audio outputs
retained their expected tone, and the local FLV sample contained video track
IDs 0–3 and audio track IDs 0–1. The copy publisher omitted FFmpeg's optional
`rtmp_enhanced_codecs` connect hint in this run; the local sink accepted the
result. This only establishes local packaging behavior. It does not identify
why Twitch closed the earlier RTMPS connections or prove that omitting the hint
would fix external delivery.

The run used an isolated synthetic OBS profile and stopped OBS, MediaMTX,
FFmpeg and Xvfb on completion. It did not modify the owner's OBS profile. The
report contains source and loaded-module hashes and exact tool versions. Its
hardware and installed-plugin dependencies limit reproduction on another host.
The real
Twitch H/V viewer and live/VOD checks remain blocked as recorded in the
[bounded attempt report](m0-twitch-live-attempts.md).
