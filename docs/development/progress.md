# Implementation progress

Updated: 2026-11-04

## Implemented

- Stage 1 WP01–WP03 authorization hardening started on branch `codex/stage1-tenancy-security`; `kara.loc` remains untouched.
- Added explicit Platform Administrator, School Manager, Academic Staff, Teacher, Student, and denied-by-default Guardian authorization matrix.
- Replaced broad school membership permissions with actor-aware direct/list guards and protected exposed Education RPC methods through Frappe overrides.
- Added school-context Custom Fields for schedules, assessments, and attendance; role synchronization and duplicate-safe constraints/indexes are delivered through post-model-sync patches.
- Created and migrated disposable `stage1.local`; the first fixture migration failure was fixed and the second migration completed successfully.

- Repository audit and version/source review completed.
- `AGENTS.md` and three repository skills added.
- Architecture, product, decision, setup, testing, and progress documentation added.
- Padars-owned School, School Membership, School Course Offering, LMS Settings, LMS Entity Mapping, LMS Enrollment State, and LMS Sync Operation DocTypes added.
- Education extension fixtures prepared for school and course-offering context.
- Mock Moodle adapter and course-offering sync service added with idempotency, mapping, retry, and failure persistence.
- Focused tests added for DocType validation, direct school-permission conditions, idempotent mock provisioning, failure recording, and retry-to-success behavior.
- CI updated to install ERPNext and Education before Padars on clean test sites.
- Junior School frontend audit completed at commit `3567e3f11c1ac553929f9bd3b111c306fe689d60`; AGPL source was used only as a reference.
- Frontend assets added for school-aware Education forms, Course Offering synchronization actions, and the LMS Synchronization Monitor page.
- Frontend JavaScript syntax checks and two dependency-free shared-helper smoke tests pass.
- Phase 1 audit, defect register, test results, and release-readiness assessment added under `docs/quality/`.
- School isolation was extended to supported Education records; Student identity reuse, mock tenant/user/enrollment operations, retry limits, and stale-worker recovery were added.

## Verified

- Local source audit confirmed Education's existing Student, Program Enrollment, Course Enrollment, Student Group, Instructor, Assessment Plan, and Assessment Result behavior.
- Frappe 16.52.0 imports under the checked-out Python 3.14 runtime when its site-packages are explicitly supplied.
- `git status` was clean before implementation.
- JSON parsing, Python compilation, module imports, deterministic mock-adapter contract, and `git diff --check` passed.

## Blocked

- The full Frappe test runner is currently blocked before Padars tests by an existing duplicate ERPNext fixture on disposable `stage1.local`; the new Stage 1 negative suite remains unexecuted until that isolated fixture state is repaired.

- Database-backed Frappe tests and migration are not yet executed: the Bench virtualenv wrappers point to `/workspace/frappe-bench`, and the host cannot load `libmariadb.so.3`; the configured DB hostname is also environment-specific.
- Ruff is not installed in the available runtime, so the configured lint command was not executed.
- Browser behavior, asset build, and database-backed frontend tests remain unexecuted because the local Bench runtime/site is unavailable; the focused Node smoke tests are passing.
- Padars is not installed on `kara.loc`; no schema or data was changed there.
- Live Moodle/MuTMS API, tenant/category mapping, and SSO contract are not available, so only the mock adapter is implemented.
- Phase 1 release assessment is `NOT READY`: bulk registration, report-card publication/versioning, student portal access, SSO, and live MuTMS verification remain incomplete.
- Canonical Phase 1 roadmap located at `docs/input/Padars_Phase1_Requirements_and_MVP_Plan.md`; the 39 committed IDs are traced in `docs/releases/phase1-requirements-matrix.md`.
- Deployment discovery found only the development site `kara.loc`; no named staging site or running Frappe web/worker service was verified. No migration, backup, install, restart, or deployment command was run.

## Next milestone

Repair or recreate the disposable fixture state, run the Stage 1 two-school negative suite and relevant existing tests, then stop for approval before WP04.

