# Moodle instructional grade discovery

The existing LMS Sync Operation queue now supports `Read Grades` for a School
Course Offering. A School Manager requests it from the offering; an in-flight
request is reused. Enqueue runs after commit. Existing retries, bounded attempts,
backoff, monitoring and school-disabled checks apply. It does not provision
remote entities or write grades to either system.

The installed Moodle 5.2 source at
`public/grade/report/user/classes/external/user.php` was read for the actual
`gradereport_user_get_grade_items(courseid, userid)` contract and optional raw,
range, visibility, override, scale and stale flags. Public reference:
[Moodle external grade report API](https://phpdoc.moodledev.io/main/d7/da7/classgradereport__user_1_1external_1_1user.html).
The installed source, followed by the configured service's own API docs, is the
version-specific authority; no live capability is inferred from the reference.

Each capture requires a matching primary school, active roster of 1–200 students,
submitted program/year enrollment, enabled user and desired/observed Moodle
student enrollment. Tenant, offering and user mappings must share one context.
The real adapter verifies installation origin, tenant fingerprint/category,
remote course category, remote user tenancy and returned course/user IDs before
accepting a report. One user's report is requested at a time, never user=0.

Immutable Moodle Grade Snapshot stores operation/student identity, observed
time, remote IDs/context and a digest of whitelisted instructional items. Names
are stripped of HTML and displayed as text. Feedback, names of other Moodle
users, external identity numbers and full raw responses are not persisted.
Missing grades stay null; non-finite numbers and duplicate IDs are rejected.
Hidden/stale grades are unavailable, scales/outcomes unsupported, invalid
ranges conflicting and overridden grades require review. Zero remains zero.
All source calls complete before atomic snapshot persistence. Operation/student
keys make retries safe. No snapshot is created on a failed remote fetch.

Managers and assigned teaching/grade staff can inspect source snapshots through
permission-aware lists and the native form's grade table. Students, guardians,
unassigned staff, public Files and DocShares cannot obtain them. Published
reports remain a separate immutable workflow. Mapping, normalization and explicit draft import are now connected through
[reviewed grade import](moodle-grade-import.md). Discovery alone never approves
an official result.

Two focused database tests cover after-commit enqueue, request deduplication,
retry idempotency, scoped reads, immutable sources, remote failure, metadata
minimization and grade-status handling. Adapter contract tests separately cover
cross-category/user denial. Live service activation, browser review and full
Phase 9 acceptance remain blocked/unperformed.
