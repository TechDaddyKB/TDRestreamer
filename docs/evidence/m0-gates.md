# M0 gate audit

Scope: the approved M0 feasibility milestone, not completion of all v1 acceptance
conditions. Overall status: **not complete**. Local evidence and documentation
cannot substitute for the missing Twitch/account evidence. No scope exception
or design change waiving a gate has been approved.

| Gate | Authoritative evidence | Assessment |
|---|---|---|
| OBS multi-track ingest | [Harness and reproduction](m0-local.md), [unaltered run report](m0-obs-preview.json), `tests/m0/obs-control.mjs` | Passed for pinned OBS custom RTMP: H.264 plus two AAC tracks; each decoded tone identified |
| Internal transport | Same report: `obs_audio_identity` and `obs_enhanced_publisher` | Passed for RTSP transport and FFmpeg copy publisher preserving both supplied mixes |
| Publisher track mapping | Same report plus [earlier selected-track spike](media-spike.json) | Controlled-sink preservation and selected-track identity passed; platform purpose metadata remains unverified |
| Twitch H/V delivery | [Platform inventory](platform-inventory.md) | **Blocked**: no authorized account test or actual Enhanced Broadcasting H/V negotiation/delivery evidence. Ordinary two-key publishing is not a substitute |
| WebRTC/HLS preview | Same run: decoded video frames, negotiated audio/video, HLS fallback after injected WHEP failure, fresh-client denials | Passed local feasibility in Chromium. ICE blackhole behavior, browser audio samples, session revocation/expiry, buffer lifetime and p95 latency remain later qualification work |
| Required ingest transport feasibility | Same run: TLS certificate validation, RTMPS and encrypted-SRT transport and denials | Passed with FFmpeg carrying actual OBS-origin media. Native OBS secure-protocol configuration is not established by this test |
| Named-platform/API eligibility inventory | [Dated platform records](platform-inventory.md) | Documentation recorded; actual account eligibility/API access for YouTube/Twitch/Kick/X/Rumble **blocked** by local-only policy. No authenticated account inventory performed |
| AWS/RunPod network and device requirements | [Provider records](provider-inventory.md) | Documentation checked; RunPod UDP limitation identified. Account lifecycle, network/device execution and billing attribution remain unverified; no resources launched |
| Test-mode boundary | [ADR 0001](../adr/0001-architecture.md), Q01 | Ratified: no destination media or platform transitions. Local fixture sinks are qualification infrastructure, not application test-mode permission to broadcast |
| Provider shortlist | ADR 0001, Q02 | Ratified AWS EC2 + RunPod Pods; cost and provisioning capabilities independently assessed |
| Stack ADR | ADR 0001 and [protocol findings](../adr/0002-m0-protocol-findings.md) | Existing stack retained provisionally. Local tests did not demonstrate a mandatory MediaMTX failure warranting SRS replacement |
| Git/tests/docs/evidence delivery | PR #2, required CI plus Sourcery-ai/gitar-bot/SonarQube Cloud | Review current PR revision before merge. Passing older checks cannot certify later code |

## What remains before M0 can close

Obtain authorized, dedicated account access and a test policy for the external
M0 gates; demonstrate actual Twitch dual-format negotiation, H/V viewer delivery
and correct live/VOD semantics; establish the named platforms' account/API
eligibility. Account-specific failure must produce a concrete blocker/design
proposal, not a fabricated success. The current instruction is local tests only,
so these actions are not authorized and will not be attempted.

Additional OBS modes, production gateway integration, GPU qualification, full
platform rule fixtures, distributed recovery, cost reconciliation and soaks remain
within their original M2–M7 milestones. Local M0 feasibility does not mark their
R/A ledger entries complete or narrow v1.
