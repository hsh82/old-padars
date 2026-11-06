# MVP ERD

```text
School (school_code unique)
  ├──< School Membership >── User
  ├──< School Curriculum Adoption >── Education Program
  │       ├── Academic Year
  │       └──< School Curriculum Course >── Education Course
  └──< School Course Offering >── Academic Year
                              ├── Program
                              ├── Course
                              ├── Student Group
                              ├── Academic Term (derived when set on group)
                              ├── School Curriculum Adoption (optional snapshot link)
                              └── Instructor

Education Student Group (extended with school/class-section fields and optional
  School Curriculum Adoption link) ── Education Program Enrollment roster

School ──< LMS Sync Operation (tenant provisioning)
User ──< LMS Sync Operation (user provisioning)
School Course Offering ──< LMS Sync Operation (course provisioning)
LMS Enrollment State ──< LMS Sync Operation (enrollment sync)
School Course Offering ──< LMS Entity Mapping (local_doctype + local_name + remote_context)
School ──< LMS Entity Mapping
School ──< LMS Enrollment State >── User
LMS Enrollment State ──> School Course Offering

Education Program Enrollment (extended with padars_school)
Education Student Group (extended with padars_school)
Education Course Schedule / Assessment Plan / Assessment Result
  (optionally extended with padars_course_offering; school visibility is derived from the offering)

School Assessment Scheme -> School Course Offering / Assessment Plan / Assessment Criteria
Report Card Publication -> Student / Program Enrollment / prior publication
  (immutable derived snapshot of approved scheme results and source provenance)
Education Program Enrollment remains the annual enrollment authority.
```

Compound business keys are validated server-side because the MVP needs portable Frappe behavior across installed database engines. Single-field identities use Frappe `unique` fields where appropriate.

