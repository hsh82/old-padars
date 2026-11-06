# Phase 7 progress and verification

Date: 2026-11-06. Phase 7 daily academic operations are implemented and
focused-verified for development handoff. This is not a release approval.

Education's Course Schedule, Student Attendance, Student Leave Application,
Student Log, and Student Attendance Tool remain authoritative. Padars adds
scoped attendance marking, late minutes, safe leave attendance effects,
student-care assignment controls, and one permission-aware attendance report.
The Education source was not modified.

On `padars-phase12-fresh.local`, `padars.tests.test_daily_operations` passed
five tests. They cover authorized roster marking and updates, late-minute
constraints, unauthorized group access, approved leave session records,
restoration of pre-existing Absent attendance, cancellation isolation,
student-owned group lookup, Student Log assignment isolation, and report
row-level scope. The Phase 5 staff module passed 5 tests and Phase 6 scheduling
passed 6 tests after the Phase 7 permission hooks were added. The disposable
site migration completed successfully. Python compilation, JSON parsing, and
`git diff --check` passed; no other app suite or browser flow was run.

See [daily operations architecture](../architecture/daily-academic-operations.md)
and [permissions](../architecture/permissions.md).

## Operational limits

- Approved leave requires scheduled Course Schedule records. Student Group
  applications cover every scheduled session in the period; Course Schedule
  applications cover one session date. Periods with no teaching sessions are
  rejected.
- If an existing record says Present and the application is not marked
  `Mark as Present`, approval is blocked for staff review. An existing Absent
  record is associated with the application and restored if it is cancelled.
- Student Log permissions are scoped by explicit Academic Assignment flags.
  The notes themselves remain sensitive and must follow the school's retention
  and access policies.
- Education's native duplicate rule limits group/date records when that
  student already has session attendance for the date. Use a single attendance
  mode per group/date.
- Browser interaction, accessibility, report export UX, and the full Education
  compatibility suite remain for the later integration/release phase.
