# Permissions and tenancy

Each school has its own Frappe site and database. One active School identifies
the site; School Membership is not an access prerequisite. Platform
administrators and System Managers retain the recovery path. The initial
primary manager receives Padars School Manager and Academics User roles;
changing that manager does not automatically revoke roles from the old user.

School managers have school-wide academic access, subject to action permissions.
Academic staff, teachers, grade-entry staff and read-only users need both the
relevant role and an active, date-valid Academic Assignment. Assignments cover
a Program, Student Group or School Course Offering, and carry separate flags
for editing, marks, attendance and sensitive records. Program scope includes
its groups; offering scope remains narrower. List filters and document checks
both enforce scope. Scoped staff cannot change defining relationships or a
group roster to expand their own access. Student accounts can access their own
supported records, but do not receive a full Student Group roster. Guardian
access is closed pending verified relationships.

Frappe custom permission types control `enter_grade`, `manage_attendance`,
`view_sensitive_student_data`, and `manage_moodle`; `approve_grade` is
reserved for a future approval workflow. Submission and cancellation of
Assessment Results by non-platform users remain disabled. A Moodle manager is
separate from a school manager; credentials remain server-side. Tenant
provisioning is platform-only.

Initial installation adds role permissions and initializes action defaults
after fixtures are synchronized. Frappe copies standard permissions into
Custom DocPerm when customization starts. Subsequent administrator changes to
the action defaults are preserved; review role permissions after upstream
Education changes.

Academic attachments must be private site files and require access to their
parent record. Direct DocShares of protected records or their files are
rejected. Install and migration validate existing shares and attachments and
stop for unsafe records without deleting them. Reports and selected Education
RPCs that have not been reviewed for scope are disabled for academic users;
some native workflows therefore remain unavailable until scoped replacements
are implemented. This is not a complete audit of all upstream endpoints.
