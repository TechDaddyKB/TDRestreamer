# M0 direct OBS control broadcast

Observed 2026-09-30 UTC on the public TechDaddy channel. These were three
synthetic, bounded broadcasts using an isolated OBS profile and Twitch's
account-negotiated four-video/two-audio configuration. The profile and its
credential-bearing override were created in private tmpfs and removed after
each run; the owner's normal OBS profile was untouched. No AWS or RunPod
resource was created.

The [90-second report](m0-twitch-obs-control-first.json) and
[150-second report](m0-twitch-obs-control-second.json) both record OBS 32.2.2
publishing, Helix live observation, a 4,720 kbps nominal negotiated ladder,
and no early OBS exit. The first report's immediate `helix_offline_after_stop`
is false because Twitch had not yet reported the stop; a later Helix read
returned offline. The second run waited for OBS to stop and Helix to become
offline, and records both successfully. After the control harness moved its
WebSocket password handoff from a second tmpfs file to the local controller's
process environment, a [30-second smoke run](m0-twitch-obs-control-smoke.json)
again observed Helix live, clean OBS stop and Helix offline. No test listeners
or private profile directories remained afterward.

During the second run, the Creator Dashboard reported **360p +1 Horizontal**
and **720p +3 Vertical**, about 4,414 kb/s and 30 fps with **Excellent** stream
health. Its horizontal viewer displayed the red **HORIZONTAL** scene. The
player's **Switch to Vertical View** control then displayed the distinct blue
**VERTICAL** scene at 720p30. The public channel player independently displayed
the red horizontal scene during the first run. These observations establish
Twitch H/V viewer delivery for direct OBS publishing.

Twitch published the first run as a public [1:30 VOD](https://www.twitch.tv/videos/2888443240).
The downloaded VOD decoded as 640×360 H.264 plus AAC and 152.08 seconds of
container duration. A two-second audio sample at 10 seconds had normalized
440 Hz power below the displayed eight-decimal precision and 880 Hz power
`0.00780275`, establishing the intended VOD audio mix in that sample. The
duration discrepancy is a container observation; the channel page labels the
broadcast 1:30.

Live audio identity is **not established**. Anonymous live HLS downloads
returned a 256×144 silent pre-roll ad, even when the 360p source rendition was
requested; those samples cannot test the stream's 440 Hz audio. The local
six-stream fixture separately decodes 440 Hz live and 880 Hz VOD tracks before
Twitch delivery.

The direct OBS control establishes that this TechDaddy channel and the
negotiated ladder can deliver H/V video. It does **not** qualify the appliance
copy-publisher: its five preceding RTMPS attempts never reached Helix live.
The publisher's wire-format or timing difference from OBS remains the next
diagnostic target. The M0 Twitch gate and milestone remain open.
