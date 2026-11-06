# Teacher overview

`/teacher` connects the assigned teacher's dated Education Course Schedules and
School Course Offerings. Native permission-aware queries and current instructor
assignments constrain the weekly/today view; School Managers can inspect their
school's overview. Guest/student/guardian roles cannot invoke the teacher API.
The view is bounded to 200 sessions and 100 offerings, with week navigation,
explicit school timezone, empty states and an overflow message.

Course and class names are batch-resolved. Active roster counts are projected
only for authorized groups; names/contact information are not returned. Lessons
link to native Course Schedule, retaining Education's existing Mark Attendance
route to Student Attendance Tool. Asynchronous lessons expose their existing
policy/evidence actions. Courses link to the offering's learning and grade review
workflows. No duplicate attendance editor or course-content editor is introduced.

Teacher Moodle links require the current user's observed and desired Teacher
course enrollment, enabled connected real adapter, permitted HTTPS host and
matching tenant/user/course mappings. Managers require their own School Manager
enrollment. URLs are constructed from the approved base and numeric ID; no API
credential or password reaches the browser. Normal Moodle login remains the
explicit fallback; opening a URL is not verified SSO. Guardian users continue to
receive no child-impersonation launch links.

Two focused tests passed for native lesson/assignment scope, unrelated-session
exclusion, manager visibility, Guest denial, empty roster/future-attendance
behavior and the shared Moodle launch-link contract. JavaScript/HTML browser
interaction and real remote enrollments remain unverified.
