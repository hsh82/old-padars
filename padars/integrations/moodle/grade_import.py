"""Explicit Moodle item mappings and audited review into Education drafts."""

import hashlib
import json
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from padars.integrations.moodle.grades import _can_read_offering, query_conditions
from padars.permissions_site import is_school_manager
from padars.school_context import get_primary_school


def _hash(data):
	return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _manager(school):
	if school != get_primary_school() or not is_school_manager(school):
		frappe.throw(_("Only this School's Manager can configure grade mappings."), frappe.PermissionError)


class MoodleGradeMapping(Document):
	def validate(self):
		if self.is_new() and self.docstatus != 0:
			frappe.throw(_("A new Moodle grade mapping must start as a draft."))
		offering = frappe.get_doc("School Course Offering", self.course_offering)
		_manager(offering.school)
		self.school = offering.school
		plan = frappe.get_doc("Assessment Plan", self.assessment_plan)
		if plan.docstatus != 1 or plan.padars_course_offering != offering.name:
			frappe.throw(_("Choose a submitted Assessment Plan for this Course Offering."))
		criteria = [row for row in plan.assessment_criteria if row.assessment_criteria == self.assessment_criteria]
		if len(criteria) != 1:
			frappe.throw(_("The criterion must belong to the selected Assessment Plan."))
		snapshot = frappe.get_doc("Moodle Grade Snapshot", self.source_snapshot)
		if snapshot.school != self.school or snapshot.course_offering != offering.name:
			frappe.throw(_("The grade source must belong to this School and offering."))
		items = [row for row in json.loads(snapshot.items) if row["id"] == self.grade_item]
		if len(items) != 1:
			frappe.throw(_("Select a discovered Moodle grade item identifier."))
		item = items[0]
		if item["scaleid"] or item["outcomeid"] or item["grademin"] is None or item["grademax"] is None or Decimal(item["grademax"]) <= Decimal(item["grademin"]):
			frappe.throw(_("Only numeric grade items with a positive explicit range can be mapped."))
		if self.decimal_places is None or not 0 <= int(self.decimal_places) <= 6 or self.rounding_mode not in {"Half Up", "Half Even"}:
			frappe.throw(_("Choose zero to six decimal places and an explicit supported rounding mode."))
		self.item_title, self.remote_context, self.remote_course = item["name"], snapshot.remote_context, snapshot.remote_course
		self.source_minimum, self.source_maximum = item["grademin"], item["grademax"]
		self.target_maximum = str(criteria[0].maximum_score)
		frappe.db.sql("select name from `tabAssessment Plan` where name=%s for update", plan.name)
		self.active_key = _hash([plan.name, self.assessment_criteria]) if self.docstatus < 2 else None
		if not self.is_new() and self.docstatus == 2:
			self.active_key = None

	def before_cancel(self):
		_manager(self.school)
		if not (self.retirement_reason or "").strip():
			frappe.throw(_("Record a reason before retiring this grade mapping."))

	def on_cancel(self):
		self.db_set("active_key", None, update_modified=False)

	def on_trash(self):
		if self.docstatus != 0:
			frappe.throw(_("Approved grade mapping history cannot be deleted."), frappe.PermissionError)


class MoodleGradeReview(Document):
	def validate(self):
		if not self.is_new() or not frappe.flags.get("padars_grade_review"):
			frappe.throw(_("Grade review history is immutable and service-created."), frappe.PermissionError)

	def on_trash(self):
		frappe.throw(_("Grade review history cannot be deleted."), frappe.PermissionError)


def mapping_query_conditions(user=None):
	return query_conditions(user).replace("`tabMoodle Grade Snapshot`", "`tabMoodle Grade Mapping`")


def review_query_conditions(user=None):
	return query_conditions(user).replace("`tabMoodle Grade Snapshot`", "`tabMoodle Grade Review`")


def review_permission(doc, ptype, user=None, **kwargs):
	return ptype in {"read", "select"} and doc.school == get_primary_school() and _can_read_offering(doc.course_offering, user)


def mapping_permission(doc, ptype, user=None, **kwargs):
	if ptype in {"read", "select"}:
		return review_permission(doc, ptype, user)
	school = doc.school or frappe.db.get_value("School Course Offering", doc.course_offering, "school")
	return bool(school == get_primary_school() and is_school_manager(school, user))


