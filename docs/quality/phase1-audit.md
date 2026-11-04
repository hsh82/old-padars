# Padars Phase 1 audit

Updated: 2026-11-04

## Evidence base

- Branch: `dev`.
- Frontend milestone: `bf69029`.
- Backend checkpoint: `40b7a74`.
- Frappe source: 16.52.0 in the checked-out Bench.
- Education source: 16.0.1 (`education/__init__.py`).
- The development site configuration lists Frappe, ERPNext, HRMS, Airplane Mode, Draw, and Education; Padars is not installed on `kara.loc`.
- Junior School was inspected independently at `3567e3f11c1ac553929f9bd3b111c306fe689d60` and was not installed or copied.

## Implementation inventory

| Area | Classification | Evidence and limitation |
| --- | --- | --- |
| School, membership, academic-year links | Implemented but untested in a live site | Padars DocTypes, validation, school context API, and Desk forms exist; migration and database tests are blocked. |
| School isolation for Padars records | Implemented but untested | Permission query and direct permission hooks exist; two-school negative tests require a working Frappe site. |
| School isolation for Education records | Implemented but untested | Program Enrollment, Student Group, Course Enrollment, Student, Instructor, schedule, assessment, and attendance hooks were added; runtime metadata/permission behavior is unverified. |
| Individual Student identity reuse | Partially implemented | Education creates/links Users; Padars rejects duplicate Student/User identity and adds a provisioning action. A complete registration wizard is not present. |
| Returning-student enrollment | Partially implemented | Education Program Enrollment remains authoritative and Padars validates school membership; no dedicated returning-student workflow or browser test exists. |
| Bulk Student import | Missing | No Padars import API, bounded batch policy, preview page, result model, or retry UI exists. |
| Student Group and instructor assignment | Partially implemented | Education Student Group is extended with school/year checks and instructor membership checks; browser and database tests are blocked. |
| Course Offering | Implemented in code, untested end-to-end | Padars model, relationship validation, form, sync actions, and duplicate checks exist. |
| Tenant provisioning | Implemented for the deterministic mock adapter | School action, operation state, mapping, retry limit, and stale-worker recovery exist; live MuTMS tenant contract is unavailable. |
| Moodle user provisioning | Implemented for the deterministic mock adapter | Student action and User mapping operation exist; no live API, account policy, or SSO contract is available. |
| Moodle course provisioning | Implemented for the deterministic mock adapter | Course, tenant, mapping, idempotency, failure, retry, and operation monitor exist; live API and course navigation are unavailable. |
| Moodle enrollment reconciliation | Implemented for the deterministic mock adapter | LMS Enrollment State validation and mock sync operation exist; no live role/enrollment API is verified. |
| Assessment entry | Reused and partially extended | Education grading remains authoritative; Padars validates optional Course Offering context. |
| Report-card approval/publication/versioning | Missing | No Report Card Publication DocType or approved publication service exists. |
| Student portal course/result access | Missing | No Padars portal/API or SSO navigation contract exists. |
| Failure and recovery | Partially implemented | Mock failures, retry state, safe errors, retry limits, and stale worker recovery are implemented; live timeout, credential, and worker tests are blocked. |
| Persian RTL/Jalali presentation | Implemented but untested | New strings are translation-ready and use Frappe date formatting; no browser/locale test was available. |

## Architecture findings

1. Education remains the source of truth for Student, Program Enrollment, Student Group, Course Enrollment, Instructor, schedules, and assessments.
2. Padars owns school tenancy, school membership, Course Offering identity, LMS mappings, enrollment state, and sync operations.
3. Padars does not modify Frappe, ERPNext, Education, Moodle, or Junior School source.
4. Frontend filters are usability aids only. Server-side permission query conditions, direct permission hooks, and validation now cover the school boundary for the supported Education records.
5. The live adapter is intentionally not claimed complete because the MuTMS tenant/category, user, enrollment, and SSO contracts were not available.

## Release blockers

- A working Frappe/MariaDB site is required for migrations, permission tests, DocType tests, and browser smoke tests.
- Bulk registration, report publication/versioning, student portal access, and SSO are not implemented contracts.
- Live MuTMS verification is unavailable; only the deterministic mock adapter is testable locally.
