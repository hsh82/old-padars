# Phase 5 progress and verification

Date: 2026-11-06. Phase 5 implementation and focused verification are complete
for development handoff. Browser and broader Education compatibility checks
remain for the later integration/release phase.

School Managers can link an active Education Instructor to one enabled Frappe
System User, assign and unassign Teachers on Course Offerings, manage scoped
Grade Coordinator and Class Supervisor assignments, maintain Instructor
Course/Grade qualifications, and view expected Teacher workload. Assignment
controllers validate school context and role-specific scopes. Existing
permission hooks require an active, date-valid assignment and its action flag
for scoped staff. Education Instructor and Course remain authoritative records.

On `padars-phase12-fresh.local`, the focused
`padars.tests.test_staff_management` module passed all five tests. Coverage
includes Instructor mapping and uniqueness, Course Offering assignment and
unassignment, cross-scope read denial, Grade Coordinator grade-entry scope,
Class Supervisor attendance scope, manager-only staff actions, duplicate
qualifications, and workload aggregation. The schema and role migration had
already completed on this disposable site as recorded at the Phase 8 return
checkpoint. No other app's tests or browser tests were run.

The initial saved result of 3 passed / 2 failed was diagnosed. Phase 8 added a
second Instructor mapping guard; the Phase 5 linking service now satisfies both
guards. The failing unassignment path also retained an active-only Instructor
match invariant after deactivating an assignment; that check now applies only
to active assignments. The focused module now passes 5/5.

See [staff architecture](../architecture/staff-management.md) and
[permission model](../architecture/permissions.md). No live Moodle action is
part of Phase 5; Phase 8 live acceptance remains separately blocked on
company-approved Moodle web-service configuration.
