# Staging 2 manual test guide

Staging 2 is the active manual-test priority. Stage 1 remains available at
`http://kara.loc` with its original checkout and runtime.

Open **http://stage2.kara.loc/login**. If your computer does not resolve this
name, add `stage2.kara.loc` to the same DNS/hosts IP entry used for `kara.loc`.
The deployment is for synthetic development data; it uses local HTTP.

Accounts and generated passwords are in the owner-only server file:
`/home/weinno/frappe/sites/stage2.kara.loc/workspace/private/staging2-credentials.json`.
Never commit or distribute that file. Use separate browser profiles or log out
when changing roles. No real student contact details were seeded.

| Account | Default Role Profile | Landing screen |
| --- | --- | --- |
| `Administrator` | Built-in trusted company administrator | Desk; infrastructure setup |
| `manager@stage2.example.invalid` | Padars School Manager | `/app/padars` |
| `teacher@stage2.example.invalid` | Padars Teacher | `/teacher` |
| `student1@stage2.example.invalid` | Padars Student | `/school` |
| `student2@stage2.example.invalid` | Padars Student | `/school` |
| `student3@stage2.example.invalid` | Padars Student | `/school` |
| `guardian@stage2.example.invalid` | Padars Guardian | `/school` |

The three demo student accounts are already activated synthetic Education users;
log in with their email and generated password. They do not have national-ID
credentials. Test national-ID first-login separately through registration/import.

## Ready-to-test school data

School `STAGE2`, academic year `2026-2027 Staging`, two terms, Grade 11,
Mathematics, class 11A, one assigned teacher and three submitted enrollments.
The timetable contains Monday/Wednesday/Friday 09:00–10:00 lessons in the current
and following week at seeding time (school timezone Asia/Tehran). Use week
navigation if testing later. Student 1 has a confirmed attendance sample; the
guardian is verified only for Student 1.

The synthetic assessment example uses 100% written assessment and a 20-point
output. It is demonstration data, not the school's default grading policy.

## Suggested test sequence

1. **Manager and academic structure.** Log in as the manager. Open School Setup,
   Academic Year, Program, Student Group, Course Offering and Instructor from
   the Padars workspace. Check all relationships and the three-student roster.
   Academic Assignments are the scope layer; adding a teacher Role Profile alone
   does not assign a class. Use the Instructor's Link Frappe User action and the
   offering's assignment action when setting up additional teachers.
2. **Timetable and attendance.** Log in as the teacher at `/teacher`; confirm
   the Mathematics course, three students and scheduled lessons. Open a lesson
   on or before today, use the native Attendance Tool/session action, record
   attendance, then inspect the official Student Attendance record. Change a
   confirmed mark only through its reasoned correction action. Future lessons
   should not allow premature attendance; missing evidence does not mean absent.
3. **Student view.** Log in as Student 1 at `/school`; check current and next
   week's lessons, course and confirmed attendance. Repeat as Student 2 and
   verify Student 1's attendance is not shown as their own. Empty learning lists
   are expected while Moodle is disabled.
4. **Guardian view.** Log in as the guardian; only Student 1 should be selectable.
   Check the same child's timetable, attendance and published reports. Supplying
   Student 2's ID in the URL/API must be rejected.
5. **Assessment/report cards.** As manager inspect the demo Assessment Plan,
   approved School Assessment Scheme, approved Assessment Results and Report Card
   Publications. Student/guardian `/report-cards` must show only their published
   records. Test creating another assessment through the native Assessment Plan
   and Assessment Result Tool; teachers enter drafts, managers approve results,
   then preview and publish with a complete scheme. Published records retain
   history; corrections need the controlled correction/version workflow.
6. **Registration/import.** As manager open Student Registration. The CSV/Excel
   action must create a saved Student Identity Data Import first. Download the
   native template, keep national ID/phone cells as text, upload a **private**
   synthetic file, inspect preview and execute. For a new provisional identity,
   test `/student-activation` (also linked from login) using its Iranian national
   ID/mobile and complete the new-password/Gmail flow. SMS is disabled; no live message is expected. Use
   controlled test contact details. Do not enter real children's IDs or phones.
7. **Security.** Manager/teacher must not manage Role Profiles, Custom Fields,
   Customize Form, scripts or infrastructure credentials. Students and guardians
   must not open unrelated student data or private import attachments. A Role
   Profile is a coarse role preset, not proof of school/class/guardian scope.
8. **Company-only role setup.** With the trusted Administrator account open
   `/app/role-profile`. Confirm all twelve `Padars ...` presets. Assign profiles
   using User's native Role Profiles table. Company Administrator/Moodle Operator
   are company-only; do not assign them to school customers. Existing customized
   profiles are preserved during installation/migration.

## Expectations and known limits

- Basic academic work, timetable, manual attendance, native import/onboarding,
  local assessment review/publication and scoped portals are the test target.
- Moodle is disabled. No tenant, live course, roster, grade synchronization or SSO
  is claimed live-verified. PlugNmeet evidence/recordings and live SMS are not
  configured. Asynchronous activity policies require actual supported LMS data;
  do not substitute mocked completion for live-class attendance.
- Reports from unavailable integrations remain empty/unavailable. No decorative
  data or fake live course links are supplied.
- HTTP role/asset/upload checks and focused backend tests do not replace your
  browser interaction and usability feedback or the final release gate.

When reporting a problem record the role, URL, record name, action, expected and
actual result. Include response status/error text when available; omit passwords,
national IDs, phone numbers and private file contents.
