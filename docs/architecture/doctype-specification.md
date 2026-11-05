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

Represents one annual teaching instance. The business key is School + Academic Year + Course + Student Group. The controller verifies compatible group/year/program context and an active instructor. Teacher LMS enrollment requires a matching active academic assignment.

## Student Identity

Private registration reservation with a unique keyed national-identifier digest
and unique Student link. It is managed by the registration service; access is
not granted through a user-facing DocType role. The Student and Program
Enrollment remain Education records. See [student registration](student-registration.md)
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

