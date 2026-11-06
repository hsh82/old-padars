# Development handoff

## Staging separation

Stage 1 is pinned at commit `81792d9` on branch `staging-1` in the original
Bench app checkout. `kara.loc` serves that checkout. User changes to AGENTS.md
and test_registration.py remain there and must not be discarded or committed
without review. Do not switch or edit that checkout for feature development.

Development continues on `codex/full-product` in
`/home/weinno/frappe/sites/kara.loc/workspace/padars-development`, visible as
`/workspace/padars-development` inside the existing trusted Frappe container.
Use command-local `PYTHONPATH=/workspace/padars-development` for explicitly
site-pinned development commands against `padars-phase12-fresh.local`; verify
`padars.__file__` before tests. The staging web process has no such override.
Do not run development tests against `kara.loc`. A separate runner was removed
after its network/grant restrictions prevented test access; no DB grants were
changed. Do not run a development asset build against the shared Bench assets
or restart staging services. Staging promotion is a separate action.

## Actual roadmap checkpoint

The canonical delivery goals and acceptance gates are in [ROADMAP.md](ROADMAP.md).
Unclosed checks are in [VERIFICATION_BACKLOG.md](VERIFICATION_BACKLOG.md).

Phases 4–7 have development handoffs and remain implemented. Phase 8 has a live
adapter, durable queue and roster lifecycle work, with live acceptance blocked
on authorized Moodle service configuration. Phase 9 includes scoped draft
entry, individual manager approval, safe draft-table rendering and manager
preview of approved Education results. See the phase reports for exact evidence.

Assessment schemes and immutable publication now have focused implementation:
eleven tests cover weights, approval, previews, publication versions, student
isolation and generated PDF. Controlled Education mark corrections are now also
implemented and focused-tested, preserving published snapshots and correction
audit metadata. Verified guardian delivery is now connected through native relationships,
manager verification/revocation actions and the published report portal. Twelve
focused tests cover account creation, isolation, explicit revocation and source
relationship changes. The `/school` student/family view now connects weekly sessions, courses and
official attendance; fourteen focused tests pass. Course links require matched
tenant mappings and observed enrollment, and use normal Moodle login.
Moodle grade discovery now runs through the existing queue with immutable,
scoped source snapshots and native review UI. Two focused database tests pass;
fourteen offline API contract tests pass, including tenant/course/user verification. Explicit manager-approved item mappings and audited Education draft imports
are now connected. Sixteen focused scheduling/assessment integration tests pass,
including mixed manual/Moodle marks, stale reviews, rollback, mapping retirement,
changed ranges and manager-controlled result corrections. No live grade read or
browser import is claimed. Teacher-published learning activities and per-child completion are now connected
through the durable queue and family portal. Seventeen focused tests and fifteen
offline adapter contracts pass; changed metadata is held for review. Session-specific asynchronous activity policies, immutable proposals, teacher
confirmation, cross-session consumption protection and reasoned manual correction
are now implemented; live analytics, browser/concurrency and release gates remain. Phase 8 live acceptance still needs an
authorized service/token/role configuration. Full Phase 9/10 and Phase 11 remain open.
Education remains authoritative; do not introduce fixed national formulas.
The remaining learning views and broader role portals, learning-activity and
PlugNmeet evidence integration, and Phase 11 release gates remain unfinished.
The approved twelve-domain list has not yet been supplied; the existing matrix
records that gap and must not be relabelled as a recovered twelve-domain list.

The objective remains completion of the approved product roadmap. An execution
or usage interruption must leave this checkpoint current. Automatic resumption
depends on an available session; do not promise an external usage reset.

## Packaging checkpoint

The wheel build and packaged-artifact guard pass; CI includes the guard.
A damaged-wheel negative check passed. A focused guardian-role installation
test passed after enforcing the portal-only app role in installation/migration
helpers. This is not fresh-site or Phase 11 acceptance. Next feature work is
Moodle activity discovery/completion and session-specific evidence; retain the
existing grade/publication and family-portal implementations.

## Latest feature checkpoint

Learning discovery and teacher checkbox publication are implemented; raw source
visibility is never equated with student access. Current family selections and
per-child statuses are scoped; API failures become unavailable and empty
publication removes activities. Live Moodle/PlugNmeet configuration remains an
external acceptance gate. Continue with session-specific evidence policies; do
not redo grade import, publication, guardian verification or academic portals.

## Current next task

The evidence milestone is verified: eighteen focused scheduling/assessment
tests, five daily-operation tests and the native form metadata harness pass.
Fresh installation on `padars-release-fresh.local` exposed and fixed action
permission fixture ordering. Native forced app reinstallation recovered the
partial install; repeated migration and all 26-DocType/fixture/index checks pass.
This adds a second disposable installation-only environment; routine academic
tests remain on `padars-phase12-fresh.local`. Student/Guardian navigation now
uses the role-filtered portal hook and passes a focused native-sidebar test.
Next: complete role experiences and independent release gates while awaiting
the approved live Moodle/PlugNmeet target configuration. Native new-form mandatory
checks now defer generated readonly values on new documents while server reqd
stays enforced. Narrow native academic-reference permissions allow manager
configuration without a broad Academics User or System Manager role. Continue
with verified PlugNmeet session analytics/combined policies only when its actual
configuration/contracts are available; do not infer live attendance from module
completion. The Stage 1 checkout remains protected.

