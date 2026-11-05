# Student registration and identity

Education Student and Program Enrollment remain authoritative. Padars keeps a
separate, private identity reservation to enforce uniqueness of a normalized
national identifier across registration requests. The reservation contains a
keyed digest, not the national identifier, and points to one Student. It is not
a public search index. The site's Frappe encryption key must be backed up and
must not be rotated without rebuilding these digests from an authoritative
identity source. National ID is mapped at login to the real Frappe User without
storing it as the User name.

Only a platform administrator or school manager may use staff registration and
enrollment services. Staff registration requires a name, Iranian mobile number
and real email address because the installed Education Student and Frappe User
require email. Returning enrollment uses the existing Student and Education
Program Enrollment.

For two-column imports, a Student Identity may be provisional: it stores a
keyed identity digest, a mobile number and a Frappe password hash, but has no
Student, User, Frappe session or academic permissions. The initial secret is
invalidated transactionally when first-login setup collects a real Gmail address,
name and new password and creates the Education Student and Frappe User.
Per-identity locking serializes competing claims. Native Student creation is
not blocked; existing records without identity information require review.

Frappe's native Data Import is used for Student Identity CSV and Excel
intake. The provider requires national ID and phone only; names are optional.
The School Manager's Data Import access is restricted to this DocType and to
imports they own. Frappe's
native Student import retains its ordinary Education behavior. Import files
must be private, and IDs and phone numbers must be formatted as text to
preserve leading zeroes. Frappe previews, import logs, and retry are reused.

Iranian national IDs are checked for ten digits, repeated-digit values and a
modulo-11 check digit; this does not establish ownership or legal validity.
Phone syntax is not proof of ownership. Imported identities have no User until
the student uses the first-login link at `/login`, supplies their national ID
and mobile number in `09...` format at `/student-activation`, and completes
Gmail and password setup. Existing staff-created accounts stay disabled until
their password is changed. Shared phone numbers are stored in the non-unique
Frappe User `phone` field, which Frappe's SMS 2FA can also use as a fallback.
The school may require SMS verification at activation using Frappe's configured
SMS provider. With SMS disabled, national ID and phone are predictable, and an
attacker who knows both may activate the account first. Configure SMS to reduce
this risk. Existing Students created outside these services are not
automatically matched by ID. A public `/student-application` accepts a basic
application and adult/guardian consent declaration. An opaque bearer reference
permits status lookup; the applicant must keep it private. With SMS enabled,
submission requires a code sent through Frappe's configured provider. A school
manager approves or rejects applications; approval creates or reuses Education
records and a disabled account awaiting activation. The consent declaration is
not independent verification of a guardian relationship.
Review request and error logging before using real identifiers: verbose Frappe
diagnostics can include function arguments. See
[Phase 3 progress](../quality/phase3-progress.md).
