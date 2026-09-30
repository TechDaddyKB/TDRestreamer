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

## Test coverage and SonarQube Cloud

Run `make coverage` after `make setup` (requires `uv`, or override
`COVERAGE='python3 -m coverage'` with coverage.py 7.10.7 installed). It runs
race-enabled Go unit tests, Vitest V8 coverage, and Python unittest coverage.
Reports stay ignored: `coverage/go.out`, `web/coverage/lcov.info`, and
`coverage/python.xml`. The pinned Vitest coverage provider matches Vitest.

CI uploads these reports for seven days and a separate `sonar` job imports them
using `sonar-project.properties`, then waits for the existing quality gate.
Only generated sqlc code/API types and test files are excluded from production
analysis. Untested production files remain visible at zero coverage; integration,
browser and media qualification runs are not counted in these unit reports.
Coverage does not establish M0 media or platform acceptance.

The project must use CI analysis: automatic analysis does not import coverage.
See [SonarQube coverage setup](https://docs.sonarsource.com/sonarqube-cloud/analyzing-source-code/test-coverage/overview).
The repository secret `SONAR_TOKEN` supplies scanner authentication only to the
scan step. The dedicated token expires 2026-12-29; rotate it in SonarQube account
security settings and replace the GitHub Actions repository secret before expiry.
Never put the token in a command argument, report, commit, or workflow file.
Fork and Dependabot PRs still generate coverage but skip authenticated analysis;
review their changes before moving them to a trusted maintainer branch. Do not
use `pull_request_target` to execute contributor code with this secret.

For missing coverage, check the CI artifact contains all three nonempty reports,
then check scanner logs for successful Go, LCOV, and Python imports. LCOV paths
must resolve under `web/src`; Python uses relative paths. Do not suppress a
coverage failure by excluding application code or lowering the quality gate.

## GitHub Actions runtime

The CI workflow pins the official actions to reviewed release commits:
checkout 7.0.1, setup-go 7.0.0, setup-node 7.0.0, upload-artifact 7.0.1,
and download-artifact 8.0.1. Their action manifests use Node.js 24; this runtime
is independent of the application's Node.js 26.7.0 toolchain. GitHub-hosted
Ubuntu 24.04 runners support it. Downloaded artifacts retain digest verification;
the newer download action fails on a digest mismatch.

When updating actions, verify the official release and `action.yml`, retain the
version comment beside the commit pin, and run the complete workflow to validate
checkout, dependency caches, report transfer, and scanner import. Do not opt back
into an insecure Node.js runtime to suppress deprecation annotations.

## Repository and deployment contents

GitHub retains source, tests, documentation, the original specification,
sanitized acceptance evidence, migrations, deployment definitions, dependency
lockfiles, and generated API/sqlc source. These are needed to review, test,
reproduce, maintain, and qualify the application even when they are not runtime
files. Raw test output and private working files belong in ignored `runtime/`,
`coverage/`, `.tools/`, `.venv/`, `data/`, `backups/`, or `secrets/` directories.
Environment files, private keys, dependencies, builds, browser artifacts, and
tool/editor caches stay local. Sanitized `.env.example` files remain tracked.

`.gitignore` affects untracked files; it does not unpublish an already tracked
file. Before pushing, inspect `git status --short`, `git diff --cached`, and
`git ls-files -ci --exclude-standard`, then run secret scanning. Avoid `git add
-f` for local artifacts. If a harmless local file was tracked accidentally,
`git rm --cached -- path` stops tracking it while retaining the local copy;
credential exposure also requires rotation and history assessment.

`.dockerignore` independently limits the build context. The Dockerfile's final
stage contains the three Go executables, compiled UI, license, and base runtime
dependencies. Development documentation, test results, source dependencies, and
local credentials are not copied into the released image.

## Runtime architecture

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
