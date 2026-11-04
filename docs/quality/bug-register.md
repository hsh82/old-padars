# Phase 1 defect register

Updated: 2026-11-04

## Fixed

| ID | Severity | Defect | Fix |
| --- | --- | --- | --- |
| PAD-001 | High | Education Program Enrollment and Student Group records were not included in Padars school query conditions. | Added school-aware permission query and direct permission hooks, with safe handling for optional fixture fields. |
| PAD-002 | High | A mapping could identify one School while pointing at an unrelated local record or arbitrary DocType. | Restricted local mapping types and validate the local record's school context. |
| PAD-003 | High | LMS Enrollment State validated only the Course Offering school, not the enrolled User or role. | Require active school membership and role-compatible Student/Instructor identity. |
| PAD-004 | Medium | Inactive memberships were treated as duplicate active memberships, and validity dates were ignored by access checks. | Validate only active duplicates and honor `valid_from`/`valid_to`. |
| PAD-005 | High | LMS Sync Operation advertised tenant/user/enrollment operations while the service only handled courses. | Connected those operation types to the deterministic mock adapter and validate operation/target pairs. |
| PAD-006 | Medium | A worker interruption could leave an operation permanently `Running`. | Added hourly stale-operation recovery and an explicit retry limit. |
| PAD-007 | Medium | Student creation could leave duplicate Student/User identities when an email already belonged to a User or Student. | Added server-side Student identity validation and reuse of an existing matching User. |

## Open

| ID | Severity | Defect or gap | Required next action |
| --- | --- | --- | --- |
| PAD-008 | Blocker | No bulk registration backend or UI. | Define bounded import/partial-success contract and implement it using Frappe's supported import facilities. |
| PAD-009 | Blocker | No report-card publication/versioning service. | Approve publication model and workflow before adding student-facing controls. |
| PAD-010 | High | Live MuTMS adapter and SSO contract are unavailable. | Confirm tenant, category, user, role, enrollment, and SSO API contracts in a sandbox. |
| PAD-011 | High | Database-backed multi-school and browser tests cannot run locally. | Repair the Bench Python/MariaDB runtime and run the isolated-site test plan. |
