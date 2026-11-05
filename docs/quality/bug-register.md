# Phase 1 defect register

Updated: 2026-11-04

## Fixed

| ID | Severity | Defect | Fix |
| --- | --- | --- | --- |
| PAD-014 | Blocker | A Student or Teacher with ordinary Education roles could list/read other pupils' records in the same school because the earlier hook treated any membership as broad school access. | Replaced it with actor-aware, fail-closed list and direct-document checks; student own-record and teacher assigned-group rules have regression coverage. |
| PAD-015 | Blocker | Education roster, attendance, applicant-enrollment, and report-card RPC endpoints accepted caller-controlled identifiers or used unscoped queries. | Added narrow `override_whitelisted_methods`: scoped roster/attendance reads require authorized groups; unsafe generic and write/report paths fail closed pending reviewed services. |
| PAD-016 | High | Custom Field fixture could not migrate because records lacked required fixture names. | Added deterministic names; migration was rerun successfully on `stage1.local`. |
| PAD-017 | High | Required school context fields, scoped roles, and supporting database constraints were not synchronized or guarded by migration checks. | Added named fixtures, role patch/install hook, duplicate preflight, unique constraints, and lookup indexes; validated on the disposable site. |

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
| PAD-012 | Blocker | No named non-production staging site or verified Frappe deployment service was discovered. | Provision/identify an isolated staging site and document its authorized deployment owner before running migrations or backups. |
| PAD-013 | Medium | Checked-out Education repository is tagged `v16.1.0` but its `__version__` string reports `16.0.1`. | Resolve the upstream/package metadata discrepancy in the pinned build, without editing upstream source in Padars. |
| PAD-018 | Blocker | On the Phase 0 clean site, ERPNext `BootStrapTestData.make_item_group()` fails because `All Item Groups` is absent, preventing full and focused Frappe runs from reaching Padars tests. Earlier `stage1.local` runs also encountered a duplicate ERPNext test fixture. | Keep as an upstream test-environment blocker; do not mark Padars tests passed. Revisit if it prevents Phase 1 acceptance, without changing production data. |
