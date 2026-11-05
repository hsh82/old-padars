# DocType specification

> This specification documents the experimental shared-site model currently
> in source. Review it against [ADR-005](../decisions/ADR-005-site-per-school.md)
> before changing schemas. Since Padars is pre-release, Phase 1 may simplify or
> replace these models without an old-schema compatibility promise.

## School

`school_code` is the stable unique local identity. `school_name`, status, current academic year, and optional company/configuration metadata are stored here. System Manager and Education Manager manage records; non-privileged access is membership-scoped.

## School Membership

Links User to School with a school role, status, and optional validity dates. One active membership is allowed per User/School/role combination. It is the authorization source for shared-site school access.

## School Course Offering

Represents one annual teaching instance. The business key is School + Academic Year + Course + Student Group + Offering Identifier. The controller verifies that the group year and program/course context are compatible and that the instructor has an active school membership.

## LMS Settings

Single DocType for adapter selection and server-side endpoint/token configuration. The MVP defaults to `Mock`; the real Moodle adapter is not claimed complete.

## LMS Entity Mapping

Maps an approved local record type to a remote type/id inside an explicit remote context. School consistency and duplicate local/remote identities are validated; arbitrary Dynamic Link targets are rejected.

## LMS Enrollment State

Stores desired and observed enrollment separately, with role, verification timestamp, and safe error text.

## LMS Sync Operation

Persistent job intent with target Dynamic Link, operation type, school, unique idempotency key, state, attempts, retry timestamp, and diagnostic text. Supported operation/target pairs are tenant/School, user/User, course/School Course Offering, and enrollment/LMS Enrollment State. State transitions, retry exhaustion, target-school consistency, and safe diagnostics are controlled by the controller/service.

## Not implemented

Report Card Publication, School Enrollment, bulk import result storage, and portal/SSO session records are not present. The existing Education records remain authoritative until those contracts are approved.

