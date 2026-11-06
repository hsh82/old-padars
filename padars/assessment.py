"""Integrity checks for Education's official assessment results."""

import math

import frappe
from frappe import _


@frappe.whitelist()
def preview_approved_results(student, program, academic_year, academic_term=None):
	"""Preview submitted Education results for a student's school enrollment."""
	from padars.permissions import is_school_manager
	from padars.school_context import get_primary_school

	school = get_primary_school()
	if not school or not is_school_manager(school):
		frappe.throw(_("Only a School Manager can review results for publication."), frappe.PermissionError)
	if academic_term and frappe.db.get_value("Academic Term", academic_term, "academic_year") != academic_year:
		frappe.throw(_("The Academic Term must belong to the selected Academic Year."))
	if not frappe.db.exists("Program Enrollment", {
		"student": student, "program": program, "academic_year": academic_year,
		"padars_school": school, "docstatus": 1,
	}):
		frappe.throw(_("The student needs a submitted Program Enrollment for this school, program and year."))
	filters = {"student": student, "program": program, "academic_year": academic_year,
		"padars_school": school, "docstatus": 1}
	if academic_term:
		filters["academic_term"] = academic_term
	draft_filters = {**filters, "docstatus": 0}
	draft_count = len(_get_all_permitted_names("Assessment Result", draft_filters))
	rows = []
	start = 0
	while True:
		batch = frappe.get_list("Assessment Result", filters=filters, pluck="name",
			order_by="name asc", start=start, page_length=200)
		for name in batch:
			result = frappe.get_doc("Assessment Result", name)
			result.check_permission("read")
			rows.append({"result": result.name, "assessment_plan": result.assessment_plan,
				"course": result.course, "academic_term": result.academic_term,
				"grading_scale": result.grading_scale, "maximum_score": result.maximum_score,
				"total_score": result.total_score, "grade": result.grade,
				"criteria": [{"name": row.assessment_criteria, "score": row.score,
					"maximum_score": row.maximum_score, "grade": row.grade} for row in result.details]})
		if len(batch) < 200:
			break
		start += len(batch)
	groups = frappe.get_all("Student Group Student", filters={
		"student": student, "parenttype": "Student Group", "parentfield": "students",
	}, pluck="parent")
	offering_names = _get_all_permitted_names("School Course Offering", {
		"school": school, "program": program, "academic_year": academic_year,
		"student_group": ["in", groups],
	}) if groups else []
	offering_courses = {frappe.db.get_value("School Course Offering", name, "course") for name in offering_names}
	result_courses = {row["course"] for row in rows}
	return {"school": school, "student": student, "program": program,
		"academic_year": academic_year, "academic_term": academic_term, "results": rows,
		"draft_count": draft_count, "courses_without_approved_results": sorted(offering_courses - result_courses)}


def _get_all_permitted_names(doctype, filters):
	names = []
	while True:
		batch = frappe.get_list(doctype, filters=filters, pluck="name", order_by="name asc",
			start=len(names), page_length=200)
		names.extend(batch)
		if len(batch) < 200:
			return names


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
			student.modified = str(result.modified)
			student.correction_pending = bool(result.amended_from and result.docstatus == 0)
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
		result = frappe.get_doc("Assessment Result", existing[0], for_update=True)
		result.check_permission("write")
		if result.docstatus != 0:
			frappe.throw(_("Submitted assessment results require an authorized correction workflow."))
		if str(scores.get("expected_modified") or "") != str(result.modified):
			frappe.throw(_("This assessment result changed after it was loaded. Reload before saving marks."), frappe.TimestampMismatchError)
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
		"modified": str(result.modified), "grade": result.grade, "details": {row.assessment_criteria: row.grade for row in result.details}}


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
		row.score = score  # Education compares numeric values before ORM field coercion.
	if seen != set(maxima):
		frappe.throw(_("Enter a score for each Assessment Plan criterion."))
	doc.maximum_score = sum(maxima.values())


def validate_result_uniqueness(doc, method=None):
	"""Serialize direct and API result writes against the same Education plan."""
	if not doc.assessment_plan or not doc.student:
		return
	if not frappe.db.sql("select name from `tabAssessment Plan` where name=%s for update", doc.assessment_plan):
		frappe.throw(_("Choose an existing Assessment Plan."))
	duplicates = frappe.db.sql("""
		select name from `tabAssessment Result`
		where assessment_plan=%s and student=%s and docstatus < 2 and name != %s
		limit 1 for update
	""", (doc.assessment_plan, doc.student, doc.name or ""))
	if duplicates:
		frappe.throw(_("An active Assessment Result already exists for this student and plan."))


