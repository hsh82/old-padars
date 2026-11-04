# Education gap analysis

Source inspected: local Education 16.1.0 checkout, paired with Frappe 16.52.0.

## Confirmed reusable behavior

- `Student` has a unique required `student_email_id`, a `user` Link, guardian and sibling tables, and server-side website-user creation unless `Education Settings.user_creation_skip` is enabled.
- `Student Applicant` already represents application status, program, academic year, optional term, and guardian data.
- `Academic Year` validates date order; `Academic Term` validates uniqueness and containment within its academic year.
- `Program Enrollment` requires Student, Program, Academic Year, and Enrollment Date. Its controller prevents duplicate student/program/year/term records and creates `Course Enrollment` records on submit.
- `Course Enrollment` prevents duplicate student/course/program-enrollment combinations.
- `Student Group` owns academic year, optional term/program/course, roster, and instructors, and validates roster membership against submitted Program Enrollment when Education settings enable those checks.
- `Instructor` has an Education naming strategy and duplicate employee validation.
- `Assessment Plan` and `Assessment Result` already support course/group/year/term links, grading scales, scores, grades, submission, and duplicate result prevention.
- `Education Settings` is a global Single DocType; its academic-year/term defaults are site-wide, not school-specific.

## Gaps and safe extensions

- Education has no independent School or school membership boundary. Padars adds these as new DocTypes.
- Education has no annual teaching-instance record with a school-scoped Moodle identity. Padars adds `School Course Offering`.
- `Program Enrollment` is sufficient for annual registration, so Padars adds a `padars_school` Custom Field rather than a duplicate School Enrollment DocType.
- `Student Group` needs a school context for shared-site validation; Padars adds `padars_school`.
- Padars document-event hooks validate that school-scoped Program Enrollment and Student Group roster entries resolve to a Student User with an active School Membership; this composes with Education validation without overriding its controller.
- `Course Schedule`, `Assessment Plan`, and `Assessment Result` need an optional offering link for future alignment; Padars provides fixture Custom Fields.
- Assessment periods are not the same as Education Academic Terms. The first slice does not hardcode Iranian grading rules; a configurable period extension remains pending.

