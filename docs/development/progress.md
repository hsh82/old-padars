# Implementation progress

> Phase 0 established a fresh baseline on 2026-11-05. For the accepted product
> topology and current source/runtime pins, see [ADR-005](../decisions/ADR-005-site-per-school.md),
> [target architecture](../architecture/target-system.md), and
> [Phase 0 results](../quality/phase0-results.md). This progress log retains
> earlier shared-site work as implementation history.

Updated: 2026-11-05

## Phase 3 implementation handoff

Phase 3 implementation is complete. Development handoff is accepted; integration
and production release verification remain pending. The status matrix and
backlog are in [Phase 3 results](../quality/phase3-progress.md). See also
[student registration](../architecture/student-registration.md).

## Current Phase 1–2 work

Site-per-school setup, scoped academic assignments and permissions, a school
setup page, Workspace and onboarding records are implemented. The current
verification and limitations are in [Phase 1–2 results](../quality/phase1-2-results.md).
The sections below record earlier work and do not supersede that evidence.

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

## Verification limits

- The clean-site Frappe test runner stopped in ERPNext preloading before any
  Padars test ran: `BootStrapTestData.make_item_group()` could not find the
  `All Item Groups` parent. Earlier `stage1.local` runs also hit a duplicate
  ERPNext fixture. See [Phase 0 results](../quality/phase0-results.md).
- Historical Padars schema migration tests were skipped because the app is
  pre-release and the baseline is a fresh install.
- Browser behavior and asset build were outside Phase 0; the local Bench runtime
  is available through the Frappe container.
- The current `kara.loc` site config lists Padars as installed; no Phase 0
  command targeted it.
- Moodle/MuTMS code versions are recorded, but live web-service functions,
  tenant/category mapping, service-account capabilities, and SSO remain
  unverified. The adapter remains mock-only.
- Phase 1 release assessment remains `NOT READY`: bulk registration,
  report-card publication/versioning, student portal access, SSO, and live
  MuTMS verification remain incomplete.
- The 39 Phase 1 requirement IDs are traced in
  `docs/releases/phase1-requirements-matrix.md`.
- Phase 0 created a temporary backup during initial inspection and removed it
  after the scope was narrowed; no migration, restart, or deployment command
  was run.

## Next milestone

Phase 4 Curriculum Adoption and Offerings is approved and is the next milestone.
Historical schema migration compatibility remains outside the pre-release
clean-site scope.

