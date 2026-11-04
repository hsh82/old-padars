# ADR-003: Reuse Program Enrollment for annual registration

## Context

Education's Program Enrollment already requires Student, Program, Academic Year, and date; its controller prevents duplicate annual enrollment and creates Course Enrollment records on submit.

## Decision

Reuse Program Enrollment as the authority and add a `padars_school` Custom Field. Do not create a parallel School Enrollment record. Academic Term remains optional and is not treated as an Iranian assessment period.

## Consequences

School-aware enrollment validation must be composed around Education lifecycle events and tested after fixture installation. Existing Education behavior, including course-enrollment creation, is preserved.

