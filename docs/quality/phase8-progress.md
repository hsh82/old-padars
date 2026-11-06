# Phase 8 implementation and verification

Updated: 2026-11-06. Phase 8 implementation is complete for offline
development. Live Moodle acceptance remains blocked by service configuration.

## Implemented

- Company-only Moodle settings, enablement, tenant provisioning, and reconnect
  controls. School Managers retain course and student enrollment actions.
- A live Moodle REST adapter using the documented Moodle 5.2 and MuTMS
  functions, with HTTPS host allowlisting, POST-body tokens, redirects disabled,
  bounded timeouts, and redacted errors.
- Stable installation fingerprints, tenant idnumber reconciliation, remote
  category/cohort verification, tenant-member user and course reconciliation,
  configured course roles, and verified manual enrollment state.
- Durable operations, after-commit job queueing, idempotency, immutable
  mappings, retry recovery, and provisioning status.
- Focused offline tests for REST encoding/security, tenant retries and clone
  rejection, user ownership/tenant allocation, course category/idempotency,
  configured enrollment roles, and the existing mock service lifecycle.
- Backfill-before-unique migration patch for existing School, mapping, and
  enrollment records.
- Moodle/MuTMS setup runbook and source-verified API architecture notes.

## Verification

| Check | Result |
| --- | --- |
| Python compilation, JavaScript syntax, JSON parsing, and `git diff --check` | PASS — final static run recorded with this checkpoint |
| `padars.integrations.moodle.test_contracts` on `padars-phase12-fresh.local` | PASS — 13 focused contract tests |
| `padars.integrations.moodle.test_service` on `padars-phase12-fresh.local` | PASS — 8 focused integration tests, including manager restrictions and one teacher/three students |
| Schema migration on `padars-phase12-fresh.local` | PASS — integrity-key patch and company-only School field permissions synchronized |
| School Manager boundary | PASS — cannot write LMS Settings, enable/provision tenants, alter tenant bindings, or change company-only automatic roster policy; can queue own course/student operations |
| Live Moodle API calls | BLOCKED — web services are disabled and no approved service token or role IDs are configured |
| Full browser journey | NOT RUN — the Phase 8 checkpoint limits verification to focused tests and configured live API checks |

The local Moodle source was inspected read-only at Moodle 5.2.4 / MuTMS
`tool_mutenancy` 5.2.4.01, along with the complete official MuTMS
multi-tenancy, installation, tenant-management, technical-architecture, and
web-service docs and the Moodle 5.2 web-service setup and external API,
function, and security docs. No remote tenant, course, user, or enrollment has
been created. The failure to run live calls is an environment/configuration
blocker, not evidence that a live Moodle deployment works.

## Acceptance still required

- Withdrawal prerequisite: an existing enrollment may be set to Not Enrolled
  after local eligibility is removed; the worker uses existing active mappings
  and refuses to create users or courses during withdrawal. The focused Moodle
  service suite passed eight tests on `padars-phase12-fresh.local`, including a
  mock withdrawal after roster removal and a subsequent rejoin. When company
  support enables automatic enrollment, a Student Group edit reconciles existing
  student states and queues withdrawal after commit. Changes to Program Enrollment
  now trigger reconciliation when a Program Enrollment is submitted or cancelled.
  The focused mock test covers cancellation and subsequent submission. Student
  enablement/User-link changes and linked User enablement/type changes also
  reconcile active groups when automatic enrollment is enabled. The focused
  Moodle service suite passed eight tests after those hooks were added. When
  automatic enrollment is disabled, these events queue withdrawal of ineligible
  existing students but do not enroll newly eligible students. The focused mock
  test covers removal, rejoin with auto enrollment disabled, and denial of course
  provisioning through the internal withdrawal path. Live unenrollment remains
  unverified.
- Registration regression was attempted after the new hooks. The normal runner
  stopped in ERPNext fixture preload because `All Item Groups` was missing before
  registration tests ran. Light mode ignored the requested module filter and was
  interrupted when it continued into other Padars modules; it is not counted as
  a completed registration run.
- Teacher assignment or removal on a mapped, enabled offering now queues the
  current teacher and withdraws former teacher states. A focused mock integration
  test processed both replacement operations and confirmed reuse of the course
  mapping; eight Moodle service and five staff tests passed on the disposable
  site. Live replacement remains unverified and conflicting roles require review.
- After a tenant reconnect, mapped rosters are reconciled even when automatic
  enrollment is disabled; with it enabled, full eligible rosters are reconciled.
  A mock test covers a group removal while LMS is disabled, re-enable, tenant
  mapping reuse, and the resulting desired withdrawal. Live reconnect and queued
  withdrawals still require verification on an authorized Moodle service.
- The installed Moodle 5.2 manual unenrollment API removes the manual course
  enrollment rather than a specific role. Padars blocks withdrawal when another
  local role still needs or reports access, but cannot detect independent Moodle
  role assignments; operator reconciliation and live verification remain needed.

- An authorized company operator must enable the Moodle REST service, create a
  restricted service user/token, configure target role IDs and the Frappe host
  allowlist, and save credentials in LMS Settings.
- On the disposable target, run one live journey: enable one School, verify
  exactly one MuTMS tenant, create one course, enroll one teacher and three
  students, and confirm Moodle's enrollment API returns the expected course
  membership. Retry and disable/re-enable must reuse the same tenant.
- Verify a School Manager can complete the academic course/enrollment flow and
  cannot edit LMS Settings, enable Moodle, or provision/replace a tenant.
- Do not treat mock or fake-client success as live integration acceptance.

See [Moodle and MuTMS setup](../operations/moodle-mutms-setup.md),
[integration architecture](../architecture/moodle-integration.md), and the
[Phase 8 priority checkpoint](../development/phase8-priority-checkpoint.md).
