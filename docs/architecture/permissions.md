# Permissions and tenancy

The provisional architecture is one shared Frappe site with multiple schools. System Manager and Education Manager can administer all Padars records. Other users require an active School Membership for the record's School.

Padars uses both `permission_query_conditions` for list/report filtering and `has_permission` for direct document access. The hooks cover Padars records plus the school-linked Education records used by Phase 1: Program Enrollment, Student Group, Course Enrollment, Student, Instructor, Course Schedule, Assessment Plan, Assessment Result, and Student Attendance. Controller validation repeats school-link checks because query conditions do not protect background jobs or arbitrary server-side writes.

Program Enrollment and Student Group receive Padars Custom Fields; schedule and assessment records use the optional Course Offering link for school context, while attendance resolves through Student Group. Future APIs must require an explicit school context before returning Education data. File/report/API authorization needs dedicated tests before exposing portals.

