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
browser import is claimed. Next: learning-activity discovery/completion and
session-specific attendance evidence; Phase 8 live acceptance still needs an
authorized service/token/role configuration. Full Phase 9/10 and Phase 11 remain open.
Education remains authoritative; do not introduce fixed national formulas.
The remaining learning views and broader role portals, learning-activity and
PlugNmeet evidence integration, and Phase 11 release gates remain unfinished.
The approved twelve-domain list has not yet been supplied; the existing matrix
records that gap and must not be relabelled as a recovered twelve-domain list.

The objective remains completion of the approved product roadmap. An execution
or usage interruption must leave this checkpoint current. Automatic resumption
depends on an available session; do not promise an external usage reset.
