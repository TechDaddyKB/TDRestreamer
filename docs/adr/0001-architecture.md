# ADR 0001: architecture and ratified product decisions

Status: accepted by project owner, 2026-09-30.

Go control/worker/admin binaries; React/TypeScript/Vite UI; PostgreSQL, pgx, sqlc;
SQL migrations; FFmpeg and initially MediaMTX; Compose; Redis only for distributed
mode. MediaMTX remains subject to multi-track protocol qualification. AGPL-3.0-or-later.
Public GitHub repository: camarokris/TDRestreamer. Brand: Tech Daddy's Restreamer.

Q01: Test prohibits destination media and platform broadcast transitions. Configured
remote workers/previews, account checks and notifications are permitted.
Q02: AWS EC2 provisioning/Cost Explorer, RunPod Pods provisioning/available usage;
manual pricing for all providers. Billing capabilities are independently verified.
Q03: RTMP, RTMPS and encrypted SRT ingest required.
Q04: Cloud local login recovery-only after bootstrap.
Q05: No recording, replay or DVR.
Q06: One-time generated-token display and encrypted administrative exports allowed.
Q07: Invitations, initial owner, explicit operator edit grants; viewers read only.
Q08: Stable ingress edge for distributed workers.
Q09: Five 1080p30 H.264/AAC relay sessions, three controlled sinks each, eight-hour
N100 soak; separate eight-hour device transform workload and measured capacity.
Q10: Profile-approved transcoding; software fallback explicit and off by default.
Q11: Optional restricted Compose host updater; external/CLI workflows elsewhere.
Q12: Seven-day detailed metrics, 90-day rollups/events, 365-day audit, 60-second
preview buffers. Daily encrypted backups, seven-day retention, 24-hour RPO and
one-hour lab restore target. Configurable retention.
Q13: Manual Go Live; independent input readiness; 30-second reconnect grace;
30-second worker lease renewed every five seconds; stop before ownership expires.
Q14: Stack and AGPL variant as above.
Q15: Docker bridge default; optional host networking. Ubuntu 24.04 LTS and Debian
13 certification targets, not yet certified.
Q16: Preserve/select supplied tracks; no mixing or cross-input reuse.
Q17: Warning-only budgets; estimates retain currency and pricing provenance;
no automatic termination of live resources.
Q18: External account access, approvals and spending policy remain acceptance
prerequisites. They do not authorize broadcasts/spending automatically.

Plan-approved performance targets: A/V ±100ms; operational API p95 <500ms;
health refresh <=2s; supported local WebRTC p95 <1s; bounded memory/disk/queues.
