# Teacher-published Moodle activities and completion

Moodle owns course modules, activity dates and completion. `Read Learning` extends
the existing LMS Sync Operation mechanism, after-commit queue, retries and remote
mapping checks. Assigned teaching staff may request this read-only operation for
their offering, without receiving tenant management or credential privileges.
Grade/learning reads use the existing long queue, including retries; ordinary
provisioning keeps its existing queue. The bounded roster allows 1–200 students
and up to 500 activities. Realistic school performance remains a release gate.

The installed Moodle source was inspected for `core_course_get_contents` and
`core_completion_get_activities_completion_status(courseid, userid)`. Contents
are requested with `excludecontents=1`. The shared adapter verification checks
site origin, tenant fingerprint, course category and each remote user's tenant.
Completion is fetched for each exact mapped user; the catalogue's embedded
completiondata belongs to the service account and is deliberately ignored.

Moodle Learning Snapshot retains one immutable, minimized catalogue and local
student-to-completion map per operation. Native module/instance IDs, tracking,
completion state, reported timestamp and override flag are preserved. Unknown,
duplicate or changed identifiers fail capture. Descriptions, files, raw activity
URLs, feedback, remote user names and override-user IDs are not copied. Raw
snapshots are readable only within authorized teaching scopes, never by students
or guardians. Files and DocShares retain the same private-data restrictions.

## Publication and family projection

The snapshot form lists actual activities and tracking, with selection checkboxes,
dates in the school's timezone, current selections and a reasoned publication
action. Only the assigned teacher or authorized academic editor may publish.
Read-only/grade-entry scope alone is insufficient. Course Activity Selection is
an immutable, monotonically versioned decision. An empty selection withdraws
publication, including when the external service is unavailable. Repeated equal
requests reuse the current decision.

Visibility/availability returned by the privileged service is not proof of a
student's access. Consequently, the student/family portal receives only explicitly
published titles and dates and that child's own completion state. Hidden or
restricted activities are identified to the publishing teacher; publication
shares metadata, while Moodle continues to enforce actual activity access.
New names/dates differing from the published snapshot are withheld and flagged
for teacher review rather than silently showing a stale deadline. Republishing
current metadata closes that warning.

The active class/program/year scopes in `/school` control the learning projection.
Students cannot read source snapshots or other students' status maps. Verified
guardians use the same selected-child projection. States distinguish incomplete,
complete, complete/pass and complete/fail; missing status or a failed/latest
source operation is unavailable. Observed timestamps are shown. The reported
completion timestamp is not claimed as an exact submission or live-join time.
No overdue classification is inferred from translated date labels.

All selections currently mean engagement only. No module, including PlugNmeet,
is offered as automatic class-attendance proof. Session policies, evidence
review and official attendance confirmation are the next unfinished workflow.
Grade-item mappings remain in their separate approved assessment workflow.

## Evidence

Seventeen focused scheduling/assessment tests passed, including two students with
different states, unpublished-title exclusion, source privacy, failed reads,
publication withdrawal and strict module/state matching. The extended focused
journey also covers changed-date review and republication. Fifteen offline
adapter contract tests passed, including request-user identity, content exclusion
and warning rejection. These use mock adapters; no live activity read, real worker
journey or browser interaction is claimed. No development changes are promoted
to the Stage 1 site.
