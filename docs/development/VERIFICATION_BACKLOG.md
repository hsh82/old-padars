# Verification backlog

This tracks unclosed gates. Earlier focused passes are evidence for the covered
rules, not whole-product acceptance. See phase quality reports for commands and
results. No new test run was performed for this roadmap update.

| Gate | Status | Required next evidence |
| --- | --- | --- |
| Stage 1 manual journeys | Awaiting user feedback | Execute stage1-manual-test-guide on `kara.loc`; record PASS/FAIL/BLOCKED and exact role/action/error. |
| Phase 3 final regression | Outstanding | Final import/upload/activation/shared-phone journey; fix standard fixture preload or use a genuinely scoped verified runner. |
| Live SMS | External dependency | Verify configured Frappe provider only if required for the intended deployment; disabled-mode behavior remains explicit. |
| Live Moodle/MuTMS | Blocked on authorized service setup | Goal G1, including actual remote isolation, roles and recovery. Fake clients do not close this gate. |
| Independent Moodle role assignments | Unresolved | Explicit reconciliation policy and live tests for manual unenrollment removing whole enrollment. |
| Assessment UI | Outstanding | Final renderer behavior, hostile text, stale edits, loading/error/retry states and manager review in a browser. |
| Assessment concurrency | Outstanding | Competing draft creates/updates and identity claims; verify locking and stale revision rejection across connections. |
| Grading scheme and publication | Implementation pending | G4/G6 calculations against approved examples; permission tests; immutable snapshots/corrections and print reproduction. |
| Learning and PlugNmeet evidence | Implementation/live contracts pending | Actual session-specific data, policy evaluation, unavailable sources, deduplication and authorized override. |
| Guardian/student isolation | Implementation pending | Linked-student access plus direct endpoint negatives for unrelated users and unpublished records. |
| Full endpoint/report audit | Outstanding | Customer restrictions, Files/DocShares, reports, RPCs, User administration and privileged customization denial. |
| Fresh current-build installation | Outstanding | G9 on a disposable site; optional integrations disabled must not block basic setup. |
| Recovery and deployment | Partial | Backup exists for Stage 1; restore has not been verified. Prove restore and document compatible code/schema/assets. |
| Realistic school performance | Outstanding | Profile permission scopes, timetable, rosters, grade/report queries, queue backlog and bounded retries. |
| Full Phase 11 suite | Not started | Current build passes product scenarios A–J and all agreed release criteria; record unperformed/blocked services accurately. |
| Twelve-domain closure | Source missing | Recover the exact approved list and map requirements/evidence; do not invent substitute domains. |

No usage-limited, externally blocked or unperformed gate may be marked passed.