def validate_result_ready_for_approval(doc, method=None):
	if frappe.db.get_value("Assessment Plan", doc.assessment_plan, "docstatus") != 1:
		frappe.throw(_("An Assessment Result can be approved only for a submitted Assessment Plan."))


def validate_result_correction(doc, method=None):
	from frappe.utils import get_datetime
	old = doc.get_doc_before_save()
	metadata = ("padars_correction_reason", "padars_corrected_by", "padars_correction_at")
	if old and old.amended_from != doc.amended_from:
		frappe.throw(_("An assessment correction's source cannot be changed."))
	def normalized(record, field):
		value = record.get(field)
		return get_datetime(value) if field == "padars_correction_at" and value else value
	if old and any(normalized(old, field) != normalized(doc, field) for field in metadata):
		frappe.throw(_("Recorded correction reason and reviewer cannot be changed."))
	if not doc.amended_from:
		if any(doc.get(field) for field in metadata):
			frappe.throw(_("Correction metadata is valid only on a controlled correction."))
		return
	from padars.permissions import is_school_manager
	from padars.school_context import get_primary_school
	if not is_school_manager(get_primary_school()):
		frappe.throw(_("Only a School Manager can change a result correction."), frappe.PermissionError)
	source = frappe.db.get_value("Assessment Result", doc.amended_from,
		["docstatus", "student", "assessment_plan"], as_dict=True)
	if not source or (source.docstatus, source.student, source.assessment_plan) != (2, doc.student, doc.assessment_plan):
		frappe.throw(_("The correction must reference a cancelled result for the same student and plan."))
	if doc.is_new() and frappe.flags.get("padars_result_correction") != doc.amended_from:
		frappe.throw(_("Start a correction through the reviewed result action."), frappe.PermissionError)
	if not doc.padars_correction_reason or not doc.padars_corrected_by or not doc.padars_correction_at:
		frappe.throw(_("A correction must retain its reason, reviewer and timestamp."))


def validate_result_cancellation(doc, method=None):
	from padars.permissions import is_platform_admin
	if not is_platform_admin() and frappe.flags.get("padars_result_correction") != doc.name:
		frappe.throw(_("Approved results can be cancelled only through a controlled correction."), frappe.PermissionError)


def protect_result_history(doc, method=None):
	if doc.docstatus or doc.amended_from:
		frappe.throw(_("Approved and corrected assessment history cannot be deleted."), frappe.PermissionError)


@frappe.whitelist(methods=["POST"])
def correct_assessment_result(result, expected_modified, reason):
	from padars.permissions import is_school_manager
	from padars.school_context import get_primary_school
	from frappe.utils import escape_html
	from frappe.utils import now_datetime
	school = get_primary_school()
	if not is_school_manager(school):
		frappe.throw(_("Only a School Manager can start a result correction."), frappe.PermissionError)
	if not isinstance(reason, str) or not reason.strip():
		frappe.throw(_("A correction reason is required."))
	plan = frappe.db.get_value("Assessment Result", result, "assessment_plan")
	if not plan:
		frappe.throw(_("Choose an existing Assessment Result."))
	frappe.db.sql("select name from `tabAssessment Plan` where name=%s for update", plan)
	source = frappe.get_doc("Assessment Result", result, for_update=True)
	source.check_permission("read")
	if source.padars_school != school:
		frappe.throw(_("The result belongs to another School."), frappe.PermissionError)
	if not frappe.has_permission("Assessment Result", "approve_grade", doc=source):
		frappe.throw(_("Grade approval permission is required for corrections."), frappe.PermissionError)
	if source.docstatus != 1 or str(source.modified) != str(expected_modified):
		frappe.throw(_("The approved result changed after review. Reload before starting a correction."), frappe.TimestampMismatchError)
	amended = frappe.copy_doc(source)
	amended.docstatus = 0
	amended.amended_from = source.name
	amended.owner = frappe.session.user
	amended.padars_correction_reason = reason.strip()
	amended.padars_corrected_by = frappe.session.user
	amended.padars_correction_at = now_datetime()
	amended.flags.ignore_permissions = False
	point = "padars_correction_" + frappe.generate_hash(length=8)
	frappe.db.savepoint(point)
	previous_flag = frappe.flags.get("padars_result_correction")
	frappe.flags.padars_result_correction = source.name
	try:
		source.flags.ignore_permissions = True
		source.cancel()
		amended.insert()
		source.add_comment("Info", _("Correction draft {0}. Reason: {1}").format(escape_html(amended.name), escape_html(reason.strip())))
	except Exception:
		frappe.db.rollback(save_point=point)
		raise
	finally:
		frappe.flags.padars_result_correction = previous_flag
	return {"name": amended.name, "modified": str(amended.modified), "amended_from": source.name}
