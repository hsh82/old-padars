# Staff management and academic scope

Education owns Instructor records. Padars adds a read-only `padars_user` link
and qualification child table to Instructor; a School Manager links an active
Instructor to one enabled Frappe System User through
`padars.staff.link_instructor_to_user`. The service grants the scoped Teacher
role and creates or reuses that user's active Teacher School Membership. A
Frappe User cannot be linked to multiple Instructors.

Teacher assignment is performed through
`padars.staff.assign_teacher_to_offering`. It checks the School Manager's
Course Offering, active Instructor, Instructor-to-User link, and enabled
System User, then updates the Education Instructor on the offering and creates
or reuses the matching Academic Assignment. Unassignment deactivates the
assignment. Direct Instructor edits to an offering are blocked by server
validation.

Academic Assignment supports four types:

| Type | Scope | Additional rule |
| --- | --- | --- |
| Scoped Staff | Program, Student Group, or Course Offering | User must already have a Padars staff role; action flags decide writes. |
| Teacher | One Course Offering | Instructor, linked User, and offering must match. |
| Grade Coordinator | Program | Program has a configured grade; grants grade entry within that scope. |
| Class Supervisor | Student Group | Group must be a Padars class section; grants attendance management within that group. |

Only School Managers and platform administrators can create or change these
assignments. The controller validates the current site's School context, the
linked records, enabled System User status, assignment dates, and duplicate
active user/scope keys. List conditions and document permission hooks enforce
the active, date-valid scope; role membership by itself does not grant access.
Deactivation removes effective authorization even if the Frappe role remains
assigned to the User.

Instructor Qualification child rows reference an Education Course and an
optional grade from 7 through 12. Duplicate Instructor/Course/Grade rows are
rejected. Teacher Workload is a School Manager report that totals expected
weekly hours from accessible Draft and Active Course Offerings by academic
year. It is planning data, not measured attendance, payroll, or time tracking.
