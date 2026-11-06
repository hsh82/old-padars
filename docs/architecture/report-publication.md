# Reviewed report publication

Report Card Publication owns an immutable, derived publication snapshot. It is
not a second marks database: all source marks remain Education Assessment
Results. Managers select one approved School Assessment Scheme per enrolled
Course. Publication rejects incomplete course coverage, mixed term/annual
schemes, nonmatching school/program/year, unsubmitted enrollment/results and
missing grade-approval permission. No global average or national formula is
invented; each course uses its explicit approved scheme.

The preview returns a content digest. Publication rebuilds sources and requires
that digest, so changed marks/configuration require another review. Student and
enrollment row locks serialize version allocation; a unique scope/version key
also prevents duplicate versions. A repeated identical publication reuses the
existing record. A changed publication requires a correction reason and stores
`supersedes`, actor and timestamp without changing older records.

Snapshots retain school/student display labels, enrollment, period, course
outcomes, selected scheme/version, weights, original scores/maxima, result IDs
and revisions, rounding mode and approved grading intervals. Private teacher
comments are omitted. No direct create/update/delete is available to school
customers; the publication service and controller enforce creation and history.
Attachments must be private and direct shares are blocked.

Managers can preview/publish from the Student form. Published records open the
student-facing `/report-cards` view and a protected PDF download. Students can
read/list/print only their own published records; guardians remain denied until
verified relationship access is implemented. List APIs are paginated.

The print format and self-contained PDF use escaped snapshot values. A native
Frappe PDF attempt on the disposable test hostname failed to resolve site assets;
the self-contained export avoids that dependency and produced a PDF in focused
tests. Browser interaction, cross-request concurrency and final deployment
verification remain open. This development work is not deployed to Stage 1.

## Correcting underlying marks

The approved Assessment Result form exposes a manager-only Correct Result
action. It requires grade-approval permission, a current result revision and a
reason. The service atomically cancels the retained source and creates a native
Education amendment draft using `amended_from`. Failure restores the original
approved result. The reason, reviewer and timestamp are protected Custom Fields;
teachers cannot edit correction drafts or forge amendment links. A manager must
review and submit the replacement before it can contribute to a calculation.
Approved/cancelled/amended result history cannot be deleted through the app.

Existing publications stay unchanged after the correction. A new source preview
and explicit publication correction reason are required to issue another report
version. Focused tests cover rollback on draft-creation failure, teacher denial,
metadata protection, replacement approval and preservation of the earlier report.
