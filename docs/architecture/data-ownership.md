# Data ownership

| Concern | Owner | Padars boundary |
| --- | --- | --- |
| Student identity and guardian relationships | Education | Reuse; Education already links Student to User and creates a website user unless configured not to |
| Academic year, term, program, course | Education | Reuse |
| Annual student registration | Education `Program Enrollment` | Extend with a school Custom Field; do not create a second enrollment authority |
| Class roster and instructors | Education `Student Group`, `Instructor` | Validate school context through Padars fields/membership |
| Annual teaching instance | Padars `School Course Offering` | Owns school/year/course/group boundary and offering identifier |
| LMS connection and external state | Padars | Owns settings, mapping, desired/observed enrollment, and sync operations |
| Grades and assessment results | Education | Reuse; add offering/period extension only when requirements are confirmed |

