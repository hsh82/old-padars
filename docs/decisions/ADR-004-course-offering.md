# ADR-004: Own annual School Course Offering in Padars

## Context

Education Course and Student Group describe reusable academic entities and roster context, but neither represents a school-scoped annual teaching instance or remote LMS identity.

## Decision

Create `School Course Offering` with School, Academic Year, Program, Course, Student Group, optional Instructor, Offering Identifier, and status. The stable business key prevents accidental Moodle course reuse across schools, years, or groups.

## Consequences

Education schedules and assessments can link to an offering through optional Custom Fields. Moodle provisioning targets the offering, not the reusable Course.

