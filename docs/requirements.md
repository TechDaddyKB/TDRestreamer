# Requirement and acceptance ledger

Statuses record evidence, not intent. Pending entries remain v1 blockers.

| ID | Requirement | Status | Implementation / tests / evidence |
|---|---|---|---|
| R01 | Multi-tenant design everywhere; local installs generally single-user, cloud may be multi-user | Pending | — |
| R02 | Discord primary login, Google fallback; local authentication for LAN and initial cloud setup | Pending | — |
| R03 | Admin, operator/mod, streamer, viewer/read-only roles | Pending | — |
| R04 | Plain RTMP allowed on private LAN by default; no default public exposure | Pending | — |
| R05 | Standard, dual-input, combined-canvas modes | Pending | — |
| R06 | Layout presets and custom rectangles | Pending | — |
| R07 | Automatic vertical generation: center/positioned crop, blur/fill | Pending | — |
| R08 | YouTube H/V, Twitch H/V, Kick, X, Rumble, generic RTMP/RTMPS in v1 where supported | Pending | — |
| R09 | Platform OAuth/API integration in v1 where supported | Pending | — |
| R10 | Recommended common profile plus advanced per-service profiles/settings | Pending | — |
| R11 | Compatibility engine is core | Pending | — |
| R12 | Recommend transcoding profiles while retaining user choice | Pending | — |
| R13 | Software x264 fallback, strongly discouraged | Pending | — |
| R14 | Automatic GPU assignment, including multiple GPUs | Pending | — |
| R15 | Multiple audio tracks; supported services use them; choose track for single-track services | Pending | — |
| R16 | “none in v1?” for recording: tentative exclusion requiring confirmation | Pending | — |
| R17 | No replay/DVR | Pending | — |
| R18 | Test live OBS feed, stats, browser preview, validation, H/V processing, destination review; send nothing externally | Pending | — |
| R19 | WebRTC preview preferred, HLS fallback | Pending | — |
| R20 | User chooses go-live behavior during setup/testing | Pending | — |
| R21 | Independent destination retry with exponential backoff | Pending | — |
| R22 | Health dashboard and configurable issue notifications | Pending | — |
| R23 | Notification priority: Discord webhook/DM, web, email | Pending | — |
| R24 | Input and output metrics, drops, state, CPU/RAM/GPU/encoder usage, uptime, bandwidth | Pending | — |
| R25 | Historical statistics | Pending | — |
| R26 | Bandwidth accounting, connected provider costs where available, manual pricing fallback; popular providers in v1 | Pending | — |
| R27 | Secrets write/replace, never reveal stored values | Pending | — |
| R28 | PostgreSQL everywhere | Pending | — |
| R29 | Redis only in distributed/cloud-worker mode | Pending | — |
| R30 | Cloud orchestration starts in v1 | Pending | — |
| R31 | Remote workers in v1 | Pending | — |
| R32 | LAN discovery via mDNS and IP/hostname | Pending | — |
| R33 | LAN HTTP sufficient; HTTPS elsewhere | Pending | — |
| R34 | Optional bundled Caddy; external proxy including Nginx Proxy Manager | Pending | — |
| R35 | Standard networking default, configurable host/bridge options | Pending | — |
| R36 | Most configuration in web UI/database | Pending | — |
| R37 | Backup/export and restore | Pending | — |
| R38 | Update notifications; UI update option or CLI instructions | Pending | — |
| R39 | Prometheus metrics from day one | Pending | — |
| R40 | Fully documented REST API and interactive documentation | Pending | — |
| R41 | Streamer.bot integration and instructions | Pending | — |
| R42 | OBS uses custom streaming-server configuration | Pending | — |
| R43 | Admin-configurable limits; default no quotas | Pending | — |
| R44 | AGPLv3 | Pending | — |
| R45 | Performant implementation with understandable code commentary | Pending | — |
| R46 | Non-technical UX, coherent navigation, explanations, tooltips, light/dark/color-blind adaptations | Pending | — |
| R47 | x86-64 Linux CPU/Intel/NVIDIA/AMD; ARM64 Linux CPU where feasible, all in v1 | Pending | — |
| R48 | Minimum N100/8 GB/1 GbE; recommended N100/N305 or Intel 8th-gen+/16 GB; pro Arc A310 or NVIDIA equivalent | Pending | — |
| R49 | Five simultaneous sessions initially; detect hardware and advise reasonable capacity | Pending | — |
| R50 | Reliable restreaming, transforms, monitoring; not a cloud studio | Pending | — |

