# Phase 10 progress

Phase 10 is in progress on `codex/full-product`; Stage 1 is unchanged.

Verified Guardian Access reuses Education Guardian.user and Student Guardian
rows. School Managers verify or revoke one relationship with an audit reason.
A matching new account receives only the portal-only Padars Guardian role as a Website User;
existing accounts use the fixed role extension. No general User administration
permission is granted. Parents use standard password reset; no invite is sent.

Published report lists, reads and PDF delivery revalidate grants and native
links. The report portal displays only verified linked children. Native source
changes revoke incompatible grants, and old decisions remain auditable.
Unverified guardians cannot access reports, draft grades or teacher comments.

Twelve focused scheduling/assessment integration tests passed on
`padars-phase12-fresh.local`; they cover weighted grades, publication and PDF,
guardian verification, limited account creation, unrelated-child denial,
explicit revocation and automatic revocation. JavaScript syntax and Python/JSON
checks passed. No browser journey or full app suite was run for this milestone.

Next: connect student/guardian timetable, attendance and course views, then
learning data when actual Moodle service capabilities are available. Full
Phase 10 and release acceptance remain unfinished.

The `/school` portal now connects weekly Education sessions, course/teacher
names and submitted attendance to Students and verified guardians. Active
roster/program-year enrollment scope controls sessions; withdrawn students
retain attendance history. Week navigation and published-report links are
connected. Only the Student receives a Moodle course link after local tenant,
user/course and observed-enrollment checks. SSO and learning deadlines remain
explicitly unavailable. Fourteen focused tests passed, including projection
scope, withdrawal, escaped HTML and course-link contracts. Browser and live
service acceptance remain open.
