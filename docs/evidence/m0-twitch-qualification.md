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

Canvas enumeration alone proves local creation, not encoded frames or delivery.
The later [repeatable dual-canvas fixture](m0-dual-canvas.md) now establishes actual
local encoding, transport and copy-publisher video/audio identity using synthetic
configuration. Twitch negotiation, GPU capacity and platform delivery remain open.

## Separate API eligibility step

On 2026-09-30, after explicit owner approval, a dedicated app was registered
under TechDaddy as `Tech Daddy's Restreamer M0`, category Broadcaster Suite,
confidential client, redirect `http://localhost:18971/oauth/twitch/callback`.
The application appeared in Developer Applications after submission; its manage
page showed the approved settings. A new client secret was generated once and
the client ID and secret were stored in the local Secret Service keyring under
`service=tdrestreamer`, `account=twitch-m0`. The secret-bearing browser tab was
closed. Neither credential was copied into this repository or chat.

The [reproducible read-only preflight](../../tests/m0/twitch-app-token.mjs) used
the app credentials to obtain a client-credentials bearer token, then queried
Helix `GET /users?login=TechDaddy`. The [unaltered sanitized report](m0-twitch-app-token.json)
records HTTP 200 for both calls and one matching user. This establishes basic
app-token/API eligibility for public reads. It does not establish user consent,
scope grants, refresh/revocation, ingest rights, or H/V negotiation. No callback
service was started and no OAuth authorization-code flow was attempted.

Use a dedicated client, as required by [Twitch's registration guide](https://dev.twitch.tv/docs/authentication/register-app/).
The public channel/API read used an app access token with no user scopes.
Any later user consent must identify the exact endpoint and minimal scope using
[Twitch's scope reference](https://dev.twitch.tv/docs/authentication/scopes/).
Stream-key access is a sensitive credential grant; do not request it merely to
prove public channel reads. Client creation does not prove refresh, revocation,
ingest rights or H/V negotiation. Keep credentials out of evidence and Git.

## Offline negotiated-config guard

The [M0 config guard](../../scripts/m0_twitch_config.py) checks an OBS 32.2.2
GoLive response before it can be used in the isolated copy-publisher path. It
requires the pinned schema, both canvas orientations, one AAC live and one AAC
VOD track with output-order track IDs, and an RTMP(S) endpoint. Its summary
contains no authentication or endpoint URL. It also constructs an OBS override
with only a loopback ingest endpoint, removing the remote authentication from
that override. Unit controls reject missing or swapped roles. These are
synthetic contract checks. A later [account-specific response](m0-twitch-live-attempts.md)
passed the guard, but the guard is not a working Twitch publisher. If a later
response differs, record the difference and qualify it before sending media.

## Remaining execution sequence

1. The [local fixture](m0-dual-canvas.md) passes labeled H/V frames and distinct
   supplied audio through each transport boundary with external networking
   disabled. A later [four-rendition run](m0-twitch-ladder-local.md) uses
   sanitized account-negotiated encoder settings, checks order, dimensions,
   identities and FLV track IDs 0–3. Neither fixture proves Twitch delivery.
2. Implement the qualification publisher's negotiation and track mapping against
   the observed contract, using the offline guard as an initial check. Do not
   claim that ordinary FFmpeg two-key fanout or a
   mocked response meets Twitch's contract. A direct OBS test is only a reference
   control; the chosen appliance transport/publisher path must also pass.
3. Prepare a new broadcast approval request once the corrected executable path is
   ready. Specify TechDaddy as the destination, synthetic content only, maximum
   duration/attempt count, bandwidth cap, viewer visibility and VOD retention.
   The two approved attempts in the [diagnostic record](m0-twitch-live-attempts.md)
   were used; no further broadcast is authorized.
4. With approval, use credentials during execution to obtain the actual negotiated
   H/V ladder and audio track roles. Redact credentials from retained evidence,
   logs and artifacts. Verify labeled horizontal and vertical viewer playback
   within the same Twitch broadcast, then verify intended live/VOD audio identity.
   Desktop-only playback or an Inspector bandwidth test cannot prove all of this.
5. Stop outputs on completion/failure, verify the channel is offline, and retain
   sanitized results with exact tool versions and producing-source hashes. A
   failed or unsupported path remains a blocker; no local fixture waives it.

The original app-token preflight performed no broadcast or stream-key read. The
later bounded attempts are recorded separately. No OAuth grant or change to the
user's OBS configuration occurred. The other platforms' application/API
prerequisites remain in the [account record](m0-account-eligibility.md).
