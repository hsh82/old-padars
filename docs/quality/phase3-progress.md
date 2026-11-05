# Phase 3 progress and verification

Date: 2026-11-05. Phase 3 has been implemented for review; release acceptance
requires the remaining checks below.

Staff can register individuals and create returning-student draft enrollments.
Frappe Data Import handles CSV/Excel template, preview, execution, retries and
row results through a Student import provider; the earlier separate CSV batch
processor was removed. Native Data Import remains limited to users with its
Frappe permissions, normally System Manager. Student import files must be
private. Format ID and phone spreadsheet columns as text to preserve zeros.

Iranian national ID check digits and mobile formats are validated. Public
applicants submit a consent declaration and can check or update a pending
application using a private bearer reference. A manager approves or rejects
applications. Approved students receive a disabled Frappe user; a mandatory
password change at `/student-activation` enables the account. Initial login is
national ID and mobile number in `09...` format. The School setting can require
SMS at application and activation through Frappe's configured SMS provider.
SMS jobs are queued after commit and no fallback is allowed while enabled.

On disposable `padars-phase12-fresh.local`, the Padars-only `--lightmode`
suite ran 50 tests successfully, with six legacy shared-site tests skipped.
Other apps' test suites were not run. Python/JSON parsing and JavaScript syntax
checks passed. The suite includes CSV/Excel parsing and mocked SMS delivery.

An additional focused run executed 17 registration tests, including a Frappe
HTTP test for the public application page before school setup. The page now
renders in that state; submission still requires a configured school. This HTTP
check does not replace browser interaction testing.

## Remaining acceptance limits

- With SMS disabled, a person who knows a student's ID and phone may activate
  their account before the student. The first password change does not establish
  identity. This fallback was explicitly requested and is not suitable where
  those values are considered secret or account takeover is unacceptable.
- SMS uses mocked delivery in tests; no live provider or end-to-end browser flow
  has been verified. A consent declaration is not independent verification of
  guardian authority or compliance with local requirements for minors.
- The site needs a persistent, backed-up Frappe encryption key and a genuine
  student email. Review Frappe request/error logging before processing real
  national IDs; verbose diagnostics can contain request arguments.
- Duplicate prevention applies to identities registered through these services
  and the configured Data Import provider. Existing Students or records created
  directly through other Education paths need reconciliation; site-wide
  duplicate prevention has not been established.
- Review import file and status-reference retention practices before use. The
  bearer reference is the applicant's only access to their pending application.

## Candidate for closing the direct-creation gap

A possible change is a Student `before_insert` guard requiring a matching
Padars Student Identity reservation, with registration creating that
reservation before inserting the Education Student. Direct form, API, and
upstream Education paths without a reservation would fail. Existing Students
would still need a reviewed reconciliation process. This candidate was not
applied: automatic approval review rejected the global guard because it could
disrupt Education and administrator workflows. Its compatibility and rollout
need explicit review before applying it.
