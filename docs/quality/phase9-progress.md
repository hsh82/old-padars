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
submitted results. A scoped roster API is connected to the native bulk tool.
Padars replaces the upstream HTML template renderer with DOM text and attribute
setters for names, criteria and comments, and the tool saves draft marks. The
submission endpoint remains closed pending an approval workflow.

The focused `padars.tests.test_scheduling` integration module passed nine tests
on `padars-phase12-fresh.local`, including the Frappe validation hook for score
bounds, duplicate/missing criteria, client-supplied maximum, and plan criteria
access and draft entry for an assigned teacher versus an unrelated user, and
rejection of updates to submitted results, tool access and roster scope.
JavaScript syntax was checked; browser interaction and hostile-text rendering
have not been browser-tested. This is not a
complete grade-entry or publication acceptance test.

Moodle grade mapping and import, review, approval, report-card calculation,
versioned publication, correction and student access remain unimplemented.
Non-platform Assessment Result submission remains closed until its approval
workflow and permissions are implemented. The school's grading rules still
require explicit configuration and approval.