Teacher overview is now implemented at `/teacher`, with native scoped schedules,
course links and roster counts. Shared course-launch checks support observed
Teacher and School Manager enrollment without exposing tokens. Two focused
teaching/link tests passed. Stable-identity rename/merge safeguards are now implemented and focused-tested
through Frappe's rename service. Next continue independent release checks and
role workflows while the approved live target/configuration question is pending.
Do not claim all phases or live Moodle/PlugNmeet acceptance complete.

## Staging 2 priority (2026-11-06)

User requested a separate working Staging 2 before further feature work. Twelve
native Role Profile presets now install repeatably without changing customized
profiles. Customer presets exclude System Manager and Academics User; only the
company administrator preset includes infrastructure privileges. Fixed-role
services preserve native multi-profile semantics and reject escalated profiles.
Managers receive native enrollment/assessment-plan submission without broad
roles. Existing Student Customer name/image projection is narrowly synchronized;
unauthorized Customer retargeting is rejected. Focused regressions pass.
Separate runtime deployment and role-login acceptance remain to be performed.
Stage 1 checkout, database, workers and assets must remain untouched.

Staging 2 preparation verification: all 23 focused scheduling/product tests pass
on `padars-phase12-fresh.local`, including default-profile repeatability, safe
role grants, manager permission boundaries and existing Customer projection.

Staging 2 installation now passes on its independent `stage2.kara.loc` site.
Synthetic academic seeding, native private intake upload/download and role HTTP
checks pass. User-profile landing pages are verified. The current-day assessment
comparison defect was traced to SQL date/timedelta versus incoming strings;
canonical date/time comparisons fix unchanged submissions without permitting
real past rescheduling. All 24 focused product tests pass. Final deployment
snapshot promotion and synthetic publication verification follow this commit.

## Staging 2 ready for manual testing (2026-11-06)

The installed product snapshot includes `fb8953c` (twelve default profiles) and
`76b7457` (assessment schedule fix and staging tooling), followed by the final
deployment-record commit. The local `staging-2` branch and independent clone
are pinned to that record. Open `http://stage2.kara.loc/login`; map the name to
the same server IP as `kara.loc` if needed. See [manual guide](STAGING_2_TEST_GUIDE.md)
and [deployment tooling](../../scripts/staging2/README.md). Credentials are in the
owner-only private file documented in the guide, outside Git.

Verified: genuine fresh Frappe/ERPNext/Education/Padars install with twelve
profiles; 26 DocType/fixture/index gate; all 24 focused product tests; real HTTP
manager/teacher/student/guardian login and role landing; academic lists; teacher
three-student roster; own timetable/attendance; native saved-parent private CSV
upload/download; unrelated attachment denial; private-file/student/guardian
isolation; real teacher mark entry, manager approval and three report-card
publications; scoped report pages and generated PDF; app JS assets; realtime
transport HTTP 200; one worker online and scheduler enabled. New seeds are
repeatable and preserve credentials/data. Runtime proxy now resolves changing
Docker upstream addresses instead of retaining a stale address after restart.

Not verified: interactive browser acceptance, execution of a new CSV/Excel
identity batch on this new site, SMS delivery, live Moodle/MuTMS/PlugNmeet or SSO,
performance/concurrency and final Phase 11 release acceptance. LMS/SMS remain
disabled; mocked or absent services are not reported as live. Follow the user’s
staging-test priority; collect feedback before another staging promotion. Keep
Stage 1's original branch/worktree, including new user edits, untouched.

## kara.loc promoted to Staging 2 at user request (2026-11-06)

Explicitly requested by the user after the independent Stage 2 acceptance.
Runtime Padars snapshot: `a0aa6e1`, cloned on `staging-2` in
`workspace/padars-staging2`. The original IDE checkout remains on `staging-1`
with all three uncommitted user files preserved. It is no longer the runtime
Padars source. The independent `stage2.kara.loc` deployment is unchanged.

Database/config/public/private files backed up before migration:
`workspace/frappe-bench/sites/kara.loc/private/backups/20261106_180209-kara_loc-*`.
Native `bench --site kara.loc migrate` passed with the new snapshot. Site-level
developer mode is 0. All twelve default Role Profiles are installed; existing
school records/users and integration configuration were not replaced by demo data.

Runtime overlay: `docker-compose.staging2.yml` mounts the pinned source read-only
at the normal app path in web, socketio, scheduler, workers and nginx. `.env`
sets COMPOSE_FILE to base + workers + staging2 overlay. For future restarts use
`docker compose -p karaloc up -d` from this directory. Tools explicitly supplying
only the base compose file omit this overlay and must be adjusted accordingly.

Verified: installed schema/fixtures/indexes (26 DocTypes), required profiles,
login HTTP 200, served Padars JS hash matches the pinned source, all Kara services
running. No synthetic seeding, authentication experiment or write test was run
against existing Kara school data. Existing credentials remain unchanged.
Use http://kara.loc/login and hard-refresh after the upgrade.
