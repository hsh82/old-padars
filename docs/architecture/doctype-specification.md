# DocType specification

This describes the site-per-school model. Padars is pre-release; installing on
a clean site is supported without an old experimental schema migration promise.

## School

`school_code` is the stable unique local identity. School name, status, current academic year, primary school manager, and optional configuration are stored here. A unique active key enforces one active School per site. Platform administrators control status and the primary manager.

## School Membership

Retained as historical affiliation; it does not grant or gate authorization.

## Academic Assignment

Links an enabled User, optionally an Instructor, to a Program, Student Group,
or School Course Offering, with status, validity dates, and action flags.
The same active user/scope combination cannot be duplicated. Effective access
also requires the appropriate Frappe role and action permission.

## School Course Offering

Represents one annual teaching instance. The business key is School + Academic Year + Course + Student Group. The controller verifies compatible group/year/program/term context, curriculum membership for adopted class sections, and an active instructor. A curriculum-generated offering retains its adoption version and copied required-course/weekly-hours metadata. Teacher LMS enrollment requires a matching active academic assignment.

## School Curriculum Adoption and School Curriculum Course

An annual, school-specific snapshot of an Education Program's course template. A unique version key identifies School + Academic Year + Program + Version; at most one version is Active. Drafts can be edited, Active snapshots can only be archived, and Archived snapshots remain immutable. Child rows snapshot the Education Course link, course name, required flag, and optional expected weekly hours. Education remains authoritative for Programs and Courses.

Education Student Groups marked as Padars class sections link to an active adoption at creation. School, year, Program, and term must match. A stable unique key prevents duplicate section codes within a School + year + Program. After offerings exist, the section's academic identity is fixed. Students must have a submitted Education Program Enrollment for that School, year, Program, and, when selected, term; a student can belong to only one Padars class section for that scope. Roster assignment and annual offering generation are idempotent manager actions.

## Student Identity

Private registration reservation with a unique keyed national-identifier digest
and unique optional Student and User links. A provisional identity may hold a
mobile number and a separately hashed first-login credential before those links
exist. School managers have read/import permission; creation and changes are
controlled by registration services. Data Import access is limited to each
manager's own Student Identity imports. The Student and Program Enrollment
remain Education records. See [student registration](student-registration.md)
for requirements, key management and current limitations.

## Student Registration Application

Stores a pending application, encrypted national ID, keyed identity and status
reference digests, consent declaration, phone verification state, and approval
status. School managers may read and approve/reject; public access uses an
opaque bearer reference and does not grant a Frappe session. Education Student
and Program Enrollment continue to own academic records.

## LMS Settings

Single DocType for adapter selection and server-side endpoint/token configuration. The MVP defaults to `Mock`; the real Moodle adapter is not claimed complete.

## LMS Entity Mapping

Maps an approved local record type to a remote type/id inside an explicit remote context. School consistency and duplicate local/remote identities are validated; arbitrary Dynamic Link targets are rejected.

## LMS Enrollment State

Stores desired and observed enrollment separately, with role, verification timestamp, and safe error text.

## LMS Sync Operation

Persistent job intent with target Dynamic Link, operation type, school, unique idempotency key, state, attempts, retry timestamp, and diagnostic text. Supported operation/target pairs are tenant/School, user/User, course/School Course Offering, and enrollment/LMS Enrollment State. State transitions, retry exhaustion, target-school consistency, and safe diagnostics are controlled by the controller/service.

## Not implemented

Report Card Publication, School Enrollment, durable bulk import result storage, and portal/SSO session records are not present. The existing Education records remain authoritative until those contracts are approved.

