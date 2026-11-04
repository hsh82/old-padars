# System overview

Padars is a companion app to Frappe Education. Education remains the source of truth for students, academic years/terms, programs, courses, program enrollment, course enrollment, groups, instructors, schedules, assessment plans, and assessment results.

Padars owns the independent-school boundary and external-LMS state:

```text
School ──< School Membership
   │
   └──< School Course Offering ──> Education Course / Student Group / Instructor
                    │
                    └──> LMS Sync Operation ──> Moodle adapter ──> LMS Entity Mapping
```

The Moodle adapter is server-side and mockable. A DocType save never performs an HTTP request. Tenant, user, course, and enrollment requests persist local operations and enqueue processing after commit. The checked-in adapter is deterministic mock behavior; live MuTMS transport and SSO remain external release prerequisites.

