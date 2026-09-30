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

## Main-branch result

PR #7 merged as `8e2359c`. Its final PR checks all passed, including SonarQube,
Sourcery, Gitar, and CodeQL. The first
[main CI run](https://github.com/camarokris/TDRestreamer/actions/runs/36745440744)
passed tests, integration, and builds and published the same 18.4% overall
coverage. Its quality gate **failed** on new-code coverage: 5.4% against the
existing 80% requirement. The main new-code period starts at the previous-version
baseline (2026-09-30 14:10:58 UTC); it covers more code than the configuration-only
PR diff. This is exposed testing debt, not an import failure. Do not reset that
baseline, lower the threshold, or exclude production code to make it green.

The `sonar` GitHub Actions check is now required by main branch protection,
alongside `checks` and `integration`. Coverage reporting is operational; the
main-branch coverage gate is not yet satisfied.

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

PR #16 classifies `scripts/m0-dual-canvas.py` as test code in both matching
Sonar test/source patterns. It is a standalone hardware qualification harness,
not product code; its NVENC path cannot execute in hosted CI. The shared FLV
and stream-checking helpers remain in source coverage, with negative controls
for the four-rendition ladder. This classification does not change coverage
thresholds or exclude application code.
