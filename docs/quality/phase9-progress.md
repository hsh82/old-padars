# Phase 9 assessment and report-card progress

Phase 9 is **in progress**. Education Assessment Plan and Assessment Result
remain authoritative. Padars now checks result scores before Education grade
calculation: the result must contain each configured plan criterion exactly
once, plan maxima must be positive and finite, and scores must be finite and
within each criterion's range. The result maximum is derived from the plan.
The native grading scale remains responsible for grades; no school formula is
introduced.

The native Assessment Result form can load criteria for an Assessment Plan the
caller can read. The native mark-result RPC now creates or updates one scoped
draft through Education's document lifecycle, with a plan lock to serialize
concurrent creation. It rejects inactive group members, invalid scores and
submitted results. A scoped roster API is implemented and tested separately.
The native bulk tool's roster override and submission endpoint remain closed:
its installed template interpolates names and comments into HTML without
escaping. Safe rendering and a reviewed approval workflow are needed before
opening that screen.

The focused `padars.tests.test_scheduling` integration module passed nine tests
on `padars-phase12-fresh.local`, including the Frappe validation hook for score
bounds, duplicate/missing criteria, client-supplied maximum, and plan criteria
access and draft entry for an assigned teacher versus an unrelated user, and
rejection of updates to submitted results, and roster scope. This is not a
complete grade-entry or publication acceptance test.

Moodle grade mapping and import, review, approval, report-card calculation,
versioned publication, correction and student access remain unimplemented.
Non-platform Assessment Result submission remains closed until its approval
workflow and permissions are implemented. The school's grading rules still
require explicit configuration and approval.
