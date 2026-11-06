# Reviewed asynchronous attendance evidence

Education Course Schedule is the session, and Student Attendance is the official
record. `padars_session_mode` adds Physical/Online/Hybrid/Asynchronous without
replacing native scheduling. Existing sessions default to Physical. The current
Moodle completion policy is available only for an explicitly Asynchronous session;
it cannot infer attendance in a physical or live meeting.

## Policy and evaluation

Session Attendance Policy is a versioned, submitted school decision for one
session/offering. Assigned attendance staff select actual automatic-completion
activities using checkboxes, choose all/any, an explicit site-timezone evidence
window (at most fourteen days covering the session date), optional pass-required
semantics and a reason. Approval records actor/time and freezes that version.
New versions retain prior decisions. Manual tracking is excluded, and the
PlugNmeet module is excluded because its completion may be cumulative rather
than session-specific. Manual attendance remains available through Education.

Evaluation checks current school/session/offering bindings, active student/group,
submitted academic enrollment, enabled account, observed/desired LMS enrollment,
latest approved policy and latest successful learning snapshot. Snapshots retain
the immutable user mapping/remote-user identifiers behind local student status.
The evaluator revalidates those mappings, exact module/instance/tracking,
completion state and timestamp in the policy's captured timezone. Completion
pass/fail is distinct; pass-required rules accept only the pass state. A reported
override flag is retained for teacher review. The timestamp is Moodle's reported
completion timestamp, not a claimed exact submission or meeting join time.

Attendance Evidence Proposal is immutable and retry-idempotent. A positive rule
produces Proposed Present. Incomplete/nonqualifying evidence stays Pending
Evidence; stale/missing data becomes Evidence Unavailable. Neither marks absence.
An existing official record is Already Recorded and is not overwritten.

## Confirmation, reuse and correction

A teacher with native `manage_attendance` for the exact session/student reviews a
proposal and supplies a reason. Confirmation locks offering → student → session,
re-evaluates the source/policy/consumption fingerprint and writes a submitted
Education Student Attendance through its normal lifecycle. Future dates are
rejected. Immutable Attendance Evidence Review records actor, reason and source
proposal. A failed audit write rolls the attendance back. Retries reuse the
review and cannot undo a later override.

The review's immutable Attendance Evidence Use children reserve a unique
student/tenant-context/module key. The same activity cannot count for another
session, even if its completion timestamp changes. No reuse exception is enabled
in this milestone. One module may be relevant to engagement without qualifying as
attendance; evidence selection is independent of family activity publication.

Confirmed evidence attendance can be manually corrected to Present/Absent, with
late minutes supported for Present, through a reasoned action on its native form.
Every change retains previous/new status and late minutes, actor and time. Direct
status/late edits to evidence-backed records are blocked. Existing validated
leave approval/cancellation flags retain Education's controlled leave workflow
and its own prior-status/approval history. A confirmed source is never recycled
because attendance was overridden or leave was cancelled.

## Screens, permissions and boundaries

Course Schedule offers policy configuration and per-student evaluation for
Asynchronous sessions. The policy form selects supported discovered activities;
the proposal form confirms a positive proposal. Student Attendance offers scoped
review history and reasoned override only for evidence-backed records. Student
and guardian portals read the resulting official attendance and late minutes;
they cannot read source/proposal/review records or invoke teacher actions.
Private attachment and direct-share restrictions include these records and their
consumption children. Grade/learning provisioning credentials remain company-only.

## Verification and limitations

The focused scheduling/assessment module passed seventeen tests after the initial
evidence implementation. Its extended integrated journey additionally passed
positive confirmation, missing evidence, duplicate confirmation, cross-session
reuse denial after a changed timestamp, atomic rollback, immutable consumption,
reasoned status/late correction, revoked attendance permission and approved-leave
approval/cancellation. Five daily-operation tests passed for existing workflows.
The final expanded scheduling/assessment module passed eighteen tests, including
the native reference-role boundary test. The installed native form mandatory
checker also passed against all three affected form schemas.

This is not live service/browser/concurrency acceptance. PlugNmeet analytics,
meeting-duration policies, combined manual/live rules, automatic attendance
confirmation and reuse exceptions are not offered. They require verified source
contracts and further policy versions; no aggregate meeting attendance is inferred.
