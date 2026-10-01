# Approved build plan

Approved 2026-09-30; revised by [ADR 0003](adr/0003-local-appliance-scope.md).
ADR 0001 records the original answers. ADR 0003 supersedes its cloud and
remote-worker scope. The v1 deployment target is a complete local appliance
on a streamer's secondary system.

## Git and delivery

Initialize main; commit spec, plan, decisions, ledger, license, docs, gitignore and
scaffolding after secret review. Create public camarokris/TDRestreamer.
Use branches/PRs, required CI and protected main. Track code, lockfiles, schemas,
fixtures, tests and documentation; exclude runtime data and secrets.

## Milestones

| ID | Work | Exit gate |
|---|---|---|
| M0 | OBS/track/transport/Twitch H/V/preview spikes and named-platform/API eligibility | End-to-end appliance delivery evidence or explicit blockers before dependent integration; no provider qualification |
| M1 | Compose/PostgreSQL, tenant/RBAC/bootstrap/local/OAuth auth, encrypted secrets, audit, OpenAPI, Prometheus, CI | Clean install/restart, isolation, no Redis locally, no leaked secrets |
| M2 | Authenticated RTMP/RTMPS/SRT, standard/dual relay, isolated publishers, durable lifecycle, test/previews | OBS-to-test-to-live, no test destination delivery, output failure isolation |
| M3 | Immutable profiles/rules, compatibility, sharing, canvas/vertical transforms, audio, GPUs, capacity | Pixel/audio correctness, copy checks, real device tests, explicit fallback |
| M4 | YouTube/Twitch/Kick/X/Rumble, supported OAuth/API, setup, accessibility, history, notifications | Real account evidence, UX/role acceptance |
| M5 | Local worker supervision, restart/recovery, hardware capacity, bandwidth accounting and admin limits | No duplicate publishers after local process failure; bounded retry and resource use; measured local capacity |
| M6 | Encrypted backups/restore, restricted updater, discovery/proxies, Streamer.bot | Clean-host restore, update recovery, tested automation |
| M7 | Local hardware/architecture matrix, soak/chaos/security/accessibility, source/images/SBOM | All active v1 requirements and acceptance gates satisfied or owner-approved exceptions |

## Contracts and tests

/api/v1 REST with OpenAPI-generated clients and interactive docs; every meaningful
UI action has an API equivalent. SSE for browser updates; signed retryable outbound
webhooks. Tenant-scoped IDs, permissions, machine-readable errors, pagination,
idempotency, expected revisions and asynchronous operation IDs.

The local worker uses versioned plans and durable desired state. PostgreSQL
and its transactional outbox are authoritative. Restart/reconciliation must
not create duplicate destination publishers. No platform publishers or
transitions occur in test sessions. Remote enrollment, Redis dispatch,
cloud provisioning and provider billing are deferred by ADR 0003.

Go unit/race tests; Vitest/Testing Library UI tests; Playwright browser tests;
real PostgreSQL/FFmpeg/MediaMTX synthetic fixtures; separate credentialed and
hardware qualification. Mock-only tests do not establish platform support.

Complete user/admin/developer/API/operations/OBS/Streamer.bot documentation,
capability records and evidence ledger accompany implementation. Pin dependencies
and images. Releases carry corresponding source, notices, SBOM and build metadata.
Public broadcasts require configured accounts and the owner's authorization.
The owner has authorized further broadcasts needed for M0. Provider tests
and billable cloud resources are outside the current plan.
