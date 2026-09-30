# Project utilities

These scripts are maintained project tooling for contributors and CI, not
one-off Codex session helpers. Keep them in source control so tests and evidence
can be reproduced without the original developer's workstation.

| Script | Purpose | Entry point |
| --- | --- | --- |
| `configure.py` | Generate local deployment configuration without overwriting existing files or printing secrets | Installation guide and CI |
| `integration.sh` | Configure the dedicated test database connection and run Go integration tests | CI |
| `browser-integration.sh` | Start the application for Playwright integration tests and clean it up | CI |
| `check-docs.py` | Validate documentation links, license, and requirements ledger | `make docs` |
| `scan-secrets.py` | Check tracked files for common accidental credentials; complements the dedicated scanners | CI |
| `media-spike.py` | Reproduce local transport and audio-mapping checks | `make media` |
| `m0-local.py` | Run isolated real OBS, secure transport, and browser-preview qualification | `make m0` |
| `m0_protocols.py` | Shared transport assertions for M0 qualification | Imported by the M0 harnesses |
| `m0-dual-canvas.py` | Run isolated OBS horizontal/vertical transport and copy-publisher qualification | `make m0-dual` |
| `m0_dual_checks.py` | Validate ordered streams and decoded video pixels | Dual-canvas harness and unit tests |

Private configuration and raw output remain in ignored `.env` and `runtime/`
paths. Only reviewed, sanitized evidence is copied into `docs/evidence/` for
versioning. Local binaries and dependencies live in ignored tool/dependency
directories. Do not commit personal credentials, browser-session automation, or
temporary agent scratch scripts here.

The directory is excluded from the Docker build context. The final application
image contains compiled executables and UI assets, not these development tools.
See the [development guide](../docs/development.md) for repository boundaries and
the [M0 evidence](../docs/evidence/m0-gates.md) for qualification limits.
