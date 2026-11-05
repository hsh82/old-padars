# Moodle integration

The integration boundary is `padars.integrations.moodle`.

- `MoodleAdapter`: narrow interface for tenant, user, course, and enrollment reconciliation.
- `MockMoodleAdapter`: deterministic local adapter used for tests and the first vertical slice.
- Tenant, user, course, and enrollment requests create or reuse persistent `LMS Sync Operation` records, enqueue after commit, and process with idempotent mappings.
- `LMS Entity Mapping`: preserves local/remote identifiers and remote context.
- `LMS Sync Operation`: records pending, running, succeeded, and failed states with attempts and safe diagnostics.

The local Moodle code tree is Moodle 5.2.4 (Build 20261005) with MuTMS
`tool_mutenancy` v5.2.4.01; exact source metadata is in the
[version baseline](../operations/version-baseline.md). This confirms the local
code version only. The live site's enabled API functions, service-account
capabilities, tenant allocation rules, category/cohort IDs, role/enrollment
semantics, and SSO contract remain unverified. No live API success is claimed.
Credentials remain in a Frappe Password field and are not returned by APIs.
Mock operations have bounded retries and stale-worker recovery.

