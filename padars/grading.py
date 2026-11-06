"""Explicit school assessment configuration over Education's approved marks."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, ROUND_HALF_EVEN
import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from padars.permissions import is_school_manager
from padars.school_context import get_primary_school


def number(value):
	try:
		value = Decimal(str(value))
	except (InvalidOperation, ValueError, TypeError):
		frappe.throw(_("Assessment configuration and scores must be numeric."))
	if not value.is_finite():
		frappe.throw(_("Assessment configuration and scores must be finite."))
	return value


class SchoolAssessmentScheme(Document):
	def _offering(self):
		offering = frappe.get_doc("School Course Offering", self.course_offering)
		if offering.school != get_primary_school() or not is_school_manager(offering.school):
			frappe.throw(_("Only this school's manager can configure assessment schemes."), frappe.PermissionError)
		offering.check_permission("read")
		return offering

	def before_insert(self):
		if self.docstatus != 0:
			frappe.throw(_("New assessment schemes must start as drafts."))
		offering = self._offering()
		frappe.db.sql("select name from `tabSchool Course Offering` where name=%s for update", offering.name)
		versions = frappe.db.sql("""select version from `tabSchool Assessment Scheme`
			where course_offering=%s and coalesce(academic_term,'')=%s
			order by version desc limit 1 for update""", (offering.name, self.academic_term or ""))
		self.version = int(versions[0][0]) + 1 if versions else 1
		self.school = offering.school
		import hashlib
		self.version_key = hashlib.sha256(f"{offering.name}\0{self.academic_term or ''}\0{self.version}".encode()).hexdigest()
		self.approved_by = self.approved_at = None
		self.scale_snapshot = None

	def validate(self):
		offering = self._offering()
		if self.school != offering.school:
			frappe.throw(_("The assessment scheme School must match the Course Offering."))
		old = self.get_doc_before_save()
		if old:
			if old.docstatus == 1:
				frappe.throw(_("Approved assessment schemes are immutable; create a new version."))
			if any(old.get(k) != self.get(k) for k in ("school", "course_offering", "academic_term", "version", "version_key")):
				frappe.throw(_("Saved scheme context and version cannot change."))
			if any(self.get(k) != old.get(k) for k in ("approved_by", "approved_at", "scale_snapshot")):
				frappe.throw(_("Approval metadata is assigned on submission."))
		if self.academic_term and frappe.db.get_value("Academic Term", self.academic_term, "academic_year") != offering.academic_year:
			frappe.throw(_("The scheme term must belong to the offering's Academic Year."))
		if number(self.output_maximum) <= 0 or int(self.decimal_places or 0) not in range(7):
			frappe.throw(_("Set a positive output maximum and 0–6 decimal places."))
		if self.rounding_mode not in {"Half Up", "Half Even"}:
			frappe.throw(_("Choose an explicit supported rounding mode."))
		if frappe.db.get_value("Grading Scale", self.grading_scale, "docstatus") != 1:
			frappe.throw(_("Choose a submitted Education Grading Scale."))
		seen, total = set(), Decimal(0)
		for row in self.components:
			key = (row.assessment_plan, row.assessment_criteria)
			if key in seen or number(row.weight) <= 0:
				frappe.throw(_("Assessment components must be unique with positive weights."))
			seen.add(key)
			total += number(row.weight)
			plan = frappe.get_doc("Assessment Plan", row.assessment_plan)
			plan.check_permission("read")
			if plan.docstatus != 1 or plan.padars_course_offering != offering.name or plan.padars_school != offering.school:
				frappe.throw(_("Every component must use a submitted plan for this Course Offering."))
			if self.academic_term and plan.academic_term != self.academic_term:
				frappe.throw(_("Every component must use the scheme's Academic Term."))
			criteria = [c for c in plan.assessment_criteria if c.assessment_criteria == row.assessment_criteria]
			if len(criteria) != 1 or number(criteria[0].maximum_score) <= 0:
				frappe.throw(_("Each component must select a valid positive-maximum plan criterion."))
		if not seen or total != Decimal(100):
			frappe.throw(_("Assessment component weights must total 100 percent."))

	def before_submit(self):
		self._offering()
		self.approved_by = frappe.session.user
		self.approved_at = now_datetime()
		intervals = frappe.get_all("Grading Scale Interval", filters={"parent": self.grading_scale}, fields=["threshold", "grade_code"])
		if not intervals or any(not r.grade_code or number(r.threshold) < 0 or number(r.threshold) > 100 for r in intervals):
			frappe.throw(_("The grading scale needs valid grade intervals from zero through 100."))
		if len({number(r.threshold) for r in intervals}) != len(intervals) or not any(number(r.threshold) == 0 for r in intervals):
			frappe.throw(_("The grading scale needs unique thresholds and a zero threshold."))
		self.scale_snapshot = json.dumps([{ "threshold": str(number(r.threshold)), "grade_code": r.grade_code} for r in intervals])

	def before_update_after_submit(self):
		frappe.throw(_("Approved assessment schemes are immutable; create a new version."))

	def before_cancel(self):
		frappe.throw(_("Approved schemes are retained; create a new version."))

	def on_trash(self):
		self._offering()
		if self.docstatus:
			frappe.throw(_("Approved assessment schemes cannot be deleted."))


@frappe.whitelist()
def calculate_scheme(scheme, student):
	scheme = frappe.get_doc("School Assessment Scheme", scheme)
	scheme.check_permission("read")
	offering = scheme._offering()
	if scheme.docstatus != 1:
		frappe.throw(_("Approve the assessment scheme before calculating results."))
	if not frappe.db.exists("Program Enrollment", {"student": student, "program": offering.program,
		"academic_year": offering.academic_year, "padars_school": offering.school, "docstatus": 1}):
		frappe.throw(_("The student needs a submitted enrollment matching this scheme."))
	total, evidence = Decimal(0), []
	results = {}
	for component in scheme.components:
		if component.assessment_plan not in results:
			names = frappe.get_list("Assessment Result", filters={"student": student,
				"assessment_plan": component.assessment_plan, "docstatus": 1}, pluck="name", page_length=2)
			if len(names) != 1:
				frappe.throw(_("Each scheme plan requires exactly one approved result for this student."))
			result = frappe.get_doc("Assessment Result", names[0])
			result.check_permission("read")
			if result.padars_course_offering != offering.name or result.padars_school != offering.school:
				frappe.throw(_("Assessment Result context does not match the scheme."))
			results[component.assessment_plan] = result
		result = results[component.assessment_plan]
		rows = [r for r in result.details if r.assessment_criteria == component.assessment_criteria]
		if len(rows) != 1:
			frappe.throw(_("The approved result is missing a unique scheme criterion."))
		score, maximum, weight = number(rows[0].score), number(rows[0].maximum_score), number(component.weight)
		if maximum <= 0 or score < 0 or score > maximum:
			frappe.throw(_("An approved source score is outside its valid range."))
		total += score / maximum * weight
		evidence.append({"result": result.name, "modified": str(result.modified),
			"criterion": component.assessment_criteria, "score": str(score), "maximum": str(maximum), "weight": str(weight)})
	quantum = Decimal(1).scaleb(-int(scheme.decimal_places or 0))
	output = (total / 100 * number(scheme.output_maximum)).quantize(quantum,
		rounding=ROUND_HALF_UP if scheme.rounding_mode == "Half Up" else ROUND_HALF_EVEN)
	intervals = [frappe._dict(row) for row in json.loads(scheme.scale_snapshot)]
	grade = next((r.grade_code for r in sorted(intervals, key=lambda r: number(r.threshold), reverse=True) if total >= number(r.threshold)), "")
	return {"scheme": scheme.name, "version": scheme.version, "student": student,
		"score": str(output), "maximum": str(scheme.output_maximum), "percentage": str(total), "grade": grade,
		"rounding_mode": scheme.rounding_mode, "decimal_places": scheme.decimal_places,
		"grade_intervals": json.loads(scheme.scale_snapshot), "sources": evidence}
