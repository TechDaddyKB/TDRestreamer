# SonarQube coverage import

Setup date: 2026-09-30. Project: `camarokris_TDRestreamer`.

PR #6 was merged as `e78f7d9` before coverage implementation began in
[PR #7](https://github.com/camarokris/TDRestreamer/pull/7).

## Import evidence

[CI run 36744150459](https://github.com/camarokris/TDRestreamer/actions/runs/36744150459)
at `222afeb` successfully generated and imported all three reports:

- Python Cobertura sensor parsed `coverage/python.xml`.
- Go Cover sensor loaded `coverage/go.out`.
- JavaScript/TypeScript Coverage sensor analyzed `web/coverage/lcov.info`.

There were no unresolved source paths in the LCOV/Python reports. Go warned
only about the deliberately excluded generated sqlc files. SonarQube's PR API
reported 18.4% coverage, 17.6% line coverage, 24.6% branch coverage, and 1,810
lines to cover. These are the initial imported snapshot, not release targets.
The main-branch dashboard updates after the merged workflow runs.

The scan correctly failed its gate on `githubactions:S8541`: pip could install
a source distribution. The workflow now uses `--only-binary :all:`. Gate
thresholds and issue severity were not reduced to bypass this finding.

## Review and validation

Gitar's source/test overlap finding was addressed with explicit, matching test
exclusions; the bot confirmed the fix in `222afeb`. Sourcery and CodeQL passed
that revision. The final revision must pass all reviews and CI before merge.

Local `make coverage` passed Go race tests, two Vitest tests, and six Python
tests. Lint, documentation validation, builds, and deterministic secret scans
passed. CI integration exercised PostgreSQL, browser journeys, and FFmpeg tests.
Only unit runs contribute to these coverage reports; no live platform or
hardware qualification is inferred from coverage.

Automatic analysis was switched off in project settings. The dedicated CI token
is stored only in GitHub's `SONAR_TOKEN` repository secret and expires
2026-12-29. No token value is in this evidence or source control. See the
[developer coverage guide](../development.md#test-coverage-and-sonarqube-cloud)
for reproduction, rotation, fork restrictions, and report troubleshooting.
