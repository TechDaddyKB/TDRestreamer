# Twitch qualification prerequisites and procedure

Reviewed 2026-09-30. **Not a passing test result.** This narrows the remaining
[M0 gate](m0-gates.md) into work that can be verified without treating account
login, a client ID, or a direct OBS broadcast as appliance delivery evidence.

## Encoder and protocol findings

The installed Arch package reports OBS Studio 32.2.2-1 (`obs --version` reports
32.2.2). Twitch's [dual-format instructions](https://help.twitch.tv/s/article/dual-format-vertical-video)
list Windows/macOS, OBS 32 or newer, Enhanced Broadcasting and an additional
vertical canvas. Linux is not listed in that requirements table. This is a
documented-support gap, not proof that the Linux encoder fails.

OBS source at commit `ba2f32bdf791005443988a4955e963663e16b1ed` (32.2.2) establishes:

- [Settings](https://github.com/obsproject/obs-studio/blob/ba2f32bdf791005443988a4955e963663e16b1ed/frontend/settings/OBSBasicSettings.cpp)
  expose multitrack video for an RTMP service with a configuration URL, or a
  custom service with an explicit configuration. The inspected function has no
  Linux-specific exclusion; this does not establish installed runtime support.
- [Negotiation input](https://github.com/obsproject/obs-studio/blob/ba2f32bdf791005443988a4955e963663e16b1ed/frontend/utility/GoLiveAPI_PostData.cpp)
  includes the stream key, system capabilities, codecs, canvas dimensions/frame
  rates and VOD-audio preference. Schema version is `2025-01-25`. It is distinct
  from Helix OAuth; registering an application does not negotiate an encoder.
- [Response types](https://github.com/obsproject/obs-studio/blob/ba2f32bdf791005443988a4955e963663e16b1ed/frontend/utility/models/multitrack-video.hpp)
  include ingest endpoints, video encoder configurations with `canvas_index`,
  and separate live/VOD audio configurations with track IDs.
- [Output setup](https://github.com/obsproject/obs-studio/blob/ba2f32bdf791005443988a4955e963663e16b1ed/frontend/utility/MultitrackVideoOutput.cpp)
  applies those configurations to actual canvases and audio mixers. Custom-service
  configuration can exercise a local fixture, but cannot establish Twitch's
  account response or viewer behavior.

[Aitum Vertical 1.6.4](https://github.com/Aitum/obs-vertical-canvas/releases/tag/1.6.4)
publishes a Linux package. A subsequent package inventory found that
`obs-vertical-canvas 1.6.4-1` was already installed on this host. The existing
qualification harness explicitly disables multitrack video and proves one video
plus two audio tracks; it is not a dual-canvas or negotiation result.

### Local canvas preflight

A separate temporary OBS profile was launched under Xvfb `:198`, software GL and
a new user/network namespace. The probe checked that only loopback existed and
both IPv4/IPv6 route tables were empty, then enabled loopback. No output was
started. OBS WebSocket 5.7.4 `GetCanvasList` returned status 100 / result true:

| Canvas | Base and output size | Frame rate |
|---|---|---|
| Main | 640 × 360 | 30/1 |
| Aitum Vertical | 1080 × 1920 | 30/1 |

This is a manually summarized exploratory observation, not a reproducible
qualification report. The first attempt timed out: a downloaded plugin duplicated
the installed one, and the temporary WebSocket configuration omitted
`first_load=false`. The successful retry used the installed plugin only and
corrected that configuration. Temporary OBS/Xvfb processes were terminated;
the user's OBS profile and system plugin installation were not changed.

Canvas enumeration proves local creation, not encoded frames, track mapping,
negotiation, GPU capacity, or delivery. A checked-in, repeatable dual-canvas media
fixture is still required for execution step 1 below.

## Separate API eligibility step

Prepared, but not submitted: a Twitch registration under TechDaddy named
`Tech Daddy's Restreamer M0`, category Broadcaster Suite, confidential client,
redirect `http://localhost:18971/oauth/twitch/callback`. The form accepts this
localhost redirect. No callback service or client credential has been created.
The browser registration is awaiting action-time confirmation because it creates
a persistent application identity. Registration is separate from channel consent.

Use a dedicated client, as required by [Twitch's registration guide](https://dev.twitch.tv/docs/authentication/register-app/).
Initial public channel/API reads can use an app access token with no user scopes.
Any later user consent must identify the exact endpoint and minimal scope using
[Twitch's scope reference](https://dev.twitch.tv/docs/authentication/scopes/).
Stream-key access is a sensitive credential grant; do not request it merely to
prove public channel reads. Client creation does not prove refresh, revocation,
ingest rights or H/V negotiation. Keep credentials out of evidence and Git.

## Remaining execution sequence

1. Exercise the actual additional-canvas encoder locally with labeled H/V frames
   and distinguishable supplied live/VOD audio. Keep external networking disabled.
   Probe each transport boundary, including track order, dimensions and identity.
2. Implement the qualification publisher's negotiation and track mapping against
   the observed contract. Do not claim that ordinary FFmpeg two-key fanout or a
   mocked response meets Twitch's contract. A direct OBS test is only a reference
   control; the chosen appliance transport/publisher path must also pass.
3. Prepare a separate broadcast approval request once the executable path is
   ready. Specify TechDaddy as the destination, synthetic content only, maximum
   duration/attempt count, bandwidth cap, viewer visibility and VOD retention.
   Current authorization does not cover starting that broadcast or negotiation
   that could transition platform state.
4. With approval, use credentials during execution to obtain the actual negotiated
   H/V ladder and audio track roles. Redact credentials from retained evidence,
   logs and artifacts. Verify labeled horizontal and vertical viewer playback
   within the same Twitch broadcast, then verify intended live/VOD audio identity.
   Desktop-only playback or an Inspector bandwidth test cannot prove all of this.
5. Stop outputs on completion/failure, verify the channel is offline, and retain
   sanitized results with exact tool versions and producing-source hashes. A
   failed or unsupported path remains a blocker; no local fixture waives it.

No broadcasts, stream-key reads, app registrations, OAuth grants or changes to the
user's OBS configuration occurred during this preparation. The other platforms'
application/API prerequisites remain in the [account record](m0-account-eligibility.md).
