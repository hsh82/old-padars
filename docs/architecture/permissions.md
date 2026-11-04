# Permissions and tenancy

The provisional architecture is one shared Frappe site with multiple schools. System Manager and Education Manager can administer all Padars records. Other users require an active School Membership for the record's School.

Padars uses both `permission_query_conditions` for list/report filtering and `has_permission` for direct document access. Controller validation repeats school-link checks because query conditions do not protect background jobs or arbitrary server-side writes.

Education records do not all become school-scoped in the first patch. Program Enrollment and Student Group receive Padars Custom Fields; future APIs must require an explicit school context before returning Education data. File/report/API authorization needs dedicated tests before exposing portals.

