# Implementation plan

## Completed in this slice

- Repository and installed-source audit.
- Architecture documentation and repository skills.
- Shared-site tenancy decision.
- Padars School, membership, course-offering, and LMS persistence models.
- Mock-backed course-offering sync service with idempotency, mapping, retry, and failure state.
- Frontend checkpoint: school-aware form helpers, Course Offering Moodle actions, Education selector extensions, and the LMS Synchronization Monitor page.

## Temporary priority and resume point

Phase 8 Moodle/MuTMS implementation and focused offline verification are
complete; live integration acceptance remains blocked until company service
configuration is available. The exact preemption checkpoint, unfinished Phase
5 work, and preservation rules are in
[`phase8-priority-checkpoint.md`](phase8-priority-checkpoint.md).

After this Phase 8 implementation is committed, resume the existing Phase 5
working tree, then continue Phases 6 and 7. Phase 4 is already complete and
must not be repeated. Phase 8 remains implemented when the original sequence
reaches it.

## Remaining roadmap

1. Phase 8: implementation complete with offline verification; live MuTMS
   tenant/course/user/enrollment acceptance is blocked on service credentials
   and target capabilities.
2. Resume Phase 5, then implement Phases 6 and 7.
3. Continue with Phase 9 grades, Phase 10 guardians/extensions, and Phase 11
   comprehensive integration and release verification.

## Frontend follow-up

- Add a backend-backed bulk student registration contract before building CSV/Excel preview UI.
- Add account provisioning state/retry APIs before adding student account actions.
- Add Moodle SSO/course URL and report-card publication APIs before exposing those buttons.

