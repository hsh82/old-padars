# Verification backlog

This tracks unclosed gates. Earlier focused passes are evidence for the covered
rules, not whole-product acceptance. See phase quality reports for commands and
results. Latest portal/guardian/assessment/grade-import module: eighteen integration tests passed on the disposable development site.

| Gate | Status | Required next evidence |
| --- | --- | --- |
| Stage 1 manual journeys | Awaiting user feedback | Execute stage1-manual-test-guide on `kara.loc`; record PASS/FAIL/BLOCKED and exact role/action/error. |
| Phase 3 final regression | Outstanding | Final import/upload/activation/shared-phone journey; fix standard fixture preload or use a genuinely scoped verified runner. |
| Live SMS | External dependency | Verify configured Frappe provider only if required for the intended deployment; disabled-mode behavior remains explicit. |
| Live Moodle/MuTMS | Blocked on authorized service setup | Goal G1, including actual remote isolation, roles and recovery. Fake clients do not close this gate. |
| Independent Moodle role assignments | Unresolved | Explicit reconciliation policy and live tests for manual unenrollment removing whole enrollment. |
| Assessment UI | Outstanding | Final renderer behavior, hostile text, stale edits, loading/error/retry states and manager review in a browser. |
| Assessment concurrency | Outstanding | Competing draft creates/updates and identity claims; verify locking and stale revision rejection across connections. |
| Grading scheme and publication | Focused implementation; release checks outstanding | Eleven focused tests now cover schemes, coverage, publication versions, own-student access and PDF. Browser journeys, concurrent publication, real approved school schemes and cross-connection correction checks remain. |
| Learning and PlugNmeet evidence | Learning and asynchronous evidence focused-tested; live meeting evidence pending | Actual session-specific data, policy evaluation, unavailable sources, deduplication and authorized override. |
| Guardian/student isolation | Focused report-access checks passed | Verified native links, account creation, list/read denial, revocation and source changes tested; weekly timetable/attendance/withdrawal and course-link contract tests passed; learning views, browser flow and final endpoint audit remain. |
| Full endpoint/report audit | Outstanding | Customer restrictions, Files/DocShares, reports, RPCs, User administration and privileged customization denial. |
| Fresh current-build installation | Schema/package gates passed; full acceptance outstanding | Disposable fresh bootstrap recovered after fixing fixture order; repeated migration and 26 DocType/fixture/index checks passed with LMS disabled. Clean first-attempt CI and isolated assets/browser acceptance remain. |
| Recovery and deployment | Partial | Backup exists for Stage 1; restore has not been verified. Prove restore and document compatible code/schema/assets. |
| Realistic school performance | Outstanding | Profile permission scopes, timetable, rosters, grade/report queries, queue backlog and bounded retries. |
| Full Phase 11 suite | Not started | Current build passes product scenarios A–J and all agreed release criteria; record unperformed/blocked services accurately. |
| Twelve-domain closure | Source missing | Recover the exact approved list and map requirements/evidence; do not invent substitute domains. |

No usage-limited, externally blocked or unperformed gate may be marked passed.

Moodle grade-source discovery: two focused database tests pass. Contract tests
exercise the installed report shape and cross-tenant/category/user rejection.
Mock calls do not verify actual service capabilities or live grade delivery.
Approved mappings, explicit normalization and reviewed Education draft imports now pass focused checks. Live service/browser/concurrency gates remain open.

Learning source/publication: 17 focused integration tests and 15 offline adapter
contracts passed. An extended focused journey verifies changed dates are held
for teacher review. Live service/worker/browser evidence remains unperformed.
Session-specific asynchronous policy/evidence evaluation and reviewed native attendance are implemented. Live/combined rules and final acceptance remain.

Stable identity lifecycle: actual framework rename/merge tests passed for bound
School/Offering/User/Student records and unbound Student compatibility. Reviewed
bound email/key migration and other academic master rename cases remain open.

## Staging 2 priority (2026-11-06)

User requested a separate working Staging 2 before further feature work. Twelve
native Role Profile presets now install repeatably without changing customized
profiles. Customer presets exclude System Manager and Academics User; only the
company administrator preset includes infrastructure privileges. Fixed-role
services preserve native multi-profile semantics and reject escalated profiles.
Managers receive native enrollment/assessment-plan submission without broad
roles. Existing Student Customer name/image projection is narrowly synchronized;
unauthorized Customer retargeting is rejected. Focused regressions pass.
Separate runtime deployment and role-login acceptance remain to be performed.
Stage 1 checkout, database, workers and assets must remain untouched.

Staging 2 preparation verification: all 23 focused scheduling/product tests pass
on `padars-phase12-fresh.local`, including default-profile repeatability, safe
role grants, manager permission boundaries and existing Customer projection.

Staging 2 installation now passes on its independent `stage2.kara.loc` site.
Synthetic academic seeding, native private intake upload/download and role HTTP
checks pass. User-profile landing pages are verified. The current-day assessment
comparison defect was traced to SQL date/timedelta versus incoming strings;
canonical date/time comparisons fix unchanged submissions without permitting
real past rescheduling. All 24 focused product tests pass. Final deployment
snapshot promotion and synthetic publication verification follow this commit.

## Staging 2 ready for manual testing (2026-11-06)

The installed product snapshot includes `fb8953c` (twelve default profiles) and
`76b7457` (assessment schedule fix and staging tooling), followed by the final
deployment-record commit. The local `staging-2` branch and independent clone
are pinned to that record. Open `http://stage2.kara.loc/login`; map the name to
the same server IP as `kara.loc` if needed. See [manual guide](STAGING_2_TEST_GUIDE.md)
and [deployment tooling](../../scripts/staging2/README.md). Credentials are in the
owner-only private file documented in the guide, outside Git.

Verified: genuine fresh Frappe/ERPNext/Education/Padars install with twelve
profiles; 26 DocType/fixture/index gate; all 24 focused product tests; real HTTP
manager/teacher/student/guardian login and role landing; academic lists; teacher
three-student roster; own timetable/attendance; native saved-parent private CSV
upload/download; unrelated attachment denial; private-file/student/guardian
isolation; real teacher mark entry, manager approval and three report-card
publications; scoped report pages and generated PDF; app JS assets; realtime
transport HTTP 200; one worker online and scheduler enabled. New seeds are
repeatable and preserve credentials/data. Runtime proxy now resolves changing
Docker upstream addresses instead of retaining a stale address after restart.

Not verified: interactive browser acceptance, execution of a new CSV/Excel
identity batch on this new site, SMS delivery, live Moodle/MuTMS/PlugNmeet or SSO,
performance/concurrency and final Phase 11 release acceptance. LMS/SMS remain
disabled; mocked or absent services are not reported as live. Follow the user’s
staging-test priority; collect feedback before another staging promotion. Keep
Stage 1's original branch/worktree, including new user edits, untouched.
