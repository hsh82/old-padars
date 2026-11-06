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
concurrent creation. Direct Assessment Result document writes take the same
plan lock and check for another active student/plan result. A focused test
rejects a duplicate direct insert; concurrent requests have not been stress-tested.
Assessment Plan criteria, maxima, assessment group and grading scale cannot be
changed after a non-cancelled result exists; the validation uses the same plan
lock as result creation. This does not replace immutable report-card snapshots.
The entry service rejects inactive group members, invalid scores and
submitted results. A scoped roster API is connected to the native bulk tool.
Padars replaces the upstream HTML template renderer with DOM text and attribute
setters for names, criteria and comments, and the tool saves draft marks. A
School Manager with the explicit `approve_grade` permission can submit an
individual Education Assessment Result for approval from its native form; the
draft table links to existing or newly saved results for that review.
The bulk submission endpoint remains closed.

Development after Stage 1 runs on `codex/full-product` in a separate worktree.
Draft result updates now require the revision loaded by the client. Roster and
save responses carry the revision; stale or missing revisions reject updates
instead of overwriting newer marks. The nine focused scheduling/assessment
tests passed using that worktree on `padars-phase12-fresh.local`, including a
stale-write rejection. This change is not deployed to `kara.loc` Stage 1.

A manager-only preview API reads submitted Education results for a verified
school/program/year enrollment, optionally constrained to an Academic Term.
The Student form provides a manager action to select those filters and review
the returned results, draft count, and offered courses without an approved result
in the selected period. These are review indicators, not a completeness rule:
offerings have no term field and historical group membership is included. The
preview omits teacher comments and does not calculate or publish a report card.
Result approval also requires the related Assessment Plan to be submitted.

The focused `padars.tests.test_scheduling` integration module passed nine tests
on `padars-phase12-fresh.local`, including the Frappe validation hook for score
bounds, duplicate/missing criteria, client-supplied maximum, and plan criteria
access and draft entry for an assigned teacher versus an unrelated user, and
rejection of updates to submitted results, preview exclusion of drafts, tool access, roster scope, denial
of teacher submission, and manager submission with and without approval rights.
JavaScript syntax was checked; browser interaction and hostile-text rendering
have not been browser-tested. This is not a
complete grade-entry or publication acceptance test.

Moodle grade mapping and import, broader review, report-card approval and calculation,
versioned publication, correction and student access remain unimplemented.
Report-card publication and correction remain closed. The school's grading
rules still require explicit configuration and approval.
