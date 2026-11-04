# Moodle integration

The integration boundary is `padars.integrations.moodle`.

- `MoodleAdapter`: narrow interface for remote course creation and future user/enrollment operations.
- `MockMoodleAdapter`: deterministic local adapter used for tests and the first vertical slice.
- `provision_course_offering`: creates or reuses a persistent `LMS Sync Operation`, enqueues after commit, and processes the operation with idempotent mapping.
- `LMS Entity Mapping`: preserves local/remote identifiers and remote context.
- `LMS Sync Operation`: records pending, running, succeeded, and failed states with attempts and safe diagnostics.

The configured real Moodle/MuTMS API, tenant allocation rules, category semantics, and SSO contract are unresolved. No live success is claimed. Credentials remain in a Frappe Password field and are not returned by APIs.

