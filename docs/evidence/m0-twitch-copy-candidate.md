# M0 bounded Twitch copy-publisher candidate

Run: 2026-09-30 UTC. **Local control passed; Twitch delivery remains unverified.**
The [unaltered bridge report](m0-twitch-bridge-local.json) records
`passed_local_bridge` with six streams at its loopback sink. The
[isolated ladder report](m0-twitch-ladder-local.json) records four H.264
renditions and separate AAC live/VOD tracks, preserving decoded colors and
tones through the [copy publisher](../../tests/m0/twitch_copy.c).

The default [runner](../../tests/m0/twitch_live.py) uses synthetic OBS sources
inside a user/network namespace with loopback as its only interface and empty
IPv4/IPv6 route tables. A private Unix socket carries RTSP to a host-side bridge
that listens only on `127.0.0.1:18556`. The runner copies RTSP to a second local
MediaMTX sink and probes its six tracks. It does not access the keyring or Twitch
in this mode. It stopped OBS, the bridge and both local media services after the
test; the test ports had no listeners afterward.

The copy publisher accepts only the test RTSP endpoints and the local sink or
Twitch's observed RTMPS ingest host. It reads the ingest playpath from stdin,
limits runtime to 300 seconds, verifies TLS for RTMPS, and omits FFmpeg's
optional RTMP `fourCcList` connect hint. Its local control discarded two
untimestamped startup packets from each video stream and reported no later
timestamp gap. The publisher waits for a complete BPM set before an IDR on
every video track, starts all four output renditions at the same PTS, and
includes both audio tracks at the start. A small FLV filter changes the
primary H.264 rendition from FFmpeg's legacy AVC tags to enhanced RTMP
single-track `avc1` tags, matching the IVS packaging requirement. The local
ladder report recorded 572 transformed primary tags and aligned first output
keyframes at 2000 ms.

`--broadcast` is a separate runner mode. It checks that the channel is offline,
obtains account-specific negotiation, requires an exact match to the locally
qualified encoder/audio settings and RTMPS endpoint, caps negotiated nominal
bitrate at 6000 kbps, then runs one bounded publisher. Its report has no stream
key, ingest authorization or token. The owner authorized the remaining
necessary broadcast tests. Three bounded runs of this publisher are retained in
the [attempt record](m0-twitch-live-attempts.md). The latest, with BPM-aware
startup and enhanced primary tags, still ended at Twitch ingest after roughly
four seconds. Helix never reported the channel live, and the channel was
offline after cleanup. The local controls passed in those runs.

Actual horizontal and vertical viewer playback in one broadcast
and live/VOD audio identity must be checked. A local sink result, Helix live
state, or a successful publisher exit alone cannot close those M0 gates.

The [Amazon IVS multitrack integration guide](https://docs.aws.amazon.com/ivs/latest/LowLatencyUserGuide/multitrack-video-sw-integration.html)
lists mismatched per-track frame rate/bitrate, unaligned IDRs, and missing BPM
SEI before IDRs among possible disconnect causes. The publisher now skips the
initial incomplete GOP and normalizes the first complete IDR timestamps; this
passed local decode and stream checks. Per-track measured frame rate and bitrate
and the exact downstream FLV/RTMP packet sequence still need independent checks.
The external disconnect does not isolate the remaining mismatch.

A byte-counting tap before MediaMTX recorded 128 occurrences of each BPM UUID
from OBS's plaintext loopback RTMP stream in an [isolated ladder run](m0-twitch-ladder-local.json).
The copy publisher observed the markers in separate video packets. The tap
retained counts only, not media or RTMP messages. A local attempt to read the
same MediaMTX stream through RTMP instead exposed fewer than the expected six
tracks, so that reader path did not solve the startup problem.
