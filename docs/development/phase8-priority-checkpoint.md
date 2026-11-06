# Development checkpoint: temporary Phase 8 priority

Date: 2026-11-05. Phase 8 is the active priority under the temporary Moodle
integration instruction. This reorders work; it does not cancel any roadmap
phase.

## Exact checkpoint before Phase 8

- Branch: `codex/phase1-2-school-onboarding`.
- HEAD: `19b0a20` — Curriculum Adoption and Offerings.
- Phase 3: implementation-complete handoff at `8d6134c`; browser and wider
  acceptance checks remain in the Phase 11 backlog.
- Phase 4: implementation-complete and committed at `19b0a20`; the focused
  curriculum and Course Offering tests passed on the disposable site.
- Phase 5: in progress and uncommitted. The working tree contains Instructor
  User/qualification work, teacher and specialized staff assignment workflows,
  scoped role/action permission setup, a workload report, UI changes, and a
  focused test module. Its schema migration completed on
  `padars-phase12-fresh.local`. The latest focused run reported 3 passed and 2
  failed tests; those failures have not been diagnosed to completion. Resume
  this exact working tree after Phase 8 without discarding or restaging its
  changes as Phase 8.
- Phase 6 and Phase 7: not started.
- User-owned unrelated edits to `AGENTS.md` and
  `padars/tests/test_registration.py` were already present and remain
  uncommitted; preserve them.

## Phase 8 status and implementation boundary

The committed Moodle integration is a deterministic mock vertical slice:
durable `LMS Sync Operation` records, idempotency keys, entity mappings,
enrollment state, retry recovery, and desk actions exist. There is no live
MuTMS adapter or verified tenant/course/user/enrollment call in the committed
code. Moodle 5.2.4 and MuTMS `tool_mutenancy` 5.2.4.01 are the recorded local
versions. The local Moodle stack is running; live service functions,
capabilities, token scope, and tenant configuration must be checked before any
remote write.

Phase 8 must honor the administration addendum: tenant provisioning and
connection configuration are company-controlled, while School Managers keep
their scoped academic and course operations. Do not grant them system-level
Moodle credentials or tenant-binding controls. Do not implement a studio,
subscription console, tenant dashboard, grade synchronization, or unrelated
Phases 5–7 work here.

After Phase 8 has focused verification and a coherent commit, resume at the
checkpoint above. Phase 4 is already complete; continue with the unfinished
Phase 5 work, then Phases 6 and 7. Retain the Phase 8 implementation when its
original roadmap position is reached; do not rebuild it.

## Verification policy

During Phase 8, run static checks, the Phase 8 focused tests, and only the
essential live API checks supported by the configured development Moodle
service. Do not run browser end-to-end tests, another application's tests, or
the full Padars suite. Record live results separately from mock/unit tests.

## Return state after Phase 8 implementation

Updated: 2026-11-06. The Phase 8 implementation and offline verification are
committed; live API acceptance is blocked because Moodle web services are
disabled and no approved service token or target role IDs are configured. The
disposable `padars-phase12-fresh.local` schema migration succeeded. Its focused
contract and service modules passed 13 and 8 tests respectively. Static checks
passed. No live remote records or browser journey were run.

| Phase | Status after Phase 8 |
| --- | --- |
| 3 | Implementation complete; wider acceptance remains in Phase 11. |
| 4 | Complete and committed. |
| 5 | In progress; preserve the exact uncommitted Instructor/qualification, staff workflow, workload report, and test changes listed above. The last focused result remains 3 passed / 2 failed. |
| 6–7 | Temporarily deferred; not started. |
| 8 | Implementation complete with offline checks; live integration acceptance blocked on authorized Moodle service configuration. |
| 9–11 | Not started. |

Resume Phase 5 from the existing working tree. Do not reset, stage, or replace
its changes as part of the Phase 8 commit. Phase 4 stays complete, and Phase 8
must remain in place when the original roadmap reaches it.
