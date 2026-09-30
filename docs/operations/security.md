# Security boundaries and gaps

Implemented: local Argon2id passwords; cryptographically random setup/session/input
tokens; SHA-256 token hashes; strict same-site HTTP-only session cookies; a custom
same-origin mutation header with no CORS; bounded local login throttling; server-side
membership lookup on every authenticated request; tenant RLS for media configuration,
sessions, events, audit and idempotency; tenant-bound AES-256-GCM envelope encryption;
separate privileged migrations; parameterized SQL; structured errors; no command
execution from saved destination URLs.

The single-process login limiter is an initial defense, not distributed abuse
protection. Identity/membership tables are accessed by auth code outside tenant RLS;
they need further hardening before multi-user/public certification. SSE connections
last at most one minute and reauthenticate on reconnect. There is no public OAuth,
invitation UI, credential rotation UI or cloud recovery flow yet.

The root key lives outside PostgreSQL. Envelope AAD binds encrypted data to the
tenant and resource. The envelope package supports multiple decryption key IDs,
but a deployment key-rotation command is not implemented. Never remove an old key
until all values are rewritten and a restore drill has succeeded.

Stored destination URLs are not sent anywhere. Execution must add DNS revalidation,
SSRF filtering, controlled LAN exceptions and secret-safe publisher isolation before
publishing is enabled. Logs must not contain credentials or command lines containing
keys. The public API never reads destination secrets back to users.

Prometheus /metrics requires the separate TDR_METRICS_TOKEN bearer credential.
Only an HTTP request counter exists currently; media/GPU measurements are pending.
No public release security claim is made by these foundations.
