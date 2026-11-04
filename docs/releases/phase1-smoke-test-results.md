# Padars Phase 1 smoke-test results

Updated: 2026-11-04

## Execution status

**NOT DEPLOYED / NOT EXECUTED ON STAGING**

No staging target was identified. `kara.loc` is a development site without Padars installed, and no database or service mutation was performed.

## Static and local checks

Passed locally:

- Python compilation: `python3 -m compileall -q padars`.
- JavaScript syntax: `find padars -type f -name '*.js' -print0 | xargs -0 -n1 node --check`.
- Frontend smoke tests: `node --test tests/frontend/*.test.js` — 2 passed.
- JSON validation: `find padars -type f -name '*.json' -print0 | xargs -0 -n1 jq empty`.
- Mock adapter contract check for tenant, user, course, and enrollment shapes.
- Whitespace validation: `git diff --check`.

## Roadmap acceptance tests

| Test | Status | Reason |
| --- | --- | --- |
| 1. School A cannot read School B | NOT EXECUTED | Requires disposable Frappe site, roles, direct URLs, reports, files, APIs, and jobs. |
| 2. New/returning/duplicate Excel import | NOT EXECUTED | Bulk import contract and UI are missing. |
| 3. Durable Student, annual enrollment, and User | NOT EXECUTED | Code exists, but database/browser verification is unavailable. |
| 4. Student sees only authorized courses | BLOCKED | Portal and SSO target are not configured. |
| 5. Exactly one tenant per school | BLOCKED | Live MuTMS tenant API is unavailable; mock only. |
| 6. Exactly one Moodle course per offering | BLOCKED | Live MuTMS tenant/category API is unavailable; mock only. |
| 7. Correct teacher/student enrollment | NOT EXECUTED | Live role/enrollment orchestration is incomplete. |
| 8. Moodle outage recovery without duplicates | PARTIAL | Mock failure/retry/idempotency code exists; no Frappe worker/live outage test. |
| 9. Approved first/second-term report cards | NOT EXECUTED | Publication/versioning service is missing and grade rules are not approved. |
| 10. New year preserves history | NOT EXECUTED | Requires database dataset and report snapshots. |

SSO redirect/session testing was not performed. Mock provisioning is not classified as live integration.