| Test | Acceptance condition | Requirements | Status / evidence |
|---|---|---|---|
| A01 | Fresh local and cloud installs run documented services; local mode has PostgreSQL and no Redis; distributed mode enables Redis | R28–35 | Pending |
| A02 | Discord/Google identities link safely; local bootstrap cannot be replayed; revoked sessions fail; tenant B cannot access tenant A through API, preview, events, history, or jobs | R01–03 | Pending |
| A03 | Stored credentials never appear in API reads, logs, errors, telemetry, or diagnostic exports; rotation and encrypted restore work | R27, R37 | Pending |
| A04 | Standard/dual compatible feeds preserve encoded video without a video encoder; incompatible audio can be converted independently | R05, R10–12, R15 | Pending |
| A05 | Preset/custom combined-canvas rectangles produce expected pixels and dimensions; invalid geometry is rejected; all vertical generation modes render correctly | R06–07 | Pending |
| A06 | Selected common profiles satisfy all hard rules; conflicting service rules create explained separate renditions; overrides validate; identical jobs share encodes | R10–12 | Pending |
| A07 | Each named destination has actual delivery evidence, credential/API behavior, and declared H/V capability; missing account access is a blocker, not a pass | R08–09 | Pending |
| A08 | Distinct test tones/speech identify live and VOD tracks end to end; single-track service gets the selected mix; missing mix never silently substitutes another | R15 | Pending |
| A09 | Test mode sends zero forbidden packets/API actions under Q01's boundary, including restart, retry replay, automatic mode, and Streamer.bot triggers | R18, R20 | Pending |
| A10 | WebRTC preview works on supported browsers; blocked ICE falls back to HLS; unauthorized readers fail; buffers expire | R19 | Pending |
| A11 | Manual mode waits; automatic mode follows saved policy; repeated start/stop requests do not duplicate outputs; Stop cancels retries durably | R20–21 | Pending |
| A12 | Blackhole/disconnect one publisher; unaffected destinations continue without correlated stalls; retry rate is bounded; encoder failures identify all affected outputs | R21–22 | Pending |
| A13 | All required metrics appear with units/source; unavailable GPU metrics are explicit; counters survive aggregation/reset correctly; notification preferences and recovery dedup work | R22–25, R39 | Pending |
| A14 | Cost fixtures cover tiered egress, allowances, worker startup/idle time, shared resources, GB/GiB, missing provider data, delayed reports, and no duplicate hop accounting | R26 | Pending |
| A15 | Every backend performs a real supported encode on documented hardware; GPU selection respects reservations; software fallback is explicit; insufficient resources fail clearly | R13–14, R43, R47 | Pending |
| A16 | Five concurrent logical sessions pass the ratified workload; no arbitrary five-session product quota; capacity advice matches observed limits | R43, R49 | Pending |
| A17 | Kill worker/controller, partition Redis/control links, and lose provider responses: no competing fenced publishers, duplicate VMs, unbounded retries, or unreconciled owned resources | R29–31 | Pending |
| A18 | LAN/public binding and IPv6 checks prevent accidental public plain RTMP; Caddy and Nginx Proxy Manager recipes work; mDNS and direct addressing documented/tested | R04, R32–35 | Pending |
| A19 | Backup restores on clean host with publishers disabled; interrupted update has a verified recovery procedure and records accurate status | R37–38 | Pending |
| A20 | OpenAPI matches runtime; automation scopes enforced; Streamer.bot examples prepare/test/go-live/stop/query/react without public local-control exposure | R40–42 | Pending |
| A21 | Keyboard/screen-reader workflow, themes, color-independent status, accessible crop inputs, responsive health view pass review | R46 | Pending |
| A22 | Release includes corresponding source/build instructions, dependency notices, SBOM, license decision, and reproducible image metadata | R44–45 | Pending |
