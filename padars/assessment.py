"""Integrity checks for Education's official assessment results."""

import math

import frappe
from frappe import _


@frappe.whitelist()
def get_assessment_details(assessment_plan):
	"""Expose plan criteria to the native form only within the caller's scope."""
	plan = frappe.get_doc("Assessment Plan", assessment_plan)
	plan.check_permission("read")
	return [{
		"assessment_criteria": row.assessment_criteria,
		"maximum_score": row.maximum_score,
		"docstatus": row.docstatus,
	} for row in plan.assessment_criteria]


@frappe.whitelist()
def get_assessment_students(assessment_plan, student_group):
	"""Return the native tool roster only for a plan within grade-entry scope."""
	plan = frappe.get_doc("Assessment Plan", assessment_plan)
	plan.check_permission("read")
	if plan.docstatus != 1 or plan.student_group != student_group:
		frappe.throw(_("Choose the submitted Assessment Plan's own Student Group."), frappe.PermissionError)
	from padars.scheduling import validate_assessment_result_relationships
	students = frappe.get_all("Student Group Student", filters={"parent": student_group, "active": 1},
		fields=["student", "student_name"], order_by="group_roll_number asc")
	for student in students:
		candidate = frappe.new_doc("Assessment Result")
		candidate.assessment_plan = plan.name
		candidate.student = student.student
		validate_assessment_result_relationships(candidate)
		candidate.check_permission("create")
		results = frappe.get_all("Assessment Result", filters={
			"assessment_plan": plan.name, "student": student.student, "docstatus": ["!=", 2],
		}, pluck="name")
		if len(results) > 1:
			frappe.throw(_("Multiple assessment results exist; resolve the conflict before entering marks."))
		student.assessment_details = None
		if results:
			result = frappe.get_doc("Assessment Result", results[0])
			result.check_permission("read")
			student.assessment_details = {row.assessment_criteria: [str(row.score), row.grade] for row in result.details}
			student.assessment_details.update({"total_score": [str(result.total_score), result.grade], "comment": result.comment})
			student.docstatus = result.docstatus
			student.name = result.name
	return students


@frappe.whitelist(methods=["POST"])
def mark_assessment_result(assessment_plan, scores):
	"""Create or update one permitted draft Education result for a plan."""
	if isinstance(scores, str):
		scores = frappe.parse_json(scores)
	if not isinstance(scores, dict) or not isinstance(scores.get("assessment_details"), dict):
		frappe.throw(_("Provide a student and scores for the assessment criteria."))
	plan = frappe.get_doc("Assessment Plan", assessment_plan)
	plan.check_permission("read")
	if plan.docstatus != 1:
		frappe.throw(_("The Assessment Plan must be submitted."))
	student = scores.get("student")
	if not student or not frappe.db.exists("Student Group Student", {
		"parent": plan.student_group, "student": student, "active": 1,
	}):
		frappe.throw(_("The student must be an active member of this assessment group."), frappe.PermissionError)
	# Serialize competing result creation for this plan, including requests for
	# the same student from different sessions.
	frappe.db.sql("select name from `tabAssessment Plan` where name=%s for update", plan.name)
	existing = frappe.get_all("Assessment Result", filters={
		"assessment_plan": plan.name, "student": student, "docstatus": ["!=", 2],
	}, pluck="name")
	if len(existing) > 1:
		frappe.throw(_("Multiple assessment results exist; resolve the conflict before entering marks."))
	if existing:
		result = frappe.get_doc("Assessment Result", existing[0])
		result.check_permission("write")
		if result.docstatus != 0:
			frappe.throw(_("Submitted assessment results require an authorized correction workflow."))
	else:
		result = frappe.new_doc("Assessment Result")
		result.assessment_plan = plan.name
		result.student = student
		from padars.scheduling import validate_assessment_result_relationships
		validate_assessment_result_relationships(result)
		result.check_permission("create")
	result.comment = scores.get("comment") or ""
	result.set("details", [{"assessment_criteria": key, "score": value}
		for key, value in scores["assessment_details"].items()])
	result.save()
	return {"name": result.name, "student": result.student, "total_score": result.total_score,
		"grade": result.grade, "details": {row.assessment_criteria: row.grade for row in result.details}}


def validate_result_scores(doc, method=None):
	"""Use the plan's criteria and maxima as the sole basis for entered scores."""
	if not doc.assessment_plan:
		frappe.throw(_("Choose an Assessment Plan before entering scores."))
	criteria = frappe.get_all("Assessment Plan Criteria", filters={
		"parent": doc.assessment_plan, "parenttype": "Assessment Plan", "parentfield": "assessment_criteria",
	}, fields=["assessment_criteria", "maximum_score"])
	maxima = {}
	for row in criteria:
		maximum = float(row.maximum_score or 0)
		if not row.assessment_criteria or row.assessment_criteria in maxima or not math.isfinite(maximum) or maximum <= 0:
			frappe.throw(_("The Assessment Plan must have unique criteria with positive finite maximum scores."))
		maxima[row.assessment_criteria] = maximum
	if not maxima:
		frappe.throw(_("The Assessment Plan must contain assessment criteria."))
	seen = set()
	for row in doc.details:
		criterion = row.assessment_criteria
		if criterion not in maxima or criterion in seen:
			frappe.throw(_("Each Assessment Result criterion must appear exactly once in its Assessment Plan."))
		seen.add(criterion)
		score = float(row.score or 0)
		if not math.isfinite(score) or score < 0 or score > maxima[criterion]:
			frappe.throw(_("Scores must be between zero and the criterion maximum."))
	if seen != set(maxima):
		frappe.throw(_("Enter a score for each Assessment Plan criterion."))
	doc.maximum_score = sum(maxima.values())
