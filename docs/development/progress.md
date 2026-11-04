# Implementation progress

Updated: 2026-11-04

## Implemented

- Repository audit and version/source review completed.
- `AGENTS.md` and three repository skills added.
- Architecture, product, decision, setup, testing, and progress documentation added.
- Padars-owned School, School Membership, School Course Offering, LMS Settings, LMS Entity Mapping, LMS Enrollment State, and LMS Sync Operation DocTypes added.
- Education extension fixtures prepared for school and course-offering context.
- Mock Moodle adapter and course-offering sync service added with idempotency, mapping, retry, and failure persistence.
- Focused tests added for DocType validation, direct school-permission conditions, idempotent mock provisioning, failure recording, and retry-to-success behavior.
- CI updated to install ERPNext and Education before Padars on clean test sites.

## Verified

- Local source audit confirmed Education's existing Student, Program Enrollment, Course Enrollment, Student Group, Instructor, Assessment Plan, and Assessment Result behavior.
- Frappe 16.52.0 imports under the checked-out Python 3.14 runtime when its site-packages are explicitly supplied.
- `git status` was clean before implementation.
- JSON parsing, Python compilation, module imports, deterministic mock-adapter contract, and `git diff --check` passed.

## Blocked

- Database-backed Frappe tests and migration are not yet executed: the Bench virtualenv wrappers point to `/workspace/frappe-bench`, and the host cannot load `libmariadb.so.3`; the configured DB hostname is also environment-specific.
- Ruff is not installed in the available runtime, so the configured lint command was not executed.
- Padars is not installed on `kara.loc`; no schema or data was changed there.
- Live Moodle/MuTMS API, tenant/category mapping, and SSO contract are not available, so only the mock adapter is implemented.

## Next milestone

Install Padars on an isolated disposable site with a working Frappe/MariaDB runtime, run migrations and `bench --site <site> run-tests --app padars`, then add the student/teacher provisioning vertical slice.

