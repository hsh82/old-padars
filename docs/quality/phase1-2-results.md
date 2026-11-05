# Phase 1–2 implementation and verification

Date: 2026-11-05. Branch: `codex/phase1-2-school-onboarding`.

The implementation establishes one active School per site, academic
assignments and action-specific access, and a restartable school setup page
with a Padars Workspace and native record-based onboarding steps. See the
[model](../architecture/doctype-specification.md) and
[permission boundaries](../architecture/permissions.md).

## Evidence

- A new disposable site `padars-phase12-fresh.local` installed Frappe,
  ERPNext, Education and Padars successfully from scratch, including permission
  fixtures and post-sync initialization.
- On that site, `bench --site padars-phase12-fresh.local run-tests --app padars
  --lightmode` ran 35 tests successfully, with 6 obsolete shared-site tests
  skipped. Coverage includes scoped list and direct access, student identity,
  grade and attendance actions, sensitive data, role separation, attachments,
  sharing, setup, onboarding records and mock Moodle idempotency.
- Two frontend helper tests, setup-page JavaScript syntax, Python and JSON
  parsing, and `git diff --check` passed.
- The standard runner without `--lightmode` previously failed in ERPNext test
  data preload before reaching Padars tests because `All Item Groups` was
  missing. Light mode bypasses that preload; it does not establish that the
  standard runner is fixed.

## Limits and follow-up

- This is a clean-install path; migration from old experimental Padars data is
  not supported by this work. No production site was migrated or deployed.
- The setup page and Workspace were not exercised in a browser. Native
  onboarding may hide optional cards after required steps are complete; the
  Workspace shortcuts remain available.
- Selected unreviewed Education RPCs and academic reports are disabled pending
  scoped replacements. Guardian access and result approval/publication are
  deliberately unavailable. Additional upstream endpoints and reports still
  need security review before claiming complete coverage.
- Moodle operations use the mock adapter. Live Moodle/MuTMS configuration,
  web-service capabilities and SSO are not verified.
- Scope expansion currently reads matching groups and offerings into memory;
  assess query performance with realistic school data.
- Upstream repositories were not edited; Education already had a modified
  `education/public/node_modules` entry before this work.
