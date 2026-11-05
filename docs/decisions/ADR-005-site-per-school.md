# ADR-005: One Frappe site per independent school

## Status

Accepted for the target product architecture on 2026-11-05. Supersedes the
provisional shared-site decision in ADR-001.

## Context

Padars is a Frappe Education extension for one school team per deployed site.
Independent schools receive separate Frappe sites and databases. A shared
Bench may host multiple sites. Each Padars site is associated with one primary
MuTMS tenant.

## Decision

- Treat the Frappe site/database as the independent-school boundary.
- Keep Padars responsible for site-level school configuration, external LMS
  state, and extensions Education does not own.
- Reuse Education's academic records and lifecycle.
- Treat grade, stream, campus, department, and class section as internal school
  structures, not customer tenants.
- Keep the existing `School` DocType during the transition. Decide whether it
  remains the canonical profile or becomes a Single DocType only after the
  model review in Phase 1.
- Do not use `School Membership` as a cross-customer security boundary. Decide
  whether it is retained as staff affiliation or retired in Phase 1.
- Rework schema and patches freely while Padars is pre-release. The clean
  install on the pinned Frappe/Education branch is the baseline; backward
  migration from experimental Padars schemas is not a release requirement.

## Consequences

- Site-level separation reduces cross-customer access risk.
- Staff still need role and academic-resource scopes within their school's
  site.
- Student, teacher, guardian, and school records remain subject to ordinary
  Frappe permissions and scoped workflow checks.
- Shared users across different school sites require an identity and SSO
  design; they are not represented by cross-site `School Membership` rows.
- Each site has independent backup, upgrade, and Moodle tenant mapping.
- Current shared-site hooks and docs are transitional implementation, not the
  target model. Phase 1 will replace or remove them with tests.

## Verification

The clean-install baseline is recorded in
[`../operations/version-baseline.md`](../operations/version-baseline.md).
