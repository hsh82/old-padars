# Phase 1 test results

> Historical Phase 1 evidence from 2026-11-04. The current clean-site install
> and test-preloader result are in [Phase 0 results](phase0-results.md).

Updated: 2026-11-04

## Stage 1 WP01–WP03 runtime evidence

Environment: disposable `stage1.local` only. `kara.loc` was not migrated,
restarted, or modified.

| Check | Result | Evidence / limitation |
| --- | --- | --- |
| Migration with roles, scheduler sync, constraints, and Custom Fields | Passed | The first migration exposed unnamed fixture records; after the corrective fixture fix the rerun completed. |
| Runtime two-school authorization smoke | Passed | `bench --site stage1.local execute padars.tests.test_stage1_security.run_runtime_smoke` returned six passed checks: recovery access, manager list isolation, student direct-document denial, Education endpoint denials, Custom Fields, and indexes. Synthetic School A/B, two students, two managers, and an assigned teacher exist only on the disposable site. |
| Frappe suite invocation | Blocked | `bench run-tests --module padars.tests.test_stage1_security` aborts before Padars tests because ERPNext tries to create an already present `_Test Opening Invoice Company` fixture. Recorded as PAD-018. |
| Python / fixture / diff checks | Passed | `python -m compileall -q padars`, `jq empty padars/fixtures/custom_field.json`, and `git diff --check`. |
| Changed JavaScript syntax | Passed | `node --check padars/public/js/education/student_group.js`. |

The direct runtime smoke supplements, but does not replace, the blocked Frappe
test runner or remaining browser, report, file, job, and live-integration tests.

## Passed

Executed from the Padars app root:

```text
python3 -m compileall -q padars                         PASS
find padars -type f -name '*.js' -print0 | xargs -0 -n1 node --check  PASS
node --test tests/frontend/*.test.js                    PASS (2 tests)
find padars -type f -name '*.json' -print0 | xargs -0 -n1 jq empty  PASS
git diff --check                                         PASS
```

The existing Frappe test files cover School uniqueness/permissions, Course Offering relationship rules, and mock sync idempotency/failure/retry. They were not executed in this environment.

## Blocked or not executed

- `bench --site stage1.local migrate`: passed on the disposable site; it was never run against `kara.loc`.
- `bench --site stage1.local run-tests --module padars.tests.test_stage1_security`: blocked before Padars tests by the existing duplicate ERPNext test fixture (PAD-018). The isolated direct runtime smoke passed separately.
- `ruff check .`: not executed because Ruff is not installed.
- `bench build`: not executed because the Bench wrapper/runtime is unavailable.
- Browser/UI smoke tests: not executed because no working Desk site/browser harness is available.
- Live Moodle/MuTMS tests: not executed because no sandbox endpoint or verified API contract is configured.
- Two-school authorization dataset: not created because database writes were not authorized or necessary for this audit.

Static checks are not classified as end-to-end or production verification.
