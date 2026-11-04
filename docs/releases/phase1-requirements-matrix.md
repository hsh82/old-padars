# Padars Phase 1 requirements matrix

Updated: 2026-11-04

Source: `docs/input/Padars_Phase1_Requirements_and_MVP_Plan.md`, version 2.1. The source was found in the repository and contains the canonical feature and acceptance lists. Status is evidence-based: static inspection is not treated as an end-to-end test.

Evidence keys:

- `E-CODE`: implementation and metadata inspection.
- `E-STATIC`: Python compilation, JavaScript syntax, JSON validation, frontend smoke tests, and deterministic mock contract checks passed.
- `E-FRAPPE`: existing Frappe tests are present but were not executable in this environment.
- `E-STAGING`: no named staging site was identified; no deployment or database migration was run.
- `E-LIVE`: live MuTMS/SSO service was not configured or tested.

All rows are committed MVP scope except S23, which is conditional/manual as defined by the source roadmap.

| ID | Priority | Acceptance condition | Implementation path / owner | Status | Test evidence | Corrective action |
| --- | --- | --- | --- | --- | --- | --- |
| S01 | Required | School has a stable unique identity and controlled school metadata. | Padars `School`, unique `school_code`, controller validation. | PARTIAL | E-CODE, E-STATIC; no database test. | Run clean migration and duplicate-code test on staging. |
| S02 | Required | Academic Year and two assessment terms can be defined for a school. | Education Academic Year/Term; Padars school current-year link. | PARTIAL | E-CODE; no term/report workflow test. | Verify school-specific term use and confirm assessment-period contract. |
| S03 | Required | Programs represent grades/streams 7–12 without duplicate academic authorities. | Education Program/Course; Padars filters and offering relationships. | PARTIAL | E-CODE; no representative dataset. | Configure and test the school’s grade/stream catalog. |
| S04 | Required | Each school resolves to exactly one MuTMS tenant mapping. | Padars LMS Mapping, tenant operation, deterministic mock adapter. | BLOCKED | E-CODE, E-STATIC; E-LIVE unavailable. | Confirm MuTMS tenant API and run live tenant allocation test. |
| S05 | Required | School roles cannot read or mutate another school’s records, APIs, reports, files, or jobs. | Stage 1 actor-aware Padars query/direct hooks, Education RPC overrides, membership validation. | PARTIAL | E-CODE; migration verified on disposable `stage1.local`; full two-school suite is blocked by an unrelated ERPNext fixture duplicate. | Repair disposable fixture state; execute document/list/API/report/file/job negative suite. |
| S06 | Required | Current academic year is selected per school rather than from a global site default. | `School.current_academic_year`, authorized-school API, school-aware forms. | PARTIAL | E-CODE, E-STATIC; no browser test. | Verify multiple schools with different current years on staging. |
| S08 | Required | One durable Student identity retains historical enrollments. | Education Student; Padars duplicate Student/User identity hook. | PARTIAL | E-CODE, E-STATIC; Frappe test blocked. | Test duplicate identity and historical reads with synthetic data. |
| S09 | Required | Staff can register a new student through Student and annual enrollment. | Education Student/Program Enrollment plus Padars school validation. | PARTIAL | E-CODE; no full browser journey. | Verify Student → User → Enrollment → Group journey. |
| S10 | Required | CSV/Excel import previews duplicates/errors and imports bounded partial-success results. | No implementation currently exists; should use Frappe Data Import with Padars orchestration. | MISSING | No import API/page/result model. | Define import contract, implement preview/execute/retry, and test mixed rows. |
| S11 | Required | Returning student receives a new annual enrollment without a duplicate Student. | Education Program Enrollment; Padars identity and school checks. | PARTIAL | E-CODE; no browser/database execution. | Add returning-student workflow and regression test. |
| S12 | Required | User creation/linking is deterministic, secure, activated by policy, and exposes no guessed password. | Education user creation; Padars identity check and mock Moodle-user request. | PARTIAL | E-CODE, E-STATIC; no account policy test. | Confirm activation/welcome-email policy and test disabled/duplicate users. |
| S13 | Required | Student can log into Frappe and see only authorized TMS information. | Education Student Portal plus Padars school permissions. | BLOCKED | No running Desk/Portal or browser harness. | Configure portal access and run student-role browser tests. |
| S14 | Required | Frappe identity can open Moodle through a separate secure SSO flow. | No SSO adapter or target contract is implemented. | MISSING | E-LIVE unavailable. | Obtain SSO contract/sandbox and implement separately from provisioning. |
| S17 | Required | Instructor/User records and school teacher access are defined. | Education Instructor/User; Padars instructor membership validation and filters. | PARTIAL | E-CODE, E-STATIC; no role test. | Create teacher dataset and verify direct/list/API access. |
| S18 | Required | Student Group represents school/year/program/class membership without cross-school students. | Education Student Group with Padars school field and roster validation. | PARTIAL | E-CODE; Frappe tests blocked. | Run two-school roster and membership tests. |
| S19 | Required | Course catalog remains distinct from annual course delivery. | Education Course as source of truth; Padars Offering as annual instance. | PARTIAL | E-CODE, architecture docs. | Verify catalog/offering relations on staging. |
| S20 | Required | One annual offering identifies school, year, course, group, and offering key. | Padars `School Course Offering` controller and unique business validation. | PARTIAL | Existing Frappe test present; not executed. | Run migration and duplicate/cross-year tests. |
| S21 | Required | A valid instructor is assigned to the correct school offering. | Offering validation against active instructor membership. | PARTIAL | E-CODE; no database test. | Execute teacher assignment and unauthorized mutation tests. |
| S22 | Required | Students enroll in the correct annual course/group without duplicate Course Enrollment records. | Education Course Enrollment; Student Group validation; Padars offering boundary. | PARTIAL | E-CODE; no end-to-end enrollment orchestration. | Add offering-to-enrollment service and test duplicate prevention. |
| S23 | Conditional/manual | Optional manual schedule supports minimum date/time/teacher visibility without automatic timetable generation. | Education Course Schedule plus optional Padars offering field and filter. | PARTIAL | E-CODE, E-STATIC; no browser test. | Verify only if the pilot requires manual scheduling. |
| S26 | Required | School tenant is created or found through verified MuTMS APIs and mapped durably. | Padars tenant operation and mock adapter; live adapter absent. | BLOCKED | E-LIVE unavailable. | Verify `tool_mutenancy_*` API and implement live adapter. |
| S27 | Required | Moodle user is created/found idempotently from a Frappe identity. | Padars User operation and mock mapping; live API absent. | BLOCKED | E-CODE, E-STATIC; E-LIVE unavailable. | Confirm `core_user_*` contract and run live duplicate test. |
| S28 | Required | User is allocated to the correct school tenant, including multi-school identity rules. | Mock operation carries school context; live allocation not implemented. | BLOCKED | E-LIVE unavailable. | Confirm `tool_mutenancy_allocate_user` semantics and test multi-school allocation. |
| S29 | Required | Course is created/reused in the correct tenant/category. | Padars Course Offering operation; mock tenant/course mappings. | BLOCKED | E-CODE, E-STATIC; category semantics unverified. | Confirm tenant/category relationship and live course test. |
| S30 | Required | Teacher receives the authorized Moodle role in the correct course. | No teacher enrollment orchestration/live role adapter. | MISSING | Only generic enrollment state model exists. | Implement role-aware enrollment service after API contract approval. |
| S31 | Required | Students receive correct Moodle course enrollment without duplicates. | LMS Enrollment State and mock reconciliation exist, but no automatic roster sync. | MISSING | No end-to-end enrollment test. | Build roster reconciliation and live contract tests. |
| S32 | Required | External IDs and current sync state are durable and observable. | Padars Mapping, Enrollment State, Sync Operation, monitor page. | PARTIAL | E-CODE, E-STATIC; no database/UI execution. | Verify mapping uniqueness and monitor authorization on staging. |
| S33 | Required | Queued operations are idempotent, retryable, recoverable after failure, and duplicate-free. | Padars idempotency keys, bounded retries, safe errors, stale-worker recovery. | PARTIAL | E-STATIC/mock contract; Frappe test not executed. | Run worker interruption/outage/retry tests on disposable site. |
| S34 | Required | Authorized TMS user can open the mapped Moodle course without exposing tokens. | No remote course URL/SSO contract; monitor opens local mapping only. | MISSING | E-LIVE unavailable. | Add authorized URL/SSO navigation after MuTMS contract approval. |
| S38 | Required | Student view combines identity, enrollments, class, and assessment history. | Education records plus Padars school context. | PARTIAL | E-CODE; no portal/report view. | Build authorized student record view and test historical access. |
| S39 | Required | Student files are private and school/role controlled. | Education File/attachments are not extended or tested by Padars. | BLOCKED | No file isolation test or staging site. | Define file policy and execute direct URL/report/file negative tests. |
| S40 | Required | Authorized staff can enter and validate in-person grades. | Education Assessment Plan/Result; Padars offering context checks. | PARTIAL | E-CODE; Frappe/browser tests blocked. | Verify score/grade rules and teacher permissions on staging. |
| S41 | Required | First- and second-term report cards are complete, Persian-ready, printable, and reviewable. | No Padars report-card publication service or snapshot model. | MISSING | No publication UI/API. | Approve term/report model and implement controlled publication. |
| S42 | Required | Annual report cards preserve prior-year history and final snapshots. | No annual publication/archive implementation. | MISSING | No archive/version tests. | Implement versioned snapshots without replacing Education grades. |
| S43 | Required | Grade approval, publication lock, and post-publication corrections are audited. | No Report Card Publication DocType/workflow. | MISSING | No workflow evidence. | Define approver roles, immutable versions, and correction audit. |
| S44 | Required | Student sees only their own authorized published results. | No Padars student result API/portal authorization layer. | MISSING | No student browser/API test. | Implement read-only published-result endpoint and negative tests. |
| S57 | Required | Admin sees actionable pending/failed operations and can retry safely. | LMS Synchronization Monitor, retry API, safe errors, stale-worker recovery. | PARTIAL | E-CODE, E-STATIC; no staging/UI test. | Execute role-based monitor and retry tests. |
| S58 | Required | Integration status page shows school/entity/operation/state/error/retry information. | Padars custom `lms-sync-monitor` page and shared status helpers. | PARTIAL | JavaScript syntax/smoke passed; no browser test. | Build assets and run desktop/mobile browser smoke tests. |
| S60 | Required | Persian labels, RTL layout, and Jalali display work while DB dates remain standard. | Translation-ready Padars strings, RTL CSS, Frappe localized date display. | PARTIAL | E-CODE, E-STATIC; no locale/browser test. | Test Persian locale, mixed identifiers, date filtering, and print output. |

## Matrix summary

- VERIFIED: 0
- PARTIAL: 23
- MISSING: 9
- BLOCKED: 7
- Conditional/manual: S23

The counts intentionally do not treat source inspection, syntax checks, or mock behavior as staging, live MuTMS, or end-to-end verification.
