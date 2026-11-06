# Verification backlog

This tracks unclosed gates. Earlier focused passes are evidence for the covered
rules, not whole-product acceptance. See phase quality reports for commands and
results. Latest guardian/assessment module: twelve integration tests passed on the disposable development site.

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
| Learning and PlugNmeet evidence | Implementation/live contracts pending | Actual session-specific data, policy evaluation, unavailable sources, deduplication and authorized override. |
| Guardian/student isolation | Focused report-access checks passed | Verified native links, account creation, list/read denial, revocation and source changes tested; full academic portals, browser flow and final endpoint audit remain. |
| Full endpoint/report audit | Outstanding | Customer restrictions, Files/DocShares, reports, RPCs, User administration and privileged customization denial. |
| Fresh current-build installation | Outstanding | G9 on a disposable site; optional integrations disabled must not block basic setup. |
| Recovery and deployment | Partial | Backup exists for Stage 1; restore has not been verified. Prove restore and document compatible code/schema/assets. |
| Realistic school performance | Outstanding | Profile permission scopes, timetable, rosters, grade/report queries, queue backlog and bounded retries. |
| Full Phase 11 suite | Not started | Current build passes product scenarios A–J and all agreed release criteria; record unperformed/blocked services accurately. |
| Twelve-domain closure | Source missing | Recover the exact approved list and map requirements/evidence; do not invent substitute domains. |

No usage-limited, externally blocked or unperformed gate may be marked passed.
