# ADR-006: Snapshot annual curriculum adoption in Padars

**Status:** Accepted for Phase 4 implementation

**Date:** 2026-11-05

## Context

Education owns reusable Programs and Courses, but Padars needs each school to
select and customize a curriculum for an Academic Year, preserve its history,
assign students to class sections, and generate annual School Course
Offerings. Editing an Education Program later must not rewrite the meaning of
an already adopted or delivered year.

## Decision

Reuse Education `Program`, `Program Course`, `Course`, `Academic Year`,
`Academic Term`, `Program Enrollment`, and `Student Group`. Add grade/stream
metadata to Program and class-section/adoption fields to Student Group.

Padars owns `School Curriculum Adoption` with child `School Curriculum Course`
rows. Each annual version snapshots course links, names, required status, and
expected weekly hours. Versions are sequential per School + Academic Year +
Program, only one version is Active, and activated contents cannot be edited.
An Active version may be archived but not reactivated.

Class sections remain Education Student Groups and may only be created against
an Active adoption. Existing sections preserve an Archived adoption. The
existing Padars School Course Offering remains the annual teaching record and
links the exact adoption version and copied course metadata. Generation and
roster assignment are idempotent and validate submitted Education enrollment.

## Consequences

- Education remains the single academic catalog and enrollment authority.
- Later changes to Program Course rows do not alter adopted snapshots.
- Archived versions and their class sections remain traceable.
- Offerings retain their annual business key; term is derived from the linked
  Student Group and does not change that key.
- Teacher assignment, workload, scheduling, Moodle, and grading remain later
  phase responsibilities.
