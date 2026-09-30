# PR 2 review dispositions

PR: https://github.com/camarokris/TDRestreamer/pull/2

The initial revision passed required build/integration CI but received findings
from Sourcery-ai, gitar-bot and SonarQube Cloud. Those findings were reviewed
individually; initial green CI did not justify merging. Updated automated review
results must be inspected before merge.

| Reviewer / finding | Disposition and verification |
|---|---|
| Sourcery: Python optimization removes asserts | Replaced qualification assertions with explicit fatal checks. Regression test runs the guard under `-O`; complete media harness rerun with `PYTHONOPTIMIZE=1` |
| Sourcery: versions/checksum recorded but not enforced | Added toolchain manifest and enforced exact MediaMTX/FFmpeg/OBS/websocket versions and MediaMTX Linux amd64 binary checksum, extracted from the verified release archive |
| Gitar: evidence hand-edited and browser version absent | Limitations emitted by the harness; browser version and source hashes recorded. Checked-in report copied byte-for-byte after a successful run and producing source hashes compared |
| Sonar: two CLI path-traversal findings | Removed CLI-controlled file reads. Both JS helpers read a fixed `runtime/m0/controller.json` path relative to their source |
| Sonar: empty method / repeated literals | Explained intentional HTTP-log suppression and extracted shared constants |
| Sonar: await in independent loops / unnecessary collection conversion | Independent OBS inputs and unauthorized clients now use `Promise.all`; dependent create/track operations remain ordered within each task. HLS resource set is frozen after playback stops |
| Sonar: error-constructor style | Changed to explicit `new Error` |
| Sourcery: generic subprocess audit warnings | Reviewed each call: executables and argument lists originate in this local synthetic harness; no shell is used and no request/CLI string supplies executable code. Added explicit `shell=False`, comments and narrowly scoped rule suppressions. This is a documented false-positive disposition, not an exception for arbitrary subprocess inputs |

No broad analyzer exclusions or lowered quality thresholds were added. Any new
finding on the revised PR still requires review; this record does not claim
reviewer approval or M0 completion.

Follow-up review: Sonar reported three maintainability findings in the new secure-
transport helper. TLS context managers were combined, and transport readiness,
track checks and rejection checks were separated into focused functions. The two
remaining subprocess audit annotations were moved to the call sites so formatting
does not detach them; the same no-shell rationale applies. Full media qualification
was rerun after these changes. All tracked files also passed SonarQube CLI 1.9.0
deterministic secrets scanning before subsequent inspection.
