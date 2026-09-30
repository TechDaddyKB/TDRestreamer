# Platform capability inventory

Review date: 2026-09-30. The capability table below records official documentation.
Subsequent [authenticated account observations](m0-account-eligibility.md) establish
Twitch Dual Format eligibility and access to the five platform dashboards/setup
pages. The owner now authorizes eligibility checks, with broadcasts approved
separately. No media delivery or application OAuth/API permission tests were
performed. Browser access does not establish application scopes, refresh-token
behavior or actual delivery.
Tested adapter version: none; no production platform adapter exists yet.

| Platform | Transport and credentials | Lifecycle / available API | Orientation and audio | Eligibility and outstanding evidence |
|---|---|---|---|---|
| YouTube | RTMP(S), stream keys; separate Google publishing authorization required | `liveStreams` and `liveBroadcasts`, bind and transition operations | Live Control Room documents a second encoder key for vertical; API reference still describes one stream bound to a broadcast. Do not infer API support for pairing from UI support. Independent supplied audio/VOD semantics unverified | Verified channel and no recent streaming restrictions; check actual channel/app access, publishing scopes, quota, paired-event association and dual-format delivery |
| Twitch | RTMP ingress plus account stream key; Enhanced Broadcasting required for dual format | Video ingestion is separate from account/API authorization; exact Enhanced Broadcasting negotiation and lifecycle remain a spike requirement | H/V is a negotiated dual-format broadcast, not two ordinary keys. Local OBS VOD-track preservation does not prove Twitch live/VOD semantics | Help now states dual format is available to all streamers, while server-side transcode entitlement varies. Actual account/encoder negotiation, viewer orientation and VOD playback remain blocked |
| Kick | User's stream URL/key; OAuth 2.1 authorization-code grants and `streamkey:read` are documented | Channel read and metadata patch; `channel:write` for metadata, `channel:read` for information | No supported simultaneous paired H/V or distinct live/VOD audio contract established from reviewed docs | App registration, consent, refresh/revoke and account ingest rights unverified. Metadata PATCH is not evidence for an explicit broadcast-start API |
| X | Producer sources use RTMP/RTMPS or HLS and stream key | Producer UI creates sources/broadcasts, supports immediate/scheduled broadcasts; public lifecycle API availability unverified | Reviewed Producer guide does not establish a paired H/V or separate VOD-audio mechanism | Media Studio/Live Studio UI access observed; application API eligibility unverified; do not equate ordinary X API credentials with Producer access |
| Rumble | Streamer configuration provides RTMP URL and stream key | UI creates a stream; the published v1.1 Live Stream API supplies live metadata/notifications. It does not establish create/start/stop APIs | Paired H/V and multi-track destination semantics unverified | Account rights and per-stream workflow unverified; API URL itself is a credential and must be encrypted/redacted. RTMPS support must be checked against supplied endpoint |
| Generic RTMP/RTMPS | User endpoint/key, optionally supported endpoint-specific authentication | No platform event lifecycle promised | Select supplied audio or enhanced-RTMP packaging only when the receiver declares and passes that capability | [Local report](m0-obs-preview.json) proves the pinned controlled sink, not arbitrary receivers |

## Sources and rule boundaries

YouTube's [Live API reference](https://developers.google.com/youtube/v3/live/docs)
(last updated 2026-09-15) distinguishes event and media resources. Its
[live-stream setup guide](https://support.google.com/youtube/answer/2474026?hl=en)
documents channel eligibility and encoder-based dual format. The pairing API gap
above is an unresolved inference from those two documents, not a claim that an
undocumented API exists or that separate public broadcasts satisfy the requirement.
No numeric encoding limit snapshot has yet been qualified for the application.

Twitch's [broadcast guide](https://dev.twitch.tv/docs/video-broadcast/),
[Enhanced Broadcasting guide](https://help.twitch.tv/s/article/multiple-encodes)
and [dual-format guide](https://help.twitch.tv/s/article/dual-format-vertical-video)
identify the delivery mechanism and distinction between dual-format availability
and server-side transcoding eligibility. Dynamic encoder configuration and actual
wire metadata are not proven by static profile recommendations. Keep both as
explicit gates before declaring the Twitch adapter supported.

Kick's [OAuth scopes](https://github.com/KickEngineering/KickDevDocs/blob/main/scopes/scopes.md)
and [channel API](https://docs.kick.com/apis/channels) document stream credential
read and metadata operations. Request only capabilities the user selects;
least-privilege scope/refresh tests and current codec/bitrate limits remain pending.

X's [Producer guide](https://help.x.com/en/using-x/how-to-use-live-producer) lists
H.264/AAC-LC, a 128 kb/s audio maximum, 9 Mb/s recommended versus 12 Mb/s maximum
video, and 1920×1080 at 30 fps as its listed maximum resolution/frame-rate option.
These are a dated Producer documentation snapshot, not a universal rule for every
X live product. Account-specific validation and other orientation rules remain
unverified. Starting media and creating a broadcast are separate operations.

Rumble's [setup guide](https://rumble.support/help/how-to-setup-a-livestream)
(updated 2025-12-05) and [Live Stream API guide](https://rumble.support/help/how-to-use-rumble-s-live-stream-api)
(updated 2025-11-20) establish manual RTMP setup and live metadata access. No
numeric codec/bitrate hard-limit snapshot, OAuth grant or broadcast-control API
was established from these sources; record unknown instead of inventing support.

## Evidence needed to close the account gates

For each platform retain a sanitized account eligibility result, app/API version,
minimum scope list, refresh/revocation result, actual input/output codec probes,
viewer delivery checks and account-specific limitations. For H/V, verify event
association and orientation behavior; for live/VOD tracks, verify both viewer
playback and the resulting VOD. Account eligibility checks are authorized. Use explicit test destinations and a
separately approved broadcast policy before media delivery tests. Numeric rules
need dated regression fixtures and actual rejection/acceptance evidence in M3/M4.
