# Moodle integration

The integration boundary is `padars.integrations.moodle`. Frappe persists
local intent and status; the adapter owns all Moodle HTTP calls.

## Tenant and API contract

Each School receives one stable Padars installation UUID and one immutable
MuTMS tenant binding. An authorized company operator enables Moodle on the
School; the after-update hook writes a durable operation and queues it only
after commit. A stable MuTMS `idnumber` reconciles a create whose response was
lost. A site fingerprint detects cloned Frappe sites. Retries may reconnect to
the same tenant, but never update, replace, or delete it automatically.

The live adapter uses these Moodle and MuTMS web-service functions:

| Purpose | Web-service functions |
| --- | --- |
| Check connection | `core_webservice_get_site_info` |
| Find/create and verify MuTMS tenant | `tool_mutenancy_get_tenants`, `tool_mutenancy_create_tenant`, `core_course_get_categories`, `core_cohort_get_cohorts` |
| Create or reconcile a tenant member | `core_user_get_users_by_field`, `core_user_create_users`, `core_user_update_users`, `tool_mutenancy_allocate_user` |
| Create or reconcile a course | `core_course_get_courses_by_field`, `core_course_create_courses`, `core_course_update_courses` |
| Enroll and verify course access | `enrol_manual_enrol_users`, `enrol_manual_unenrol_users`, `core_enrol_get_users_courses` |

MuTMS supplies the tenant, category, and cohort IDs; Padars stores and verifies
them instead of assuming those identifiers are interchangeable. Stable local
identifiers are used for tenants, Moodle users, and courses. Existing remote
records are checked for tenant, category, and Padars ownership before reuse.
The integration does not call MuTMS tenant update or delete APIs.

For the pinned Moodle 5.2.4 / MuTMS 5.2.4.01 source, the MuTMS patch extends
`core_user_create_users` with an optional `tenantid`; Padars uses that for new
tenant members. A previously existing, exact Padars-owned global account is
allocated with `tool_mutenancy_allocate_user` and then verified. Recheck this
extension in the target site's generated API documentation before enabling a
different Moodle/MuTMS build.

The Moodle service token is stored in the server-only Password field. REST
requests use HTTPS, a server-configured host allowlist, form-encoded nested
parameters, POST bodies, certificate verification, finite timeouts, and no
redirect following. Tokens and response bodies are excluded from diagnostics.
The Moodle service must expose only the functions above to an authorized
service account; the target site's generated API documentation is the final
authority for its enabled service and permissions.

MuTMS documents `tool/mutenancy:view` for tenant lookup,
`tool/mutenancy:admin` at system context for tenant creation, and
`tool/mutenancy:allocate` for allocation. The allocation endpoint can also
turn a tenant member into a global user, so Padars calls it only for an exact
Padars-owned account that is currently unallocated. Company support must add
the minimum capabilities Moodle's live API documentation lists for the core
functions; do not solve a missing capability by issuing a site-administrator
token.

## Roles and administration

Only company System Administrators and the `Padars Moodle Manager` support
role can configure credentials, role IDs, tenant provisioning, reconnection,
and LMS enablement. School Managers can request course synchronization, select
eligible students for enrollment, inspect their own synchronization status,
and open their school's Moodle courses. They cannot edit tenant bindings or
connection credentials.

Moodle's core APIs do not provide role discovery. Company support must read the
role IDs from the target Moodle site and configure them server-side. Teacher
and Student use their configured course roles. School Manager uses a
company-configured course-scoped viewing role; the MuTMS tenant-manager role
is deliberately not granted because it includes tenant account and settings
capabilities outside the customer boundary. No System Manager or site-wide
Moodle role is assigned to school staff.
Automatic group-roster synchronization is a company-only School setting;
School Managers request eligible student enrollments explicitly.

## Durable processing

- `MoodleAdapter`: narrow interface for tenant, user, course, and enrollment reconciliation.
- `MockMoodleAdapter`: deterministic adapter used by offline tests.
- `LMS Sync Operation`: durable queued work, idempotency key, attempt state, retry limit, and safe diagnostics.
- `LMS Entity Mapping`: immutable local/remote IDs, tenant context, and Moodle URL.
- `LMS Enrollment State`: intended and verified course access for a Student, Teacher, or School Manager.

External jobs are queued after the local transaction commits. Retries reuse
stable external identifiers and verify remote state after writes. Remote
tenant provisioning is automatic; course and student enrollment requests are
available to the school's manager. Optional group-roster synchronization can
queue currently eligible students when enabled on the School by company support.
Moodle's manual unenrollment endpoint removes the user's manual course
enrollment as a whole; it does not accept a role ID. Padars blocks withdrawal
when another local enrollment state still requires or reports access. This guard
does not discover roles or enrollments assigned independently in Moodle; operators
must reconcile those before withdrawal. Missing mappings and conflicting local
states fail for operator review rather than creating records during removal.
Keep Padars courses under the MuTMS tenant category. MuTMS tenant members can
access standard non-tenant courses by default, so the Moodle operator must
restrict those categories when that access is not intended.

The local Moodle code tree is Moodle 5.2.4 (Build 20261005) with MuTMS
`tool_mutenancy` v5.2.4.01; exact source metadata is in the
[version baseline](../operations/version-baseline.md). This confirms the local
code version and contracts only. Live web services are disabled on the
disposable Moodle site, and no Frappe connection token or approved target role
IDs are configured. Therefore no live tenant, course, user, or enrollment
write has been verified. Focused fake-client contract tests do not claim live
success. Mock and live operations have bounded retries and stale-worker
recovery.

Official references: [MuTMS multi-tenancy overview](https://docs.mutms.org/mutenancy/),
[MuTMS installation](https://docs.mutms.org/mutenancy/installation/),
[MuTMS technical architecture](https://docs.mutms.org/mutenancy/architecture/),
[MuTMS tenant management](https://docs.mutms.org/mutenancy/management/),
[MuTMS web services](https://docs.mutms.org/mutenancy/web-services/),
[Moodle web-service setup](https://docs.moodle.org/502/en/Using_web_services),
[Moodle 5.2 external services](https://moodledev.io/docs/5.2/apis/subsystems/external),
[function declarations](https://moodledev.io/docs/5.2/apis/subsystems/external/description),
[function definitions](https://moodledev.io/docs/5.2/apis/subsystems/external/functions),
[external API security](https://moodledev.io/docs/5.2/apis/subsystems/external/security).

