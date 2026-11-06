# Verified guardian access

Education Guardian.user and Student.guardians remain the relationship and
identity authorities. Verified Guardian Access is an auditable Padars grant
for one native Student Guardian row and one enabled authenticated User. School
Managers explicitly verify authority, provide a reason and bind a matching
Guardian email/User. A fixed Padars Guardian role may be added by that narrow service;
no academic or system administration role is granted.

Access requires an Active grant, current matching native relationship row,
matching Guardian.user/email, enabled Student/User and the Padars Guardian role. It is
limited initially to published report cards. Draft marks, teacher comments,
student administration and unrelated children remain unavailable. Source
relationship/user edits revoke incompatible grants; reads also revalidate the
native links, so stale grants cannot authorize access. Revocation preserves
the grant history. Managers may explicitly verify a new grant after review.

Grant creation and revocation are service-only; bindings and audit metadata
are immutable. A unique active key and Student lock prevent duplicate active
grants. Guardian users cannot list the authorization records themselves.
School staff must perform their real identity/authority checks before using
the verification action; the software records that decision rather than
claiming to independently prove guardianship.

Manager actions on Student verify a saved native Guardian relationship and open
access history; the grant form revokes access with a reason. If no matching User
exists, verification creates only an enabled Website User with the Padars Guardian
role, suppresses welcome mail, and binds Guardian.user. The parent uses the
standard Frappe password-reset process. Existing users keep their other roles;
the service cannot grant arbitrary roles. No generic User write permission is
added to School Manager.

The report-card portal offers a verified child selector. Permission hooks,
list/read APIs and PDF delivery revalidate grants. Grant history is restricted
to managers/operators. School Managers receive native Guardian create/read/write
permissions, without deletion or User administration. Education's redundant
Customer save is skipped only when synchronized name, group and image already
match, allowing relationship-only Student edits without Customer permissions.
Changed Customer values still use native authorization.

The installed native Guardian role grants Desk access. Padars leaves it unchanged
and uses its own `Padars Guardian` role with `desk_access=0` for verified portal
access. Native Guardian membership alone is insufficient.
