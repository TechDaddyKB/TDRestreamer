# M0 local RTMP wire comparison

Observed 2026-09-30 UTC. The [sanitized report](m0-rtmp-wire-comparison.json)
compares the first RTMP media messages from a loopback OBS multitrack publisher
and the RTSP-to-RTMP copy publisher. The tap forwards bytes to MediaMTX and
retains message types, timestamps, lengths, and at most eight leading bytes per
synthetic media message; it does not retain full media messages, stream keys,
or RTMP commands.
Both controls used the synthetic four-video/two-audio ladder, and both local
six-stream probes passed. This is a local comparison, not a capture of the
accepted direct OBS-to-Twitch connection.

| Observation | OBS local publisher | Original copy publisher | Revised copy publisher |
|---|---|---|---|
| First media message | AAC sequence header | Video sequence header | Video sequence header |
| First coded video | Keyframe at 0 ms | Non-key frame at 0 ms | Non-key frame at 0 ms, followed by a keyframe at 0 ms |
| First IDRs, four tracks | 0 ms | 2000 ms | 0 ms |
| AAC setup | Primary sequence header of 7 bytes; secondary of 12 bytes | Primary of 4 bytes; secondary of 9 bytes plus a multichannel configuration packet | Same as original copy |

The original copy path buffered BPM-bearing packets for two seconds before
its first IDRs. The revision drops unrelated pre-IDR packets and rebases the
IDRs to 0 ms, while retaining BPM-bearing packets. Its local sink passed, but
the [bounded Twitch attempt](m0-twitch-live-attempts.md) still ended in a broken
pipe after four seconds and Helix never reported live. The wire evidence shows
that the revised stream still starts coded video with a non-key packet; the
audio setup also differs. It does not prove which difference Twitch rejected.

The [following SEI merge control](m0-twitch-sei-merge.json) made the initial
coded video an IDR with BPM metadata and passed the full local decode and
identity checks. Its bounded Twitch attempt still failed, so the remaining
wire and audio setup differences require investigation. A later
[legacy-primary probe](m0-twitch-legacy-primary.json) also failed after
matching OBS's primary H.264 header form. That temporary switch was reverted.
