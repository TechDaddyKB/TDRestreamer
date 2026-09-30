# Contributing

Use short feature branches and focused commits. Open a pull request against main;
CI must pass before merging. Include tests, user/API documentation and updated
requirement evidence with each behavior change. Do not commit credentials, real
stream captures, database data or backup archives. Use synthetic fixtures.

Run `make check` and relevant integration tests. Report actual commands, hardware,
versions, accounts and limitations in docs/evidence. Never mark a skipped external
or hardware test as passed. Preserve the original specification and record changes
in ADRs. Comments explain invariants and tradeoffs, rather than restating syntax.

License contributions under AGPL-3.0-or-later. Read SECURITY.md before reporting
security issues. No cloud spending or public broadcasting through default tests.
