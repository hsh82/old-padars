# Permissions and tenancy

> Stage 1 supersedes the earlier broad same-school access model. The exact
> enforced role matrix is in [stage1-authorization.md](stage1-authorization.md).
> `Education Manager` is no longer a Padars platform bypass; `Administrator`
> and `System Manager` retain the documented recovery path.

The provisional architecture is one shared Frappe site with multiple schools. Platform administrators can administer all Padars records. Other users require both the appropriate Frappe role and an active School Membership for the record's School.

Padars uses both `permission_query_conditions` for list/report filtering and `has_permission` for direct document access. The hooks cover Padars records plus the school-linked Education records used by Phase 1: Program Enrollment, Student Group, Course Enrollment, Student, Instructor, Course Schedule, Assessment Plan, Assessment Result, and Student Attendance. Controller validation repeats school-link checks because query conditions do not protect background jobs or arbitrary server-side writes.

Program Enrollment and Student Group receive Padars Custom Fields; schedule and assessment records use the optional Course Offering link for school context, while attendance resolves through Student Group. Future APIs must require an explicit school context before returning Education data. File/report/API authorization needs dedicated tests before exposing portals.

