# Stable Padars identity keys

Frappe rename updates ordinary Link/Dynamic Link fields. It does not re-key
Padars hashes or immutable JSON snapshots. Moodle account/course identities are
also derived from local keys. Allowing an already-bound key to rename could
create a second remote entity, strand a mapping or let the same attendance
activity acquire a different consumption key.

A before_rename hook protects School, School Course Offering, User and Student
only once persisted Padars identity/integration history exists. Queued/failed
operations count as history because a remote call may have succeeded before a
local failure. Disabled mappings also retain ownership. School academic history,
student identity/guardian/report/grade/evidence records and a student's mapped
User are considered where relevant. Merge checks protect both the source and a
bound destination. No global Student creation guard is introduced.

Names/labels and ordinary permitted fields can still be edited; their existing
native authorization remains in force. Changing the primary key/email identity
or merging bound records needs a separately reviewed migration/reconciliation
workflow; no bypass or destructive repair endpoint is supplied in this milestone.
Unbound native Student creation and rename continue to work. Additional academic
master rename/merge cases remain part of the final endpoint/integrity audit.

A focused test calls Frappe's actual whitelisted rename service as Administrator:
queued offering/user identities and a bound School/Student cannot rename, queued
targets remain intact, merge into a bound Student is rejected, and an unbound
Student can be renamed. No remote API is called for these checks.
