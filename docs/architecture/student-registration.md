# Student registration and identity

Education Student and Program Enrollment remain authoritative. Padars keeps a
separate, private identity reservation to enforce uniqueness of a normalized
national identifier across registration requests. The reservation contains a
keyed digest, not the national identifier, and points to one Student. It is not
a public search index. The site's Frappe encryption key must be backed up and
must not be rotated without rebuilding these digests from an authoritative
identity source. The identifier is not used as a password or account name.

Only a platform administrator or school manager may use staff registration and
enrollment services. Staff registration requires a name, international-format
phone number and a real email address because the installed Education Student
requires email. It requires Education Settings `user_creation_skip` to be
enabled, preventing implicit account creation. Returning enrollment uses the
existing Student and Education Program Enrollment. Batch requests are bounded
and use per-row savepoints; failures are returned without identifier values.

National identifier format and checksum vary by jurisdiction. Current syntax
normalization checks shape only; this does not assert legal validity. Phone
syntax is not proof of ownership. SMS verification, public applications,
approval and account activation require a configured provider, abuse controls,
and policy decisions, and are not enabled by these services. Existing Student
records created outside these services are not automatically matched by ID.
Review request and error logging before using real identifiers: verbose Frappe
diagnostics can include function arguments. See
[Phase 3 progress](../quality/phase3-progress.md).
