# Padars delivery roadmap and goals

This is the current delivery index. It preserves the approved architecture,
Phase 8 priority and completed phase work. Historical context remains in
[the implementation plan](implementation-plan.md) and
[the Phase 8 checkpoint](phase8-priority-checkpoint.md).

## Product goal

Deliver the approved integrated school MVP: Education academic records,
company-controlled MuTMS lifecycle, scoped school operations, Moodle learning
and grade integration, PlugNmeet attendance evidence, published report cards,
student/guardian experiences, and verified installation and release operation.
The approved twelve-domain document is still missing; recovering it and mapping
its exact domain names remains necessary for final domain closure. The existing
capability inventory is not a replacement domain list.

## Protected staging baseline

- `staging-1`: `81792d9`, served by `kara.loc`, for Stage 1 manual feedback.
- `codex/full-product`: ongoing work in the separate development worktree.
- Routine development tests target `padars-phase12-fresh.local`; the fresh-install
  gate additionally uses disposable `padars-release-fresh.local`. Never promote
  feature changes, schemas or assets into staging as an incidental test action.
- Preserve the two user edits in the original checkout. Stage 1 findings feed
  the defect backlog; they do not cancel the full product scope.

## Current status

| Phase | Status | Meaning |
| --- | --- | --- |
| 3 | Development handoff complete | Preserve registration; final regression and live SMS checks remain. |
| 4 | Development handoff complete | Curriculum/classes/offerings implemented; do not rebuild. |
| 5 | Development handoff complete | Staff/assignment/workload implementation preserved. |
| 6 | Development handoff complete | Native scheduling with Padars relationship and history safeguards. |
| 7 | Development handoff complete | Manual attendance/leave/care implemented; online evidence remains. |
| 8 | Implementation partial at product level; live gate blocked | Adapter and roster lifecycle exist; live service acceptance remains outstanding. |
| 9 | In progress | Draft entry, approval, schemes, corrections and immutable publication exist; Moodle grade discovery, approved mappings and reviewed draft imports exist; live/browser/concurrency acceptance remains. |
| 10 | In progress | Verified family report access and weekly timetable/course/attendance views exist; published learning selections and per-child completion are connected; asynchronous evidence and teacher overview are connected; remaining live/combined experiences and final acceptance remain. |
| 11 | Unfinished | Comprehensive installation, integration, security and release gates remain. |

## Milestone goals and completion evidence

| Goal | Work and dependencies | Required completion evidence |
| --- | --- | --- |
| G1: Live Phase 8 acceptance | Authorized Moodle connection, roles and host allowlist; existing tenant/course/user/enrollment services | One unique tenant, one course, one teacher and three students verified remotely; retries, replacements, withdrawals and reconnect reuse identities; school users denied infrastructure controls and cross-tenant access. |
| G2: Close Stage 1 workflow defects | Preserve Phases 4–7; reproduce reported failures and repair connections | School setup → registration → enrollment → class → teacher → schedule → attendance and draft/approved marks work for intended roles; targeted regression for each material defect. |
| G3: Learning and session evidence | Actual supported Moodle/PlugNmeet APIs; Course Schedule and offering/user mappings | Teacher selects eligible activities; session-specific evidence has provenance, time boundaries, policy version and deduplication; missing data stays unavailable/pending; reviewed outcomes write native attendance. |
| G4: School assessment scheme | Education criteria/plans/results; explicit school configuration | Versioned configurable scales/weights/coverage validated and approved by the appropriate school role; no invented national formula; manual and imported sources have defined conflict rules. |
| G5: Moodle grade reconciliation | G1 and G4; stable course/student/grade-item mappings | Raw source grades retained with provenance; explicit normalization; changed/missing/conflicting items shown for review; approved imports reuse Education results and cannot overwrite approved/published outcomes. |
| G6: Official report publication | G4; approved Education results; G5 for Moodle-sourced components | Term/annual calculation follows the approved scheme; authorized review/publication; immutable snapshot, correction history and reproducible print/PDF; drafts and private comments excluded from student delivery. |
| G7: Student/guardian product experience | Published records and verified Education Guardian relationships; G3 learning views | Mobile/keyboard-usable timetable, courses, deadlines, attendance and published results; guardian sees only linked students; direct endpoints deny unrelated/draft/private data. |
| G8: Unified access and operations | Existing authorized identity architecture; supported integration configuration | Tested Moodle launch/SSO without password exchange or browser tokens, or explicitly documented external blocker/fallback; approved announcements and operational Phase 10 features connected. |
| G9: Installable release candidate | Coherent completed workflows; opt-in external integrations | Current supported app versions install fresh alongside Education; setup/migration repeatable; assets, jobs, indexes, configuration, backup/restore and uninstall preservation documented and verified. |
| G10: Phase 11 acceptance | G1–G9 plus exact approved domain matrix | Product scenarios A–J pass with realistic fixtures, role/security negatives, browser flows, live services, concurrency/performance and staging/pilot evidence. Every missing gate stays incomplete. |

## Execution order

First address G1 when authorized service configuration exists. While its external
gate is blocked, advance G2 and independent G4/G6 implementation. Resume
learning/evidence work G3 as its actual API contracts become available, then
finish G5–G9 in dependency order and run G10. Phases 5–7 remain preserved; add
only missing product connections. Do not restart Phase 8 from scratch.

G4 now has a focused implementation of versioned manager-approved schemes.
G6 has coverage-checked immutable publication, successor versions, student and verified-guardian
delivery and generated PDF. Twelve focused tests pass; browser/concurrency and
release acceptance remain open. Controlled Education mark corrections now have
focused implementation, including atomic rollback and protected audit metadata.
Verified guardian delivery is implemented. Student/family academic views are connected; fourteen focused tests pass. Moodle discovery, mapping and reviewed draft import are connected; sixteen focused integration tests pass. Learning discovery/publication and completion are connected; asynchronous session policies, reviewed evidence confirmation and correction are implemented; live meeting analytics and final acceptance remain. Development
changes are not promoted to staging.

## Work discipline and handoff

Each coherent milestone includes working backend and frontend contracts,
server-side authorization, focused meaningful tests, synchronized docs and a
reviewable commit. Do not count isolated models/buttons or mocked remote calls
as completed business workflows. After two evidenced attempts at a noncritical
external blocker, record it and advance independent work. Security/data-integrity
failures must be resolved before claiming readiness.

Update [PROJECT_HANDOFF](PROJECT_HANDOFF.md),
[VERIFICATION_BACKLOG](VERIFICATION_BACKLOG.md) and the domain matrix at each
milestone. Preserve the full objective across usage interruptions; automatic
resumption requires an available session and allowance.
