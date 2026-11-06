# Academic schedules and examinations

Padars reuses Education's dated `Course Schedule`, `Course Scheduling Tool`,
and submittable `Assessment Plan`. It adds no parallel timetable or exam model.
Education records remain authoritative.

The Education Course Scheduling Tool creates one dated Course Schedule for
each selected weekday in a date range. Padars permits School Managers and
platform administrators to run the batch operation, validates that the
Student Group belongs to the site's School and that the range stays within its
Academic Year or Term, and links each session to its matching non-archived
School Course Offering. A Padars class section must have an offering with an
assigned Teacher, and the session Instructor must match it.

Education rejects overlapping Student Group, Instructor, and Room bookings.
Padars adds the missing cross-checks between Assessment Plan examiners and
Course Schedule instructors, and between examiners/supervisors on competing
Assessment Plans. Assessment Plans must match their Student Group's Program,
Course, Academic Year and Term, occur within that period, and have an earlier
start time than end time. Padars class-section exams link to the matching
School Course Offering. Assessment Result context is copied from its
Assessment Plan; conflicting caller-supplied values are rejected.

Rescheduling through the Education tool is restricted to future sessions.
Past and current Course Schedules cannot be deleted. Sessions with attendance
cannot be deleted or replaced. The native tool treats its end date as
exclusive when generating occurrences but includes it in its deletion query;
Padars detects that boundary case. The replacement runs atomically: if any
session conflicts or cannot be removed, all attempted deletions and creations
are rolled back. Past/current Assessment Plans cannot be rescheduled, deleted,
or cancelled, and a plan with results cannot be moved or removed.

This provides weekly recurrence as individual dated Education records. It does
not implement automatic conflict resolution, room-capacity validation,
cross-school room sharing, examination grading policy, or grade approval.
