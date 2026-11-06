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

Phases 4–7 have development handoffs and remain implemented. Phase 8 has a live
adapter, durable queue and roster lifecycle work, with live acceptance blocked
on authorized Moodle service configuration. Phase 9 includes scoped draft
entry, individual manager approval, safe draft-table rendering and manager
preview of approved Education results. See the phase reports for exact evidence.

The next unfinished product workflow is configurable assessment/report-card
calculation and immutable publication/correction, together with Moodle grade
mapping and reconciliation. Education remains authoritative; do not introduce
fixed national formulas. Student/guardian portals, learning-activity and
PlugNmeet evidence integration, and Phase 11 release gates remain unfinished.
The approved twelve-domain list has not yet been supplied; the existing matrix
records that gap and must not be relabelled as a recovered twelve-domain list.

The objective remains completion of the approved product roadmap. An execution
or usage interruption must leave this checkpoint current. Automatic resumption
depends on an available session; do not promise an external usage reset.
