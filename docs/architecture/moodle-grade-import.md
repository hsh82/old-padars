# Reviewed Moodle grades into Education

Moodle remains the owner of instructional grades. Padars records immutable source
snapshots, explicit item-to-criterion mappings and review decisions. Education
Assessment Result owns official academic marks, followed by the existing scheme
and immutable report-publication workflow. No grade is written back to Moodle.

## Configuration and review

A School Manager creates a Moodle Grade Mapping from a discovered snapshot,
selects the offering's submitted Assessment Plan and one of its native criteria,
and enters the displayed numeric Moodle grade-item ID. Numeric ranges are copied
from that immutable source; scale/outcome-based items are unsupported. The native
criterion maximum is the target scale. Decimal places (0–6) and Half Up/Half Even
rounding are explicit. Submission approves the mapping. One active mapping per
plan/criterion is enforced under the plan lock and a unique key. Retiring a
mapping requires a reason and retains its history; a replacement is a new record.
Scheme component weights remain in School Assessment Scheme, not these mappings.

Teachers with assigned grade-entry authority or managers open a source snapshot,
choose the submitted plan and preview an import. The preview checks current
student/enrollment/group access, latest successful source operation, latest
student snapshot, matching remote course context, approved mappings and unchanged
source/target ranges. Missing, hidden, stale, conflicting or unsupported grades
block import. An override is labelled Review Required and must be explicitly
accepted with a reason. No missing value becomes zero.

Normalized marks are `(raw - source_min)/(source_max - source_min)*target_max`,
using the approved rounding. Existing manual marks for unmapped criteria and the
teacher's comment are preserved. A criterion without a mapping or an explicit
existing manual mark blocks import, so partial data cannot create a seemingly
complete result. The dialog shows previous/proposed marks and requires a review
reason. Source discovery never approves a result.

## Integrity and provenance

Import locks offering → plan → existing result, rebuilds the preview and checks
its digest. Sources and approved mapping IDs, normalization, previous/proposed
marks, student and plan are retained in immutable Moodle Grade Review, with actor,
time, reason and result revision. The native grade-entry service writes only a
draft. If the audit write fails, marks roll back to the savepoint. Retrying the
same decision reuses its review when the result still agrees. A later edit needs
new source review; approved marks require the separate manager correction action.

Source capture uses the same offering lock, preventing concurrent snapshot
insertion during the import decision. Cross-connection stress testing remains a
release gate. Approved/published results are never overwritten by import. A
manager must create an amendment draft, approve a reviewed replacement mapping
when necessary, import into that draft and separately approve/publish corrections.
Old result, review and report-card snapshots remain intact.

Manager/teaching permissions scope mapping/source/review reads to the offering.
Only managers configure/retire mappings. Students and guardians see only separately
published report cards. The native forms provide a discovered-item table, mapping
configuration and reviewed draft-import action; the plan-criterion Link query
requires manager authorization and returns only the selected plan's criteria.
No generic criteria/User/system administration permission is added.

## Evidence and remaining gates

The full focused scheduling/assessment module passed 16 integration tests on
`padars-phase12-fresh.local`. The grade journey covers durable discovery,
normalization (16/20 to 80/100), preserving a manual 70, rollback after an audit
failure, teacher review, idempotency, manager approval, rejecting a changed range,
retiring/replacing a mapping, controlled amendment to 16/40 = 40/100, and retained
old results. Stale review and student-access negatives are covered. Fourteen
separate offline Moodle adapter contracts passed earlier.

Live Moodle grades, actual service capabilities, browser interaction, concurrent
imports/publications and full-school acceptance remain unverified. This milestone
is a focused implementation, not Phase 9 or product release approval.
