# Implementation evidence — 2026-09-30

## Release status

**Development foundation; the requested full v1 is not complete.** No M0–M7
milestone is certified complete. M0 has local OBS/transport/browser-preview evidence and unresolved
Twitch, additional protocol and capability gates; M1 has an implemented local control foundation but still
needs OAuth, invitations and additional identity/operational hardening.

## Implemented and exercised

- Go control/admin/diagnostic-worker commands; React UI served by Go.
- PostgreSQL migration/replay, restricted application role, tenant RLS and sqlc queries.
- One-time local bootstrap, Argon2id login, hashed sessions, logout and role checks.
- Scoped encrypted destination storage, one-time input tokens and token rotation API.
- Desired session state with optimistic revisions, idempotency, transactional audit/outbox.
- Generic compatibility proposals, geometry validation, explicit conversion approval,
  audio-selection/sharing safety; pure reservation/lease and egress-price modules.
- Authenticated bounded SSE replay, protected basic Prometheus metric, OpenAPI and
  generated TypeScript schema types with interactive read-only API exploration.
- Loopback Compose installation with health checks and digest-pinned base images.
- Responsive dark/light/high-contrast UI; no production publishing controls enabled.

## Validation

`make check`: Go vet, TS checking/formatting, Go race-enabled unit tests, UI tests,
documentation links/72 ledger rows and native/frontend builds.

`bash scripts/integration.sh`: real PostgreSQL migration/replay, owner-role rejection,
bootstrap replay prevention, login/logout, CSRF header, viewer denial, encrypted
storage, token non-disclosure, session revisions/idempotency and 30 concurrent
pool-reuse tenant-isolation transactions.

Playwright: local auth/setup visibility; login/session/test/stop/input-token dismissal,
compatibility approval, light theme, API reference and logout. Dashboard and planner
screenshots visually inspected. Screenshots remain ignored synthetic test artifacts.

MediaMTX 1.21.1 / host FFmpeg 9.0.1: see media-spike.json. Synthetic two-AAC-track
RTSP and enhanced-RTMP preservation, selected-track relay with decoded 880 Hz
tone identity verification, isolated publisher
connection refusal and HLS playlist generation passed. This does not establish
OBS, live/VOD semantics, WebRTC, platform compatibility or full fault qualification
on its own. The later [OBS and preview harness](m0-local.md) and
[machine-readable results](m0-obs-preview.json) establish real OBS dual-audio ingest,
internal RTSP and enhanced-RTMP relay audio identity, authenticated Chromium WebRTC
playback, forced HLS fallback, and fresh-client access denials. Application preview
integration and Twitch live/VOD semantics remain unverified.

Real FFmpeg frame tests also passed for crop, fill and blur output geometry,
black fill padding, foreground preservation and positioned red/blue crop selection.
These validate the software filter builder, not GPU or application execution.

Docker image built; isolated Compose fresh start and control restart both returned
ready. Control bound to loopback only; database not host-published in appliance mode.
No Redis and no media listener in the appliance foundation.

npm audit: no known vulnerabilities at the recorded run. govulncheck 1.8.0: no
affected imported packages/reachable symbols. Module-only GO-2026-5932 concerns
unimported x/crypto/openpgp, not the Argon2 package used here. Old scanner 1.1.4
crashed on Go 1.27; replaced with 1.8.0. Gitleaks history scan passed.

## Remaining implementation (not merely external certification)

OAuth/identity linking/invitations/recovery; full profile persistence/platform rules;
application media gateway auth, ingest/probing/worker supervision/publishing/retry,
authenticated WebRTC/HLS playback, canvas editor and GPU execution; platform adapters;
health/history/notifications; distributed protocol/Redis/provisioning/cost connectors;
backup/restore/updater; discovery/proxy deployment; scoped automation tokens and
importable Streamer.bot workflows; complete release images/SBOM/notices.

## External qualification blockers

Owner instruction: **local tests only for now**. No public broadcasting, provider
spending or external account tests were performed. Actual Twitch behavior,
YouTube/Kick/X/Rumble account approvals, AWS/RunPod lifecycle and billing access,
N100/Intel/AMD/ARM64/multi-GPU reference hardware, eight-hour soaks and comprehensive
accessibility review remain unverified. They do not remove any v1 requirement.
