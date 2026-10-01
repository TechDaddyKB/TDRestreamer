# ADR 0003: Local appliance is the v1 deployment target

Status: accepted by project owner, 2026-09-30. Supersedes the cloud and remote-worker scope in ADR 0001 and the original specification.

The intended user runs Tech Daddy's Restreamer on a local secondary system. AWS and RunPod testing, provisioning, billing integrations, and cloud deployment qualification are removed from M0 and the v1 plan. Remote-worker enrollment, distributed scheduling, Redis, and stable cloud ingress are deferred with that scope. A separate machine running a complete local appliance is the supported path; it does not need to enroll as a remote worker.

The v1 appliance still needs its local PostgreSQL, media gateway, worker process, UI, hardware capability checks, platform integrations, LAN setup, backup/restore, and reliability qualification. Keep local bandwidth accounting and capacity advice. Provider cost estimates and connected billing are deferred. Existing provider inventory and account preflight are historical research, not active release gates or authorization for resource use.

This change removes the M0 provider shortlist and network/device lifecycle gate. It does not waive Twitch appliance delivery, named-platform eligibility, track semantics, or local hardware tests. M0 remains open until its remaining gates pass or the owner approves a further scope change.

No AWS/RunPod resources will be provisioned or funded for this plan. Reintroducing cloud or remote-worker support requires a new owner decision, revised requirements and acceptance gates, and a separate execution authorization.
