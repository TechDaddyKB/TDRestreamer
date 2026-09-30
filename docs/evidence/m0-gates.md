# M0 gate audit

Scope: the approved M0 feasibility milestone, not completion of all v1 acceptance
conditions. Overall status: **not complete**. Local evidence and documentation
cannot substitute for the missing Twitch/account evidence. No scope exception
or design change waiving a gate has been approved.

| Gate | Authoritative evidence | Assessment |
|---|---|---|
| OBS multi-track ingest | [Harness and reproduction](m0-local.md), [unaltered run report](m0-obs-preview.json), `tests/m0/obs-control.mjs` | Passed for pinned OBS custom RTMP: H.264 plus two AAC tracks; each decoded tone identified |
| Internal transport | Same report: `obs_audio_identity` and `obs_enhanced_publisher` | Passed for RTSP transport and FFmpeg copy publisher preserving both supplied mixes |
| Publisher track mapping | Same report, [dual-canvas FLV track-ID sample](m0-dual-canvas.md), and [earlier selected-track spike](media-spike.json) | Controlled-sink preservation, selected-track identity and local FLV muxer IDs 0/1 per media kind passed; platform purpose metadata and Twitch acceptance remain unverified |
| Local dual-canvas transport | [Repeatable fixture](m0-dual-canvas.md), [unaltered run report](m0-dual-canvas.json) | Two actual OBS H.264 canvases plus two AAC tracks preserved through RTSP and enhanced-RTMP copy publishing; decoded color/tone identity, order, and local FLV muxer track IDs passed. Synthetic configuration does not prove Twitch negotiation or delivery |
| Twitch H/V delivery | [Platform inventory](platform-inventory.md) | **Blocked pending broadcast approval**: the authenticated dashboard reports Dual Format eligible, but actual Enhanced Broadcasting H/V negotiation/delivery remains unverified. Ordinary two-key publishing is not a substitute |
| WebRTC/HLS preview | Same run: decoded video frames, negotiated audio/video, HLS fallback after injected WHEP failure, fresh-client denials | Passed local feasibility in Chromium. ICE blackhole behavior, browser audio samples, session revocation/expiry, buffer lifetime and p95 latency remain later qualification work |
| Required ingest transport feasibility | Same run: TLS certificate validation, RTMPS and encrypted-SRT transport and denials | Passed with FFmpeg carrying actual OBS-origin media. Native OBS secure-protocol configuration is not established by this test |
| Named-platform/API eligibility inventory | [Dated platform records](platform-inventory.md), [account preflight](m0-account-eligibility.md), [Twitch app-token report](m0-twitch-app-token.json) | Authenticated UI observations recorded for all five platforms. Twitch dedicated app-token/public-read access passed; Twitch user scopes and other platform application API eligibility remain unverified |
| AWS/RunPod network and device requirements | [Provider records](provider-inventory.md), [AWS quota preflight](m0-account-eligibility.md#regional-quota-follow-up), and [non-launching EC2 permission check](m0-account-eligibility.md#non-launching-ec2-permission-check) | Documentation checked; RunPod UDP limitation identified. AWS Free Plan, EC2 reads, regional quotas (Standard 32 vCPUs; G/VT and P GPU quotas 0), and `t3.micro` RunInstances permission-only DryRun verified. RunPod console accessible. Lifecycle, network/device execution and billing attribution remain unverified; no resources launched |
| Test-mode boundary | [ADR 0001](../adr/0001-architecture.md), Q01 | Ratified: no destination media or platform transitions. Local fixture sinks are qualification infrastructure, not application test-mode permission to broadcast |
| Provider shortlist | ADR 0001, Q02 | Ratified AWS EC2 + RunPod Pods; cost and provisioning capabilities independently assessed |
| Stack ADR | ADR 0001 and [protocol findings](../adr/0002-m0-protocol-findings.md) | Existing stack retained provisionally. Local tests did not demonstrate a mandatory MediaMTX failure warranting SRS replacement |
| Git/tests/docs/evidence delivery | PR #2, required CI plus Sourcery-ai/gitar-bot/SonarQube Cloud | PR #2 merged with local evidence; PR #3 merged with toolkit setup. CI and requested reviewers passed on their final revisions; later evidence changes require their own review |

## What remains before M0 can close

Authenticated account UI checks and Twitch public app-token access are established
in the [account preflight](m0-account-eligibility.md). Establish remaining application
API eligibility and obtain separate broadcast approval before demonstrating actual
Twitch dual-format negotiation, H/V viewer delivery and correct live/VOD semantics.
Account-specific failures require concrete blockers/design proposals, not invented
success. The current instruction is eligibility checks first, with broadcasts
approved separately. Cloud provisioning and spending remain unauthorized.
The [Twitch qualification procedure](m0-twitch-qualification.md) records the
pinned negotiation contract, Linux support uncertainty and remaining execution
steps; it is preparation, not passing delivery evidence.

Additional OBS modes, production gateway integration, GPU qualification, full
platform rule fixtures, distributed recovery, cost reconciliation and soaks remain
within their original M2–M7 milestones. Local M0 feasibility does not mark their
R/A ledger entries complete or narrow v1.