def _preview(source_snapshot, assessment_plan, lock=False):
	snapshot = frappe.get_doc("Moodle Grade Snapshot", source_snapshot)
	snapshot.check_permission("read")
	plan = frappe.get_doc("Assessment Plan", assessment_plan)
	plan.check_permission("read")
	if plan.docstatus != 1 or plan.padars_course_offering != snapshot.course_offering or plan.padars_school != snapshot.school:
		frappe.throw(_("Select a submitted Assessment Plan for this grade source's School and offering."))
	if lock:
		frappe.db.sql("select name from `tabSchool Course Offering` where name=%s for update", snapshot.course_offering)
		frappe.db.sql("select name from `tabAssessment Plan` where name=%s for update", plan.name)
	from padars.scheduling import validate_assessment_result_relationships
	candidate = frappe.new_doc("Assessment Result")
	candidate.assessment_plan, candidate.student = plan.name, snapshot.student
	validate_assessment_result_relationships(candidate)
	candidate.check_permission("create")
	if not frappe.has_permission("Assessment Result", "enter_grade", candidate):
		frappe.throw(_("You are not allowed to enter grades for this assessment."), frappe.PermissionError)
	latest = frappe.db.get_value("Moodle Grade Snapshot", {"course_offering": snapshot.course_offering,
		"student": snapshot.student}, "name", order_by="observed_at desc, creation desc")
	operation = frappe.db.get_value("LMS Sync Operation", {"target_doctype": "School Course Offering",
		"target_name": snapshot.course_offering, "operation_type": "Read Grades"}, ["name", "state"], as_dict=True, order_by="creation desc")
	issues = []
	if latest != snapshot.name or not operation or operation.name != snapshot.source_operation or operation.state != "Succeeded":
		issues.append(_("Fetch the latest successful grade sources before reviewing this import."))
	names = frappe.get_all("Assessment Result", filters={"student": snapshot.student,
		"assessment_plan": plan.name, "docstatus": ["!=", 2]}, pluck="name")
	if len(names) > 1:
		frappe.throw(_("Resolve duplicate Education results before importing grades."))
	result = frappe.get_doc("Assessment Result", names[0], for_update=lock) if names else None
	if result:
		result.check_permission("read")
		if result.docstatus == 0:
			result.check_permission("write")
		if result.docstatus != 0:
			issues.append(_("This Education result is approved. Use its controlled correction workflow first."))
	previous = {row.assessment_criteria: str(row.score) for row in result.details} if result else {}
	scores, sources = {}, []
	items = {row["id"]: row for row in json.loads(snapshot.items)}
	mappings = frappe.get_all("Moodle Grade Mapping", filters={"assessment_plan": plan.name, "docstatus": 1}, pluck="name")
	by_criterion = {}
	for name in mappings:
		mapping = frappe.get_doc("Moodle Grade Mapping", name)
		if mapping.assessment_criteria in by_criterion:
			frappe.throw(_("Resolve duplicate approved mappings before importing grades."))
		by_criterion[mapping.assessment_criteria] = mapping
	for criterion in plan.assessment_criteria:
		key = criterion.assessment_criteria
		mapping = by_criterion.get(key)
		if not mapping:
			if key in previous:
				scores[key] = previous[key]
			else:
				issues.append(_("An assessment criterion has no approved mapping or existing manual score."))
			continue
		item = items.get(mapping.grade_item)
		if mapping.remote_context != snapshot.remote_context or mapping.remote_course != snapshot.remote_course or not item:
			issues.append(_("A mapped grade item or its remote course context is missing."))
			continue
		if item["status"] not in {"Ready", "Review Required"}:
			issues.append(_("A mapped Moodle grade is missing, unavailable, conflicting or unsupported."))
			continue
		if Decimal(mapping.source_minimum) != Decimal(item["grademin"]) or Decimal(mapping.source_maximum) != Decimal(item["grademax"]) or Decimal(mapping.target_maximum) != Decimal(str(criterion.maximum_score)):
			issues.append(_("A grade range changed. Retire and review the mapping before importing."))
			continue
		raw, low, high = Decimal(item["graderaw"]), Decimal(mapping.source_minimum), Decimal(mapping.source_maximum)
		normalized = ((raw - low) / (high - low) * Decimal(mapping.target_maximum)).quantize(
			Decimal(1).scaleb(-mapping.decimal_places), rounding=ROUND_HALF_EVEN if mapping.rounding_mode == "Half Even" else ROUND_HALF_UP)
		scores[key] = str(normalized)
		sources.append({"mapping": mapping.name, "criterion": key, "item": item,
			"target_maximum": mapping.target_maximum, "score": str(normalized),
			"rounding_mode": mapping.rounding_mode, "decimal_places": mapping.decimal_places})
	if not sources:
		issues.append(_("At least one approved numeric Moodle mapping is required."))
	data = {"source_snapshot": snapshot.name, "source_digest": snapshot.payload_digest,
		"school": snapshot.school, "course_offering": snapshot.course_offering, "student": snapshot.student,
		"assessment_plan": plan.name, "sources": sources, "scores": scores, "previous": previous,
		"result": result.name if result else None, "expected_modified": str(result.modified) if result else None,
		"issues": issues, "ready": not issues}
	data["import_key"] = _hash({key: data[key] for key in ("source_snapshot", "source_digest", "assessment_plan", "scores", "sources")})
	data["digest"] = _hash(data)
	return data


