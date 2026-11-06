# Stage 1 manual test guide

Target: `http://kara.loc`. Use your existing Administrator credentials for initial
setup. This is an implemented-feature preview, not full MVP or production
acceptance. Use fictional student data and separate browser profiles for roles.
If your browser cannot resolve `kara.loc`, map it to the staging server IP in
your workstation's hosts file or DNS. HTTPS is not configured on the current
proxy for this hostname. Hard-refresh Desk after this update.

## 1. Initial setup (Administrator)

Open `/app/padars-setup`. Create an Academic Year covering your test dates and
two Academic Terms within it. Create an enabled System User for the school
manager and choose it in School Setup. Save one School. Leave LMS and SMS
disabled for the initial academic tests. Log in as the manager in another browser.
Expected: the site has one school; setup is resumable; manager sees the Padars
workspace. The manager must not receive System Manager privileges.

## 2. Curriculum and class (School Manager)

Create Mathematics as an Education Course. Create a Grade 11 Program with that
Course and the required Padars grade/stream values. Use the Program's curriculum
adoption action, set weekly hours, and activate the adoption. Create a Batch
Student Group marked as a Padars class section, selecting the same year,
Program and adoption. Generate Course Offerings from that class.
Expected: repeated generation reuses the offering. An active adoption's content
cannot be silently edited. Another term/year combination is rejected.

## 3. Bulk registration and first login (Manager, then Student)

Open `/app/student-registration` and create a bulk import draft using its action.
Use the native Data Import template for Student Identity; import three distinct
valid-checksum synthetic Iranian national IDs and mobile numbers in `09...`
format. Keep spreadsheet ID/phone columns as text. Use the private upload,
preview and import actions. Follow `/student-activation` for each provisional
student: national ID and phone, then Gmail, name and a new confirmed password.
Expected: import completes; activation creates the Student/User once; subsequent
national-ID login uses the new password; the old phone credential fails. Retry
does not create duplicate identities. Shared-phone behavior can also be tested.
Gmail ownership and live SMS delivery are not verified in this stage.

## 4. Enrollment and class roster (Manager)

Use Returning Student to create draft Program Enrollments for the three activated
students, then review and submit them. Use the class's Add Enrolled Students
action. Expected: students join the class once; unsubmitted or wrong-year
enrollments are rejected. No student may occupy two active class sections for
the same Program/year.

## 5. Teacher assignment (Manager)

Create an enabled System User and an active Education Instructor. Use the
Instructor linking action, then Assign Teacher on the Course Offering. Enable
marks/attendance actions for the assignment. Open Teacher Workload from Desk
search with the Academic Year filter. Expected: the teacher and weekly expected
hours appear. This is planned workload, not actual hours or payroll.

## 6. Weekly timetable (Manager, then Teacher)

Create a Room. Use Education Course Scheduling Tool to create upcoming weekly
sessions for the class and offering. Try a conflicting room/teacher time.
Expected: schedules link to the offering; conflicts fail; repeating/rescheduling
does not remove historical attendance. Teacher can access assigned sessions but
cannot use manager-only batch rescheduling.

## 7. Manual attendance (Teacher)

Use Student Attendance Tool for a session today or in the past and outside any
holiday. Mark all three students, including one Absent and one Present with late
minutes. Reopen the session. Expected: records persist; updates reuse records;
future dates and unrelated classes fail. Use one attendance mode per group/date;
native Education limits mixing group/date and per-session attendance.

## 8. Leave and attendance report (Student, Manager/assigned Teacher)

Student creates their own draft Student Leave Application for scheduled lessons.
Manager or attendance-assigned staff approves it, then tests cancellation.
Expected: only the linked student's applicable lesson records change; cancellation
restores prior Absent records and leaves unrelated attendance intact. Run Padars
Daily Attendance Register and check the teacher sees only assigned records.

## 9. Assessment entry (Manager, then Teacher)

Configure Assessment Criteria, Assessment Group and a Grading Scale using test
rules. Create a scheduled Assessment Plan for Mathematics, with positive maxima
and a matching submitted grading scale; submit the plan. Open Assessment Result
Tool as the assigned teacher and select that plan/group. Enter every criterion
score for each student. Expected: drafts save, refresh preserves marks, negative
or excessive scores fail, and Open result reaches the native result form.
Teacher must not be able to submit results or access an unrelated plan.

## 10. Result approval and review (Manager)

Open a saved Assessment Result, review and Submit it. On Student, choose
Assessments → Review Approved Results and select the Program/year/optional term.
Expected: approved results appear; drafts are excluded; draft count and courses
without approved results are indicated. Submitted marks and a plan with recorded
results cannot be silently changed. This screen is not an official report card;
publication, correction versions and final calculation are unfinished.

## 11. Role boundaries (separate logins)

Teacher: deny another class's attendance/marks. Student: deny other students'
private records. Manager: deny other users' private files and unauthorized User
administration; deny LMS credentials, tenant changes, Customize Form and scripts.
Guardian access remains closed. Record any unexpected successful access as a
blocker, including its URL/action; do not use real data while investigating.

## 12. Optional sync monitor (Administrator/support only)

`/app/lms-sync-monitor` shows durable operations. Live Moodle is not configured
or accepted by this rollout. Mock operations are demonstrations only. Do not
expect working SSO, assignments, Moodle grades, PlugNmeet evidence or a complete
student/guardian portal. Do not enable a live integration without its reviewed
connection, host allowlist and role configuration.

## Feedback

For each case record PASS/FAIL/BLOCKED, role, record name, expected behavior,
actual behavior and exact error text. Give failures priority over visual polish.
No automated acceptance or browser result is implied by this checklist.
