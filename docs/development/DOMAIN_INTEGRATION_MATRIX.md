# Domain integration matrix

Status: **incomplete**. The approved twelve-domain list has not been located in
the repository or available Padars prompt attachments. The capability inventory
below is not a replacement for that list. Map it to the approved domains once
the source is available. Existing phase handoffs establish implementation status,
not complete product acceptance.

| Capability and source of truth | Current connections and evidence | Missing connections and acceptance |
| --- | --- | --- |
| School and authorization: Padars School, Frappe site and roles | One school per site; Academic Assignment scopes academic access. [Permissions](../architecture/permissions.md). | Verify all new endpoints and roles in the full security gate; tenant infrastructure remains company-controlled. |
| Registration and identity: Education Student and Frappe User; Padars Student Identity | Registration, import, first login and reconciliation are implemented. [Phase 3](../quality/phase3-progress.md). | Verify complete browser and cross-app journeys and guardian links. |
| Curriculum and enrollment: Education Program, Course, Academic Year/Term, Student Group and Program Enrollment | Padars curriculum snapshot and School Course Offering link academic records. [Curriculum](../architecture/curriculum-model.md). | Verify the full school fixture and all lifecycle transitions. |
| Staff: Education Instructor and Padars Academic Assignment | Scoped staff and teacher assignments with qualifications and workload report. [Phase 5](../quality/phase5-progress.md). | Assigned teacher overview now links native sessions, attendance and courses. Verify live replacements across Moodle roster and historical sessions. |
| Scheduling: Education Course Schedule | Padars validates offering, group and instructor relationships and generates schedules. [Phase 6](../quality/phase6-progress.md). | Connect online session identifiers, evidence policy and student portal; verify recurring-session lifecycle. |
| Attendance and care: Education Student Attendance, Student Leave Application and Student Log | Scoped manual attendance, leave rollback and sensitive care access. [Phase 7](../quality/phase7-progress.md). | Moodle automatic-completion policies for explicit asynchronous sessions now retain provenance, proposals, teacher confirmation, consumption and correction. Live PlugNmeet evidence and final acceptance remain unverified. |
| LMS: Moodle/MuTMS tenant, course, user and enrollment; Padars mappings and sync operations | Company-controlled enablement, durable after-commit operations, retries and live adapter exist. [Phase 8](../quality/phase8-progress.md). | Live service credentials and roles are absent; verify tenant isolation, roster changes and recovery against a disposable service. No live acceptance is claimed. |
| Learning and meetings: Moodle activities and PlugNmeet sessions | Moodle owns activity data; local PlugNmeet server and recorder containers were observed. | Activity discovery, teacher publication and scoped completion have focused implementation. Asynchronous completion evidence is linked to Course Schedule; live meeting evidence, recordings and actual live contracts remain unfinished/unverified. Never infer a session from aggregate participation. |
| Assessment and reports: Education Assessment Plan/Result | Scoped drafts, individual approval, versioned schemes, coverage-checked publication, immutable successor versions, student/verified-guardian viewing and generated PDF have focused checks. | Controlled mark corrections and guardian delivery now have focused implementation; Durable scoped Moodle discovery, approved mappings and audited draft imports are connected; live/browser/concurrency acceptance remains. |
| Guardian and portals: Education Guardian | Native Guardian/User and Student Guardian links require an explicit auditable manager grant. Published reports are accessible through a verified-child selector with revocation. | Weekly timetable, courses and official attendance are now connected at `/school`; teacher-published learning and per-child completion are now connected; browser acceptance and full privacy audit remain. |

For each approved domain, the completed matrix must additionally identify exact
record identifiers, API/event contracts, synchronization direction and conflict
policy, screens, roles, recovery, acceptance scenarios and verification evidence.
The cross-system target chain and release scenarios are in the product request;
no mock or local source inspection establishes a live integration result.
