# Approved build plan

Approved 2026-09-30. The original restream-appliance-spec.md remains unchanged.
ADR 0001 records the owner's answers and supersedes the spec's open alternatives.

## Git and delivery

Initialize main; commit spec, plan, decisions, ledger, license, docs, gitignore and
scaffolding after secret review. Create public camarokris/TDRestreamer.
Use branches/PRs, required CI and protected main. Track code, lockfiles, schemas,
fixtures, tests and documentation; exclude runtime data and secrets.

## Milestones

| ID | Work | Exit gate |
|---|---|---|
| M0 | OBS/track/transport/Twitch H/V/preview spikes, platform and provider inventory | End-to-end evidence or explicit blockers before dependent integration |
| M1 | Compose/PostgreSQL, tenant/RBAC/bootstrap/local/OAuth auth, encrypted secrets, audit, OpenAPI, Prometheus, CI | Clean install/restart, isolation, no Redis locally, no leaked secrets |
| M2 | Authenticated RTMP/RTMPS/SRT, standard/dual relay, isolated publishers, durable lifecycle, test/previews | OBS-to-test-to-live, no test destination delivery, output failure isolation |
| M3 | Immutable profiles/rules, compatibility, sharing, canvas/vertical transforms, audio, GPUs, capacity | Pixel/audio correctness, copy checks, real device tests, explicit fallback |
| M4 | YouTube/Twitch/Kick/X/Rumble, supported OAuth/API, setup, accessibility, history, notifications | Real account evidence, UX/role acceptance |
| M5 | Remote enrollment/mTLS/leases/fencing, Redis, stable ingress, AWS/RunPod, costs/limits | Partition reconciliation, no duplicate publishers/orphans, cost fixtures |
| M6 | Encrypted backups/restore, restricted updater, discovery/proxies, Streamer.bot | Clean-host restore, update recovery, tested automation |
| M7 | Hardware/architecture matrix, soak/chaos/security/accessibility, source/images/SBOM | All R01–R50/A01–A22 satisfied or owner-approved exceptions |

## Contracts and tests

/api/v1 REST with OpenAPI-generated clients and interactive docs; every meaningful
UI action has an API equivalent. SSE for browser updates; signed retryable outbound
webhooks. Tenant-scoped IDs, permissions, machine-readable errors, pagination,
idempotency, expected revisions and asynchronous operation IDs.

Worker-initiated mutually authenticated control channel, versioned plans and
fencing epochs. PostgreSQL desired state and transactional outbox are authoritative;
Redis is reconstructible. No platform publishers/transitions in test sessions.

Go unit/race tests; Vitest/Testing Library UI tests; Playwright browser tests;
real PostgreSQL/FFmpeg/MediaMTX synthetic fixtures; separate credentialed and
hardware qualification. Mock-only tests do not establish platform support.

Complete user/admin/developer/API/operations/OBS/Streamer.bot documentation,
capability records and evidence ledger accompany implementation. Pin dependencies
and images. Releases carry corresponding source, notices, SBOM and build metadata.
Public broadcasts and billable tests require configured accounts/spending policy.
