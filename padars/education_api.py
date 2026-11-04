"""Security boundaries for Education RPC endpoints used in a shared Padars site.

Education endpoints below pre-date Padars school tenancy and either query with
``get_all`` or accept arbitrary document names. We override them instead of
changing upstream code. Ambiguous workflows are closed until reviewed services
arrive in later work packages.
"""

import frappe
from frappe import _

from padars.permissions import can_manage_school, get_teacher_instructors


def _deny_unsupported(action):
	frappe.throw(
		_("{0} is unavailable until the school-aware Padars workflow is configured.").format(action),
		frappe.PermissionError,
	)


def _group_school(student_group):
	if not student_group:
		frappe.throw(_("Student Group is required."), frappe.PermissionError)
	school = frappe.db.get_value("Student Group", student_group, "padars_school")
	if not school:
		frappe.throw(_("Student Group has no Padars School context."), frappe.PermissionError)
	return school


def _can_read_group(student_group, user=None):
	user = user or frappe.session.user
	school = _group_school(student_group)
	if can_manage_school(school, user):
		return True
	instructors = get_teacher_instructors(user, school)
	return bool(instructors and frappe.db.exists(
		"Student Group Instructor", {"parent": student_group, "instructor": ["in", instructors]}
	))


def _require_group_manager(student_group):
	school = _group_school(student_group)
	if not can_manage_school(school):
		frappe.throw(_("You are not authorized to change this school's roster."), frappe.PermissionError)
	return school


@frappe.whitelist()
def get_school_group_students(student_group, include_inactive=0):
	"""Return one authorized group roster, including no unrelated students."""
	if not _can_read_group(student_group):
		frappe.throw(_("You are not authorized to access this student group."), frappe.PermissionError)
	filters = {"parent": student_group}
	if not frappe.utils.cint(include_inactive):
		filters["active"] = 1
	return frappe.get_all(
		"Student Group Student",
		fields=["student", "student_name", "group_roll_number", "active"],
		filters=filters,
		order_by="group_roll_number",
		ignore_permissions=True,
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def fetch_school_group_students(doctype, txt, searchfield, start, page_len, filters):
	"""Secure replacement for Education's unscoped Student Group Link query."""
	filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
	student_group = filters.get("student_group")
	school = _require_group_manager(student_group)
	if filters.get("school") and filters["school"] != school:
		frappe.throw(_("Student Group and School do not match."), frappe.PermissionError)
	enrollment_filters = {"padars_school": school, "academic_year": filters.get("academic_year"), "docstatus": 1}
	for field in ("program", "academic_term"):
		if filters.get(field):
			enrollment_filters[field] = filters[field]
	enrolled = frappe.get_all("Program Enrollment", filters=enrollment_filters, pluck="student", ignore_permissions=True)
	current = frappe.get_all("Student Group Student", filters={"parent": student_group}, pluck="student", ignore_permissions=True)
	candidates = list(set(enrolled) - set(current)) or ["__no_matching_students__"]
	return frappe.get_all(
		"Student", filters={"name": ["in", candidates], "enabled": 1, "student_name": ["like", f"%{txt}%"]},
		fields=["name", "student_name"], order_by="student_name asc", start=frappe.utils.cint(start),
		page_length=min(frappe.utils.cint(page_len), 50), ignore_permissions=True,
	)


@frappe.whitelist()
def get_student_attendance_records(based_on, date=None, student_group=None, course_schedule=None):
	if course_schedule:
		student_group = frappe.db.get_value("Course Schedule", course_schedule, "student_group")
	if not _can_read_group(student_group):
		frappe.throw(_("You are not authorized to view attendance for this group."), frappe.PermissionError)
	return _attendance_roster(student_group, course_schedule, date)


def _attendance_roster(student_group, course_schedule, date):
	students = get_school_group_students(student_group)
	filters = {"course_schedule": course_schedule} if course_schedule else {"student_group": student_group, "date": date}
	statuses = {row.student: row.status for row in frappe.get_all("Student Attendance", fields=["student", "status"], filters=filters)}
	for student in students:
		if student.student in statuses:
			student.status = statuses[student.student]
	return students


@frappe.whitelist()
def check_attendance_records_exist(course_schedule=None, student_group=None, date=None):
	if course_schedule:
		student_group = frappe.db.get_value("Course Schedule", course_schedule, "student_group")
	_require_group_manager(student_group)
	filters = {"course_schedule": course_schedule} if course_schedule else {"student_group": student_group, "date": date}
	return frappe.get_all("Student Attendance", filters=filters, fields=["name", "student", "status"])


@frappe.whitelist()
def mark_attendance(*args, **kwargs):
	_deny_unsupported(_("Bulk attendance marking"))


@frappe.whitelist()
def get_students(*args, **kwargs):
	_deny_unsupported(_("The generic Student Group roster action"))


@frappe.whitelist()
def enroll_student(*args, **kwargs):
	_deny_unsupported(_("Student Applicant enrollment"))


@frappe.whitelist()
def preview_report_card(*args, **kwargs):
	_deny_unsupported(_("Report card preview"))
