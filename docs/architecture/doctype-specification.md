# DocType specification

## School

`school_code` is the stable unique local identity. `school_name`, status, current academic year, and optional company/configuration metadata are stored here. System Manager and Education Manager manage records; non-privileged access is membership-scoped.

## School Membership

Links User to School with a school role, status, and optional validity dates. One active membership is allowed per User/School/role combination. It is the authorization source for shared-site school access.

## School Course Offering

Represents one annual teaching instance. The business key is School + Academic Year + Course + Student Group + Offering Identifier. The controller verifies that the group year and program/course context are compatible and that the instructor has an active school membership.

## LMS Settings

Single DocType for adapter selection and server-side endpoint/token configuration. The MVP defaults to `Mock`; the real Moodle adapter is not claimed complete.

## LMS Entity Mapping

Maps a local Dynamic Link to a remote type/id inside an explicit remote context. Duplicate local and remote identities are rejected.

## LMS Enrollment State

Stores desired and observed enrollment separately, with role, verification timestamp, and safe error text.

## LMS Sync Operation

Persistent job intent with target Dynamic Link, operation type, school, unique idempotency key, state, attempts, retry timestamp, and diagnostic text. State transitions are controlled by the controller/service.

