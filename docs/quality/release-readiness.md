# Phase 1 release readiness

Updated: 2026-11-04

## Assessment

**NOT READY**

The code contains a coherent mock-backed vertical slice and strengthened school isolation, but essential acceptance workflows remain unimplemented or unverified. The local environment cannot run migrations, Frappe tests, browser tests, or live MuTMS verification.

The canonical 39-ID traceability and deployment-specific decision are maintained in `docs/releases/phase1-requirements-matrix.md` and `docs/releases/phase1-release-readiness.md`.

## Acceptance checklist

### Academic core

- [ ] School configuration verified on a running site.
- [ ] Individual student registration verified end-to-end.
- [ ] Returning-student workflow implemented and verified.
- [ ] Bulk registration implemented.
- [ ] User provisioning verified against the target policy.
- [ ] Academic year and Program relationships verified in the database.
- [ ] Student Groups verified with two-school data.
- [ ] Instructor assignments verified with two-school data.
- [ ] Course Offerings verified in browser and database tests.

### Moodle integration

- [ ] Tenant mapping verified against MuTMS.
- [ ] Moodle user mapping verified against MuTMS.
- [ ] Course creation verified against MuTMS.
- [ ] Teacher enrollment verified against MuTMS.
- [ ] Student enrollment verified against MuTMS.
- [x] Mock synchronization states, idempotency, failure, and retry are implemented in code.
- [x] Retry limit and stale-worker recovery are implemented in code.
- [ ] SSO flow verified in the target environment.

### Assessment

- [ ] Grade entry verified on a running Education site.
- [ ] Configured grade rules verified.
- [ ] First-term report cards implemented and verified.
- [ ] Second-term report cards implemented and verified.
- [ ] Annual report cards implemented and verified.
- [ ] Published results protected and versioned.
- [ ] Students can access only authorized results.

### Engineering

- [ ] No critical security issue proven by executed two-school tests.
- [ ] No critical data-integrity issue proven by database tests.
- [ ] Clean installation and migration pass.
- [ ] Full automated Frappe tests pass.
- [ ] Critical browser flows pass.
- [ ] Cross-school isolation is verified with direct reads and APIs.
- [x] Mock integration failures are recoverable in code.
- [ ] Deployment instructions validated in the target runtime.
- [x] Documentation reflects implemented and blocked behavior.

## Pilot prerequisites

1. Repair or provide an isolated Frappe/MariaDB runtime and install Padars.
2. Execute the existing Frappe tests with a two-school dataset and fix any metadata/permission incompatibilities.
3. Define and implement bulk registration and report-card publication contracts.
4. Confirm the live MuTMS tenant/user/course/enrollment and SSO APIs, then implement and test the live adapter.
