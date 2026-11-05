# Stage 1 authorization matrix

> **Historical implementation record.** This matrix describes shared-site
> Stage 1 checks, not the product target. The target is one site per school;
> staff still need scoped permissions within that site. See
> [ADR-005](../decisions/ADR-005-site-per-school.md).

Updated: 2026-11-04. This is the enforced Stage 1 baseline for the provisional
shared-site topology. A Frappe role and an active, date-valid School Membership
are both required; neither is sufficient alone.

| Actor | Required Frappe role | Required School Membership | Stage 1 authority |
| --- | --- | --- | --- |
| Platform Administrator | `Padars Platform Administrator` or `System Manager` | None | Cross-school configuration, recovery, tenant provisioning. `Administrator` and `System Manager` remain the tested recovery route. |
| School Manager | `Padars School Manager` | `School Administrator` | Manage records and sync requests for the named school only. Cannot create Moodle tenants. |
| Academic Staff | `Padars Academic Staff` | `Academic Staff` (with Instructor) | Manage local academic records for the named school. Cannot manage memberships or request tenant/sync operations. |
| Teacher | `Padars Teacher` and `Instructor` | `Teacher`, with matching User and Instructor | Read only their assigned groups, offerings, students, schedules, and attendance. Grade/attendance writes stay closed until the reviewed WP04+ services exist. |
| Student | `Student` | `Student` | Read only own Student, enrollment, result, attendance, and assigned-group schedule data. |
| Guardian | None supported in Phase 1 | `Guardian` does not grant access | Deny by default; no Guardian portal is exposed. |

## Enforcement points

- `permission_query_conditions` controls Desk lists and reports.
- `has_permission` controls direct documents, REST/RPC document reads and
  writes, and denies records without a resolvable school.
- Padars validators require school context and cross-school relationship
  consistency for Education records.
- Overrides protect Education RPC methods that were found to bypass document
  permissions. Generic roster, applicant enrollment, bulk attendance write,
  and report-card preview endpoints fail closed until their school-aware
  workflows are implemented.
- APIs that create or retry Moodle work require a School Manager; tenant
  provisioning requires a Platform Administrator.

## Shared-site decision

Shared-site tenancy remains provisional. It minimizes operational overhead but
requires every document, list, report, attachment, API, and background job to
prove school isolation. Site-per-school materially reduces blast radius but
adds provisioning, upgrades, cross-site administration, and tenant-mapping
complexity. Do not approve a pilot until the remaining file/report/job negative
tests have passed against a representative staging environment.

## Deferred decisions required before WP04–WP09

1. Student identity when no email is available: approved identifier,
   activation/recovery, consent, and no-password policy.
2. MuTMS multi-school identity: one Moodle user allocated to multiple tenants
   versus isolated remote identities, confirmed with a sandbox contract.
3. SSO: issuer, redirect/callback, session lifetime, logout, and tenant claim.
4. Iranian grading: approved rules by school/stage; no legal calculation is
   implemented or implied.
5. Report-card approval/correction: approvers, publication lock, immutable
   snapshot, and correction/audit policy.
