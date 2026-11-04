# MVP ERD

```text
School (school_code unique)
  ├──< School Membership >── User
  └──< School Course Offering >── Academic Year
                              ├── Program
                              ├── Course
                              ├── Student Group
                              └── Instructor

School Course Offering ──< LMS Sync Operation
School Course Offering ──< LMS Entity Mapping (local_doctype + local_name + remote_context)
School ──< LMS Entity Mapping
School ──< LMS Enrollment State >── User
LMS Enrollment State ──> School Course Offering

Education Program Enrollment (extended with padars_school)
Education Student Group (extended with padars_school)
Education Course Schedule / Assessment Plan / Assessment Result
  (optionally extended with padars_course_offering)
```

Compound business keys are validated server-side because the MVP needs portable Frappe behavior across installed database engines. Single-field identities use Frappe `unique` fields where appropriate.

