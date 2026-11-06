# Daily academic operations

Education remains authoritative for class sessions, attendance, approved leave
applications, and Student Logs. Padars extends the existing records and
workflows; it does not introduce parallel session or attendance models.

## Attendance and late arrival

The native Student Attendance Tool remains the roster and bulk-entry workflow.
Padars replaces its unscoped attendance RPC with a server-side operation that
requires `manage_attendance` for the target group/session, resolves the roster
from active Student Group members, requires every active student exactly once,
and writes through the Student Attendance document lifecycle. It does not
commit independently of the Frappe request transaction. Attendance cannot be
marked for future dates, outside the group's academic year, or on holidays.

`padars_late_minutes` records late arrival from 0 to 1440 minutes. Late minutes
are valid only when the native status is Present; Padars does not add a new
status value that would be incompatible with Education's attendance reports.
Education's native duplicate rule makes Student Group/date attendance
incompatible with session attendance for the same student and date. Use one
attendance mode per group/date; scheduled teaching can be marked per Course
Schedule.

## Approved absences

The Education Student Leave Application form, fields, validation, and
submittable workflow remain in use. A Padars controller extension replaces
Education's unsafe `on_submit` and `on_cancel` side effects:

- Student Group leave applies to each scheduled Course Schedule in the selected
  date range. Course Schedule leave applies to exactly that one session date.
- Only the active student's group sessions are considered; holidays and ranges
  without sessions produce no attendance records and are rejected.
- New Student Attendance records link to the approved Leave Application. An
  existing Absent record can be associated with it while retaining its prior
  status for rollback. A Present record is not overwritten unless the native
  `Mark as Present` option is selected. Other conflicts require staff review.
- Cancelling a Leave Application cancels only attendance it created. If it
  reused a prior record, cancellation restores its previous status and clears
  the link. Direct attendance cancellation is rejected outside this workflow.

Students can create and edit their own draft applications, but cannot submit or
cancel them. School Managers and staff with an active attendance assignment can
approve or cancel within their scope. Student group lookup returns the current
student's own groups or groups the staff member may read.

## Student care and reporting

Education Student Log is retained for student-care notes. Read access requires
the `Padars Sensitive Records` role and an active assignment with sensitive
record access. Creating or editing notes additionally requires
`can_manage_student_care`; this flag also enables sensitive-record viewing for
that assignment. Records remain restricted to active students in assigned
groups/programs/offerings, and Student links cannot be changed after creation.

The Padars Daily Attendance Register is the only non-platform report enabled
for scoped academic roles. It reads Student Attendance through permission-aware
Frappe ORM APIs, so group/offer scopes apply to viewing and export. Other
unreviewed Education reports stay blocked for scoped academic roles.

## Verification limits

Focused integration tests cover bulk attendance, leave submission and
rollback, assignment isolation, and report row scoping. No browser workflow,
full Education suite, or cross-app suite was run. Live SMS and other LMS checks
are tracked separately under Phase 8.
