# Data ownership

| Concern | Owner | Padars boundary |
| --- | --- | --- |
| Student identity and guardian relationships | Education | Reuse; Education already links Student to User and creates a website user unless configured not to |
| Academic year, term, program, course | Education | Reuse |
| Grade and stream labels on Programs | Education `Program` with Padars Custom Fields | Reuse Program and its Course child table; Padars validates grade/stream identity |
| Annual curriculum selection and version history | Padars `School Curriculum Adoption` and `School Curriculum Course` | Immutable snapshot of Education Program/Course rows, with school/year/version and optional expected weekly hours |
| Annual student registration | Education `Program Enrollment` | Extend with a school Custom Field; do not create a second enrollment authority |
| Class roster and instructors | Education `Student Group`, `Instructor` | Validate school context through Padars fields/membership; class sections reference a curriculum snapshot |
| Annual teaching instance | Padars `School Course Offering` | Owns school/year/course/group boundary, offering identifier, optional term, and the curriculum version used to create it |
| LMS connection and external state | Padars | Owns settings, tenant/user/course/enrollment mappings, desired/observed enrollment, and sync operations; live remote truth is not available locally |
| Grades and assessment results | Education | Reuse; add offering/period extension only when requirements are confirmed |
| Assessment calculation configuration | Padars School Assessment Scheme | Approved versions select Education plan criteria, explicit weights/scales and rounding; source marks remain in Education |
| Report-card publication and version history | Padars Report Card Publication | Immutable reviewed snapshots derived from approved Education results, retaining provenance and correction history |


Moodle Grade Snapshot retains minimized instructional evidence. Moodle Grade
Mapping owns explicit approved normalization configuration; Moodle Grade Review
retains immutable import decisions. Education results remain draft until native
manager approval. See [grade import](moodle-grade-import.md).
