# Streamer.bot integration

The implemented REST foundation can be called from a local automation client.
OpenAPI is served at `/api/v1/openapi.json`. Mutations require `X-TDR-Request: 1`.
Session actions additionally require a unique `Idempotency-Key` (8–128 bytes) and
JSON containing the current `revision`. Retry an identical request with the same
key. A changed request needs a new key. Stop cancels desired activity durably.

Current browser cookie sessions are not the final automation-token design. Scoped
API tokens, importable Streamer.bot actions, an outbound event bridge and verified
Streamer.bot version compatibility are still pending. Do not expose Streamer.bot
publicly or claim this guide is a completed end-to-end integration.

Future examples must prepare/test/go-live/stop, enable/disable destinations, read
health and react to incident/recovery events. They must preserve test-mode barriers.
Go Live currently returns `qualification_required` and cannot publish.
