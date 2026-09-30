# Development

## Prerequisites

Go 1.27.1, Node 26.7.0, npm, Python 3, Docker Engine with Compose, and Git.
The generated SQL uses sqlc 1.31.1. Go modules and npm dependencies are locked.
The media spike separately requires FFmpeg 9.0.1 and MediaMTX 1.21.1.

No workstation system settings need to be changed. A Go installation placed in
`.tools/go` can be used with `PATH="$PWD/.tools/go/bin:$PATH"`.

## Commands

```sh
make setup
make check
make generate
python3 scripts/configure.py
docker compose --env-file .env -f deploy/compose/test.yaml up -d --wait
bash scripts/integration.sh
docker compose --env-file .env -f deploy/compose/test.yaml down -v
```

`make check` runs vet/type checking, Go race-enabled unit tests, UI tests, docs
checks, and builds. `make generate` regenerates tracked sqlc code and TypeScript
API types. Review changes and run `git diff --exit-code` in CI.

Integration tests reset only a deliberately configured database whose name ends
in `_test`. Never point test URLs at a real appliance. The dedicated Compose
project exposes PostgreSQL only on loopback port 55432; its data is temporary.

`make browser` runs Playwright against TDR_E2E_URL (default localhost:8080).
Install its browser with `cd web && npx playwright install chromium` first.
`make media` runs real FFmpeg crop/fill/blur pixel tests and the loopback-only spike; set MEDIAMTX_BIN if not using
`.tools/mediamtx/mediamtx`. Generated logs/results stay in ignored runtime/.

## Architecture

`cmd/control` serves the React build and REST API. `cmd/admin migrate` applies
embedded ordered SQL migrations under an advisory lock. The application database
role is separate from the migration owner and cannot bypass row-level security.
Tenant operations use `SET LOCAL` inside transactions, preventing pool leakage.
Session actions update desired state, audit and outbox in one transaction with
idempotency-key locking and expected-revision checks.

`cmd/worker probe` is diagnostic-only: FFmpeg version and machine architecture.
It does not register, claim jobs, encode, or publish. The media spike is an isolated
feasibility harness, not the application's execution engine.

Pure packages cover permissions, envelopes, lifecycle, geometry/planning, lease
validity, reservations and egress estimates. They are not substitutes for worker
integration, capacity measurement, provider APIs or media qualification.

## Adding functionality

Keep UI/API/runtime behavior aligned. Extend OpenAPI, regenerate types, add
boundary tests and documentation, and update the ledger. Validate a real pipeline
before enabling capability flags. No platform support claim based on a mock.
