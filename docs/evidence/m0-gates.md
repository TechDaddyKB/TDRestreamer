# M0 gate audit

Scope: the approved M0 feasibility milestone, not completion of all v1 acceptance
conditions. Overall status: **not complete**. Local evidence and documentation
cannot substitute for the missing Twitch/account evidence. [ADR 0003](../adr/0003-local-appliance-scope.md)
removes provider qualification from M0; it does not waive the remaining media
or named-platform gates.

| Gate | Authoritative evidence | Assessment |
|---|---|---|
| OBS multi-track ingest | [Harness and reproduction](m0-local.md), [unaltered run report](m0-obs-preview.json), `tests/m0/obs-control.mjs` | Passed for pinned OBS custom RTMP: H.264 plus two AAC tracks; each decoded tone identified |
| Internal transport | Same report: `obs_audio_identity` and `obs_enhanced_publisher` | Passed for RTSP transport and FFmpeg copy publisher preserving both supplied mixes |
| Publisher track mapping | Same report, [dual-canvas FLV track-ID sample](m0-dual-canvas.md), and [earlier selected-track spike](media-spike.json) | Controlled-sink preservation, selected-track identity and local FLV muxer IDs 0/1 per media kind passed; platform purpose metadata and Twitch acceptance remain unverified |
| Local dual-canvas transport | [Repeatable fixture](m0-dual-canvas.md), [unaltered run report](m0-dual-canvas.json), [negotiated-ladder local run](m0-twitch-ladder-local.md), [bounded publisher and bridge control](m0-twitch-copy-candidate.md) | Two actual OBS canvases, four account-negotiated H.264 renditions and two AAC tracks preserved through RTSP and enhanced-RTMP copy publishing; decoded color/tone identity, order, and local FLV muxer track IDs 0–3 passed. The bounded libavformat publisher also passed the local six-stream bridge path. Sanitized local configuration does not prove Twitch ingest acceptance or delivery |
| Twitch H/V delivery | [Platform inventory](platform-inventory.md), [bounded attempt record](m0-twitch-live-attempts.md), [direct OBS control](m0-twitch-obs-control.md), [public live-audio sample](m0-twitch-live-audio.json), [control comparison](m0-rtmp-control-comparison.json) | **Partially passed**: direct isolated OBS delivered distinct red horizontal and blue vertical viewer scenes, an 880 Hz VOD sample, and 440 Hz live audio in public horizontal playback on the account-negotiated ladder. Nine appliance copy-publisher attempts still failed at ingest. The owner authorized further necessary broadcast tests |
| WebRTC/HLS preview | Same run: decoded video frames, negotiated audio/video, HLS fallback after injected WHEP failure, fresh-client denials | Passed local feasibility in Chromium. ICE blackhole behavior, browser audio samples, session revocation/expiry, buffer lifetime and p95 latency remain later qualification work |
| Required ingest transport feasibility | Same run: TLS certificate validation, RTMPS and encrypted-SRT transport and denials | Passed with FFmpeg carrying actual OBS-origin media. Native OBS secure-protocol configuration is not established by this test |
| Named-platform/API eligibility inventory | [Dated platform records](platform-inventory.md), [account preflight](m0-account-eligibility.md), [Twitch app-token report](m0-twitch-app-token.json) | Authenticated UI observations recorded for all five platforms. Twitch dedicated app-token/public-read access passed; Twitch user scopes and other platform application API eligibility remain unverified |
| Test-mode boundary | [ADR 0001](../adr/0001-architecture.md), Q01 | Ratified: no destination media or platform transitions. Local fixture sinks are qualification infrastructure, not application test-mode permission to broadcast |
| Stack ADR | ADR 0001 and [protocol findings](../adr/0002-m0-protocol-findings.md) | Existing stack retained provisionally. Local tests did not demonstrate a mandatory MediaMTX failure warranting SRS replacement |
| Git/tests/docs/evidence delivery | PRs #2–#23 and required CI plus Sourcery-ai/gitar-bot/SonarQube Cloud | PRs #2–#23 merged. Required CI and applicable code review gates passed; Sourcery skipped some reviews because its weekly budget was exhausted |

## What remains before M0 can close

Authenticated account UI checks and Twitch public app-token access are established
in the [account preflight](m0-account-eligibility.md). The
[Twitch attempts](m0-twitch-live-attempts.md) established account-specific
negotiation, and a [direct OBS control](m0-twitch-obs-control.md) established
H/V viewer delivery, one VOD audio sample, and a public horizontal 440 Hz live
sample. All nine appliance copy-publisher attempts failed at external ingest.
Establish remaining application API eligibility; the revised
publisher passes local stream and identity controls but failed at Twitch ingest.
Compare its wire output with the accepted OBS path before repeating it.
Account-specific failures remain concrete blockers, not invented success.
Provider qualification is no longer an M0 gate.
The [Twitch qualification procedure](m0-twitch-qualification.md) records the
pinned negotiation contract, Linux support uncertainty and remaining execution
steps; it is preparation, not passing delivery evidence.

Additional OBS modes, production gateway integration, GPU qualification, full
platform rule fixtures, distributed recovery, cost reconciliation and soaks remain
within their original M2–M7 milestones. Local M0 feasibility does not mark their
R/A ledger entries complete or narrow v1.
