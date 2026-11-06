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
complete and committed; live integration acceptance remains blocked until
company service configuration is available. The saved Phase 5 checkpoint was
resumed and its focused implementation is now complete. The exact preemption
checkpoint and preservation history are in
[`phase8-priority-checkpoint.md`](phase8-priority-checkpoint.md).

Phase 4 remains complete and must not be repeated. Phases 5, 6, and 7 are now
complete for development handoff; Phases 5 and 6 were rechecked after Phase 7
permission changes. Phase 8 remains implemented when its original position is
reached.

## Remaining roadmap

1. Phase 5: implementation complete for development handoff; 5 focused tests
   pass. See [Phase 5 results](../quality/phase5-progress.md).
2. Phase 6: implementation complete for development handoff; 6 focused tests
   pass. See [Phase 6 results](../quality/phase6-progress.md).
3. Phase 7: implementation complete for development handoff; 5 focused tests
   pass. See [Phase 7 results](../quality/phase7-progress.md).
4. Phase 8: implementation complete with offline verification; live MuTMS
   tenant/course/user/enrollment acceptance is blocked on authorized service
   credentials and target capabilities.
5. Next: Phase 9 grades, followed by Phase 10 guardians/extensions and Phase 11
   comprehensive integration and release verification.

## Frontend follow-up

- Add a backend-backed bulk student registration contract before building CSV/Excel preview UI.
- Add account provisioning state/retry APIs before adding student account actions.
- Add Moodle SSO/course URL and report-card publication APIs before exposing those buttons.

