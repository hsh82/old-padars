# Phase 6 progress and verification

Date: 2026-11-06. Phase 6 implementation and focused verification are complete
for development handoff. Comprehensive browser and cross-app verification
remain in the later integration/release phase.

The source review confirmed Education already owns dated Course Schedules, a
weekday/date-range scheduling tool, and Assessment Plans with room, time, and
Student Group links. Padars extends these native records instead of creating a
second timetable or exam model. Class-section sessions and exams resolve to
their annual School Course Offering; schedules must use its assigned Teacher.
Assessment Results must retain the context of their Assessment Plan.

Education already rejects overlapping groups, instructors, and rooms. Padars
adds the missing Assessment Plan examiner/supervisor versus Course Schedule
instructor checks and Assessment Plan date/time/context validation. Batch
rescheduling is School Manager/platform-only, future-only, protected when
attendance exists, and atomic. Past/current schedules and exams are retained;
plans with results cannot be moved or removed.

On `padars-phase12-fresh.local`, `padars.tests.test_scheduling` passed all six
tests. Coverage includes manager-only weekly scheduling, offering linkage,
group/teacher/room conflicts, exam examiner conflicts, Assessment Plan and
Result relationships, atomic rollback on conflicts, the native exclusive-end
date edge case, and past/current history protection. After Phase 7 permission
hooks were added, the Phase 5 staff module passed 5 tests and this Phase 6
module passed all 6 again. Python compilation, focused JSON parsing, JavaScript
syntax checks, and `git diff --check` passed. No other app suite or browser
tests were run.

See [scheduling architecture](../architecture/academic-scheduling.md).
Phase 7 daily attendance and student-care workflows are implemented; see
[Phase 7 results](phase7-progress.md).
