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