@frappe.whitelist()
def preview_grade_import(source_snapshot, assessment_plan):
	return _preview(source_snapshot, assessment_plan)


@frappe.whitelist(methods=["POST"])
def apply_grade_import(source_snapshot, assessment_plan, expected_digest, reason):
	if not isinstance(reason, str) or not reason.strip():
		frappe.throw(_("Record why these instructional grades are accepted."))
	preview = _preview(source_snapshot, assessment_plan, lock=True)
	existing = frappe.db.get_value("Moodle Grade Review", {"import_key": preview["import_key"]}, "name")
	if existing:
		review = frappe.get_doc("Moodle Grade Review", existing)
		result = frappe.get_doc("Assessment Result", review.assessment_result)
		current = {row.assessment_criteria: Decimal(str(row.score)) for row in result.details}
		if result.docstatus < 2 and current == {key: Decimal(value) for key, value in preview["scores"].items()}:
			return {"review": review.name, "result": result.name, "already_applied": True}
		frappe.throw(_("This source was already imported and the result subsequently changed. Fetch and review new sources."))
	if expected_digest != preview["digest"]:
		frappe.throw(_("Grade sources, mappings or Education marks changed. Preview again."), frappe.TimestampMismatchError)
	if not preview["ready"]:
		frappe.throw(_("Resolve the grade review issues before importing."))
	from padars.assessment import mark_assessment_result
	frappe.db.savepoint("padars_grade_review")
	old_flag = frappe.flags.get("padars_grade_review")
	try:
		comment = frappe.db.get_value("Assessment Result", preview["result"], "comment") if preview["result"] else ""
		result = mark_assessment_result(assessment_plan, {"student": preview["student"],
			"assessment_details": preview["scores"], "expected_modified": preview["expected_modified"], "comment": comment})
		frappe.flags.padars_grade_review = True
		review = frappe.get_doc({"doctype": "Moodle Grade Review", "school": preview["school"],
			"course_offering": preview["course_offering"], "source_snapshot": source_snapshot,
			"assessment_plan": assessment_plan, "student": preview["student"], "assessment_result": result["name"],
			"reviewed_by": frappe.session.user, "reviewed_at": now_datetime(), "review_reason": reason.strip(),
			"provenance": json.dumps(preview, sort_keys=True), "result_modified": result["modified"],
			"import_key": preview["import_key"]}).insert(ignore_permissions=True)
	except Exception:
		frappe.db.rollback(save_point="padars_grade_review")
		raise
	finally:
		frappe.flags.padars_grade_review = old_flag
	return {"review": review.name, "result": result["name"], "already_applied": False}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def search_plan_criteria(doctype, txt, searchfield, start, page_len, filters):
	filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
	plan = frappe.get_doc("Assessment Plan", filters.get("assessment_plan"))
	plan.check_permission("read")
	_manager(plan.padars_school)
	if plan.docstatus != 1:
		frappe.throw(_("Choose a submitted Assessment Plan."))
	criteria = [row.assessment_criteria for row in plan.assessment_criteria]
	return frappe.get_all("Assessment Criteria", filters={"name": ["in", criteria],
		"assessment_criteria": ["like", f"%{txt}%"]}, fields=["name", "assessment_criteria"],
		as_list=True, start=max(int(start), 0), page_length=min(max(int(page_len), 1), 50))
