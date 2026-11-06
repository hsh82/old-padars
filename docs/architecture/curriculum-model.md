# Curriculum and academic setup

## Ownership

Education remains the source of truth for `Program`, its `Program Course`
rows, `Course`, `Academic Year`, `Academic Term`, `Program Enrollment`,
`Student Group`, and the Student Group roster. Padars adds grade/stream fields
to Education Program and class-section fields to Education Student Group.
Padars does not introduce a duplicate program, course, enrollment, or class
roster model.

## Annual adoption and versioning

A School Manager creates a `School Curriculum Adoption` from a saved Education
Program and Academic Year. Padars copies each Program Course into a
`School Curriculum Course` child row with a Course link, course-name snapshot,
required flag, and editable expected weekly hours. Versions are sequential for
School + Academic Year + Program. One adoption may be Active at a time.

Drafts may be customized. Activation requires at least one course. Active
snapshots can only be archived; Archived snapshots cannot be reactivated or
edited. New Student Groups require an Active adoption. Existing groups keep
their historical adoption when it is archived, and offerings can still be
generated from that immutable snapshot.

## Class sections and roster

A Padars class section is an Education Student Group with `group_based_on` set
to `Batch`, a School, Academic Year, Program, section code, and curriculum
adoption. Its linked Academic Term, when present, must belong to the same
Academic Year. A unique digest prevents duplicate section codes for a School,
year, and Program. Once any Course Offering exists, the group's School, year,
Program, type, section code, and adoption cannot change.

Roster assignment selects enabled Students with a submitted Education Program
Enrollment for the same School, year, Program, and term when set. It uses
permission-aware lists, and the Student Group controller revalidates every
member on save. An active student can appear in only one Padars class section
for the same School, year, and Program. Assignment is repeatable without
duplicating members.

## Course Offering generation

Generation creates or reuses the existing Padars `School Course Offering` for
each course in the adopted snapshot. Each record keeps the annual offering
business key (School + Academic Year + Course + Student Group), links the
adoption version, derives Academic Term from the Student Group, and copies the
required flag and expected weekly hours. Repeating the action is idempotent;
conflicting existing offerings require review rather than silent replacement.
The Course Offering remains the teaching instance used by later scheduling,
teacher assignment, and Moodle phases.

## Boundaries

Teacher authorization and workload, schedule conflict detection, examinations,
Moodle synchronization, and grading are implemented in later roadmap phases.
The manager actions are server-authorized; form buttons are only a user
interface convenience.

Manual Student Group membership accepts enabled students registered on the site without requiring a submitted Program Enrollment. Native Education optional batch/course validation settings still apply. Program Enrollment remains a separate academic record used by bulk roster addition, portals and report cards.
