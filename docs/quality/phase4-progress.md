# Phase 4 progress and verification

Date: 2026-11-05. Phase 4 implementation and focused verification are complete
for development handoff; comprehensive browser and cross-app verification
remain in Phase 11.

Education remains authoritative for Programs/Courses, years/terms, submitted
Program Enrollments, Student Groups, and class rosters. Padars adds Program
grade/stream metadata, a versioned immutable annual curriculum snapshot,
class-section fields on Student Group, and term/adoption metadata on the
existing annual School Course Offering.

School managers can create an adoption from a Program, customize its Draft,
activate or archive immutable versions, mark a Batch Student Group as a class
section, assign submitted-enrollment students, and generate/reuse Course
Offerings. Server validation enforces school/year/Program/term consistency,
unique section identity, one active class per Student/Program/year, adoption
course membership, and stable historical links.

On `padars-phase12-fresh.local`, migration completed successfully. The focused
curriculum module passed 5 tests; the existing School Course Offering module
passed 2 tests. The curriculum tests cover normalized Grade/Stream uniqueness,
snapshot/version immutability, term/year mismatch, repeatable offering and
roster generation, duplicate class assignment, and non-manager denial. Python
compilation, JavaScript syntax, Frappe's JSON parser, and `git diff --check`
passed. The normal test runner's ERPNext preload is blocked by its missing
`All Item Groups` fixture; focused verification used light mode. Browser,
cross-phase, and full Education compatibility tests remain deferred to Phase
11.
