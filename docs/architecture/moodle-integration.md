# Moodle integration

The integration boundary is `padars.integrations.moodle`.

- `MoodleAdapter`: narrow interface for tenant, user, course, and enrollment reconciliation.
- `MockMoodleAdapter`: deterministic local adapter used for tests and the first vertical slice.
- Tenant, user, course, and enrollment requests create or reuse persistent `LMS Sync Operation` records, enqueue after commit, and process with idempotent mappings.
- `LMS Entity Mapping`: preserves local/remote identifiers and remote context.
- `LMS Sync Operation`: records pending, running, succeeded, and failed states with attempts and safe diagnostics.

The configured real Moodle/MuTMS API, tenant allocation rules, category semantics, role/enrollment semantics, and SSO contract are unresolved. No live success is claimed. Credentials remain in a Frappe Password field and are not returned by APIs. Mock operations have a bounded retry policy and stale-worker recovery.

