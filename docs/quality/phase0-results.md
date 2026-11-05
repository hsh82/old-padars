# Phase 0 results

Date: 2026-11-05. Branch: `codex/stage1-tenancy-security`.

## Completed

- Verified Frappe 16.52.0, ERPNext 16.51.1, Education source commit
  `93bc7075753369457919720690f80c6d2207b5f2`, and Padars commit
  `e254e187357fcf5636a6de3208f1606676c8fcfa`.
- Created `padars-phase0-fresh.local` in the local Frappe container.
- Installed ERPNext, Education, and Padars successfully after Frappe.
- `bench --site padars-phase0-fresh.local list-apps` confirms all four apps.
- Confirmed the app is still pre-release and may redesign its experimental
  schemas and patches without historical data migration guarantees.
- Recorded Moodle 5.2.4 and MuTMS plugin v5.2.4.01 from the running local code.
- Corrected CI to use the same source commits and runtime versions.
- Recorded that `kara.loc` has Padars listed as installed; no operation in this
  phase targeted or changed that site.

## Not run by design

- No migration or patch compatibility tests against previous Padars schemas.
- No restore exercise; it is not needed to establish the clean pre-release
  development baseline. A temporary backup was created during initial
  discovery and removed after you narrowed Phase 0 to clean install and pins.
- No live Moodle request, token inspection, or external write.
- No production or staging deployment.

## Test result

`bench --site padars-phase0-fresh.local run-tests --app padars` and a focused
Moodle service test both stopped during ERPNext test preloading, before any
Padars test executed. ERPNext's `BootStrapTestData.make_item_group()` fails
because `All Item Groups` is missing. No Padars test is marked as passed from
these attempts. This is an upstream test-fixture setup issue; schema migration
compatibility is not involved.

## Remaining verification

- Verify the enabled Moodle web-service function list and tenant configuration
  before Phase 8 remote writes.
- Revisit the upstream test-preloader blocker if it prevents Phase 1 acceptance.

Phase 1 can proceed against the clean site; migration from experimental Padars
schemas is not required.

See [version baseline](../operations/version-baseline.md) and
[Phase 0 plan](../plans/phase-00.md).
