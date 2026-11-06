# Permissions and tenancy

Each school has its own Frappe site and database. One active School identifies
the site; School Membership is not an access prerequisite. Platform
administrators and System Managers retain the recovery path. The initial
primary manager receives Padars School Manager and Academics User roles;
changing that manager does not automatically revoke roles from the old user.

Education grants `Academics User` broad level-0 User permissions. Padars does
not alter that shared DocPerm. For school-manager sessions, Padars User list
conditions and document checks limit User records to the manager's own account;
User attachments are similarly limited. This preserves Education's role for
other users while blocking a manager's direct reads, edits, password changes,
and uploads against another account. User role and API credential fields remain
at Education's System Manager-only permission level. Registration services
create student accounts through their narrowly scoped server-side paths.

School managers have school-wide academic access, subject to action permissions.
Academic staff, teachers, grade-entry staff and read-only users need both the
relevant role and an active, date-valid Academic Assignment. Assignments cover
a Program, Student Group or School Course Offering, and carry separate flags
for editing, marks, attendance, sensitive-record viewing, and student-care
record management. Program scope includes its groups; offering scope remains
narrower. List filters and document checks both enforce scope. Scoped staff
cannot change defining relationships or a group roster to expand their own
access. Student accounts can access their own supported records, but do not
receive a full Student Group roster. Guardian access is closed pending verified
relationships.

Teacher links are managed by a server-side action that pairs one active
Education Instructor with one enabled Frappe System User and a Teacher school
membership. Assigning that Instructor to a Course Offering creates or updates
the corresponding scoped Teacher assignment. Grade Coordinator assignments
target a Program and grant the grade-entry action within that scope; Class
Supervisor assignments target a Padars class section and grant attendance
management there. Role membership alone grants no academic data access: active,
date-valid assignments and action flags remain required. Deactivating an
assignment removes its effective scope even though the Frappe role can remain
on the User for historical or other assignments.

Instructor subject/grade qualifications are child rows on Education Instructor
and reference Education Courses. The Teacher Workload report reads accessible
Course Offerings and reports expected weekly hours; it does not calculate
actual hours or payroll.

The native Education Course Scheduling Tool is restricted to School Managers
and platform administrators because its reschedule action deletes existing
Course Schedules. Scoped teachers and academic staff continue to use
permission-checked individual schedule records within their assignments.

Frappe custom permission types control `enter_grade`, `manage_attendance`,
`view_sensitive_student_data`, `manage_student_care`, and `manage_moodle`;
`approve_grade` permits School Managers to submit individual Assessment Results;
teachers cannot submit and cancellation/correction remains closed. Student Log access
requires the `Padars Sensitive Records` role and an active scoped assignment;
creating or editing a note also requires `can_manage_student_care`. Student
care is not automatically granted to School Managers.

The Education Student Attendance Tool is available to managers and staff with
an attendance-capable assignment. Its Padars RPC requires the full active
roster and an authorized group/session, then saves native Student Attendance
records without committing outside the request transaction. Late minutes are
stored separately from native status and can be set only for Present records.
Submission is assignment-scoped. Direct attendance cancellation is blocked;
leave-linked records can be cancelled or restored only through their approved
Student Leave Application.

Students can create and edit their own Student Leave Application drafts.
Managers and attendance-assigned staff can submit or cancel within scope.
Education's unscoped attendance side effects are replaced: group leave applies
to scheduled sessions in its date range, and session leave applies to one exact
Course Schedule date. Cancelling a leave application affects only its linked
attendance records and restores the prior status of any reused Absent record.

The Padars Daily Attendance Register is the only reviewed report available to
scoped academic roles. It uses permission-aware Student Attendance reads for
both report execution and export. Other unreviewed reports remain blocked.
Bulk submission and cancellation of Assessment Results by non-platform users remain
disabled. A Moodle manager is separate from a school manager; credentials
remain server-side. Tenant provisioning is platform-only.

Initial installation adds role permissions and initializes action defaults
after fixtures are synchronized. Frappe copies standard permissions into
Custom DocPerm when customization starts. Subsequent administrator changes to
the action defaults are preserved; review role permissions after upstream
Education changes.

Academic attachments, including Student Leave Application files, must be
private site files and require access to their parent record. Direct DocShares of protected records or their files are
rejected. Install and migration validate existing shares and attachments and
stop for unsafe records without deleting them. Reports and selected Education
RPCs that have not been reviewed for scope are disabled for academic users;
some native workflows therefore remain unavailable until scoped replacements
are implemented. This is not a complete audit of all upstream endpoints.
