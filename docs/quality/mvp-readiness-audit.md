# MVP readiness audit

Basis: worktree at `880040f`, phase handoffs, implementation files and recorded
test evidence. This is a source/document audit, not a new release test run.
User edits in AGENTS.md and test_registration.py are preserved.

## Assessment

Estimated integrated MVP readiness: **45/100**. Engineering quality estimate:
**60/100**, provisional because browser, live integration and comprehensive
security acceptance remain outstanding. Scores express engineering judgment,
not test coverage or a measured defect rate. Product release: **not ready**.

| Capability | Weight | Estimated readiness |
| --- | ---: | ---: |
| Academic administration, staff, timetable, manual attendance | 20 | 80 |
| Registration, import and onboarding | 10 | 75 |
| Moodle/MuTMS tenant, course and roster lifecycle | 15 | 45 |
| Learning activities, PlugNmeet and attendance evidence | 15 | 5 |
| Assessment integration and report cards | 15 | 35 |
| Student and guardian experiences | 10 | 10 |
| Authorization and sensitive-data protection | 10 | 60 |
| Current installation and release verification | 5 | 30 |

Weighted readiness is 44.75, rounded to 45. The historical successful clean
installation does not verify a fresh install of today's full worktree.

## Confirmed defects and gaps

- Teacher Workload exists and grants School Manager report access, but
  `padars/reports.py` only allows the reviewed attendance report through its
  global wrapper for school users. Its native execution/export path is blocked.
- Official report-card preview/PDF is explicitly denied by
  `padars.education_api.preview_report_card`. The new approved-results review
  is a separate screen; it supplies no final calculation or publication.
- Immutable report publication, correction versions and student delivery are
  absent. School grading formulas still require explicit approval.
- Moodle grade-item mapping, grade import/reconciliation, activity discovery,
  completion, deadlines and participation evidence are absent from Padars.
- PlugNmeet containers were previously observed, but no Padars meeting/evidence
  integration is implemented. Their availability does not prove a class workflow.
- Guardian access remains denied by default; a connected student/guardian
  dashboard is missing. Registration routes are not a full student portal.
- Live Moodle acceptance is recorded as blocked by disabled web services and
  missing authorized token/role configuration. Contract/mock tests do not prove
  tenant creation, membership or isolation on a live service. This audit did not
  reconfigure or probe that service.
- Moodle unenrollment removes a manual course enrollment, not an individual
  role. Local conflicting-role guards cannot detect roles assigned independently
  in Moodle; live reconciliation needs an explicit policy and verification.
- Offering identity is annual. Term consistency and report completeness cannot
  be inferred solely from offering existence; the current preview's missing-course
  warnings are not an approved grading scheme.
- Current assessment UI changes have syntax and server-test evidence, but no
  browser evidence for interaction, registration, or hostile-text rendering on
  the final code. Registration regression also has the recorded ERPNext fixture
  preload/module-filter limitation.
- Concurrency locks exist, but claims/results have not been concurrency-tested.
  School-sized query performance, worker recovery and cross-phase behavior need
  release testing. Several native reports/RPCs intentionally remain blocked.
- The approved twelve-domain list has not been recovered; the matrix explicitly
  remains incomplete. PROJECT_HANDOFF, ROADMAP and VERIFICATION_BACKLOG files do
  not exist under those names; implementation-plan, progress and phase reports
  currently hold portions of that information and need reconciliation.

## MVP delivery order and gates

1. Complete the live Phase 8 vertical journey: authorized operator configuration,
   one tenant/course/teacher and three students, then retry, withdrawal,
   replacement and disable/re-enable. Verify customer infrastructure denial and
   live tenant isolation. Record SSO separately from course-link navigation.
2. Close known academic connections: repair Teacher Workload execution/export,
   verify final registration and assignment/timetable/manual attendance journeys,
   and preserve existing completed Phase 4–7 work.
3. Implement selected activity discovery and mappings, PlugNmeet/session evidence,
   policy versions, deduplication, proposals and teacher review that writes native
   Education attendance. Preserve unavailable/pending evidence states.
4. Finish Phase 9: configurable school-approved schemes, Moodle grade mapping and
   provenance, normalization, conflict review, official Education results,
   immutable publication/correction versions and printable output. Do not invent
   national grading formulas or silently overwrite approved results.
5. Finish Phase 10: usable student dashboard and verified guardian relationships,
   scoped published report access, timetable, learning deadlines and permitted
   live-class links; complete approved communications and operational features.
6. Finish authentication/navigation and install packaging alongside Education.
   Test opt-in integrations, repeatable setup/migration, assets, scheduled jobs,
   operational runbooks, backup/restore and data-preservation behavior.
7. Run Phase 11 acceptance scenarios A–J on approved disposable environments:
   final automated suite, direct endpoint security, realistic school fixture,
   browser journeys, live integrations, concurrency/performance and staging/pilot
   readiness. Every unavailable service stays blocked, never counted as passed.

Each milestone needs backend, usable frontend, permission checks, focused tests,
documentation and a coherent commit. Security failures take priority. External
blockers can be recorded while independent work advances. Phase 4–7 development
handoffs are not grounds to repeat their implementation or to declare release
acceptance. The full approved scope remains the target.
