# Student and verified-family academic portal

`/school` and `padars.portal.get_academic_overview` provide one read-only
projection for an authenticated Student or a verified guardian child. Managers
may inspect an explicit student. Authorization runs before any academic query.
Guardians receive no native academic DocType permissions. All projections are
restricted to the primary School and the selected enabled Student.

Education owns submitted Program Enrollment, active Student Group membership,
Course Schedule, Course/Instructor names and submitted Student Attendance.
A timetable/course requires both active group membership and a matching
program/year enrollment. Withdrawal removes current course/session access;
the student's submitted attendance history remains visible. Draft/cancelled
attendance is excluded; a missing record is not labelled absent. Native
attendance status is displayed without inventing unsupported statuses.

The view covers a Monday–Sunday week in school dates, with week navigation,
200 sessions/attendance records and 100 offerings; overflow is explicit. Names
are batch-resolved and escaped. No roster, teacher comment, contact details,
national ID, token or integration diagnostic is included. The page is uncached
and has empty states and responsive tables.

Token-free Moodle links are available only to the Student themself, with a
connected enabled real Moodle adapter, approved HTTPS host, matching tenant
context for user/course mappings and desired/observed Enrolled state. The URL
is constructed from the approved base and numeric course ID, never trusted
from arbitrary remote_url data. Guardians do not launch as their children.
Normal Moodle login is the fallback; SSO is explicitly unverified. Learning
activities, deadlines, completion and live-class links/evidence remain pending
actual API implementation and service configuration.

Fourteen focused scheduling/assessment integration tests passed on the
disposable site. Portal coverage includes native relationships, unrelated-group
exclusion, own/verified-child access, withdrawal, retained attendance, HTML
escaping and course-link contracts. No browser or live Moodle success is claimed.
