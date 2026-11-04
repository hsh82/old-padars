# Phase 1 test results

Updated: 2026-11-04

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

- `bench --site <isolated-site> migrate`: not executed; Padars is not installed on `kara.loc`.
- `bench --site <isolated-site> run-tests --app padars`: blocked by the local runtime. The available interpreter cannot load the cached Python 3.14 `orjson` extension, and the configured MariaDB host/library is unavailable from this environment.
- `ruff check .`: not executed because Ruff is not installed.
- `bench build`: not executed because the Bench wrapper/runtime is unavailable.
- Browser/UI smoke tests: not executed because no working Desk site/browser harness is available.
- Live Moodle/MuTMS tests: not executed because no sandbox endpoint or verified API contract is configured.
- Two-school authorization dataset: not created because database writes were not authorized or necessary for this audit.

Static checks are not classified as end-to-end or production verification.
