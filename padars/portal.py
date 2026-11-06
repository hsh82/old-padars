"""Read-only projections for the authenticated student or verified family.

The service authorizes a single student before querying native academic data.
It does not grant Guardian access to native academic DocTypes or their RPCs.
"""

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import getdate, today

from padars.guardian_access import linked_students, list_linked_students
from padars.permissions_site import get_student_for_user, is_school_manager
from padars.school_context import get_primary_school


def _student(student=None):
	school = get_primary_school(required=True)
	own = get_student_for_user()
	student = student or own
	if not student or (student != own and student not in linked_students()
		and not is_school_manager(school)):
		frappe.throw(_("Choose your student account or a verified linked child."), frappe.PermissionError)
	if not frappe.db.exists("Student", {"name": student, "enabled": 1}):
		frappe.throw(_("This student is unavailable."), frappe.PermissionError)
	return school, student


def _course_links(school, student, offerings):
	"""Return token-free links only for observed, tenant-matched enrollments."""
	if not offerings or get_student_for_user() != student:
		return {}
	doc = frappe.get_doc("School", school)
	if not doc.lms_enabled or doc.lms_status != "Connected" or not doc.lms_tenant_id:
		return {}
	settings = frappe.get_single("LMS Settings")
	if not settings.enabled or settings.adapter != "Moodle":
		return {}
	from padars.integrations.moodle.rest import validate_moodle_base_url
	try:
		base = validate_moodle_base_url(settings.base_url, frappe.conf.get("padars_moodle_allowed_hosts"))
	except (ValueError, TypeError):
		return {}
	context = f"moodle:{base}:tenant:{int(doc.lms_tenant_id)}"
	user = frappe.session.user
	if not frappe.db.exists("LMS Entity Mapping", {"school": school, "local_doctype": "User",
		"local_name": user, "remote_type": "Moodle User", "remote_context": context, "status": "Active"}):
		return {}
	states = set(frappe.get_all("LMS Enrollment State", filters={"school": school, "user": user,
		"role": "Student", "desired_state": "Enrolled", "remote_state": "Enrolled",
		"course_offering": ["in", offerings]}, pluck="course_offering"))
	if not states:
		return {}
	mappings = frappe.get_all("LMS Entity Mapping", filters={"school": school,
		"local_doctype": "School Course Offering", "remote_type": "Moodle Course", "local_name": ["in", sorted(states)],
		"remote_context": context, "status": "Active"}, fields=["local_name", "remote_id"])
	return {row.local_name: f"{base}/course/view.php?id={int(row.remote_id)}"
		for row in mappings if str(row.remote_id).isdigit() and int(row.remote_id) > 0}


@frappe.whitelist()
def get_academic_overview(student=None, week=None):
	"""A bounded week of native sessions and official attendance, with courses."""
	school, student = _student(student)
	date = getdate(week or today())
	start = date - timedelta(days=date.weekday())
	end = start + timedelta(days=6)
	enrollments = frappe.get_all("Program Enrollment", filters={"student": student,
		"padars_school": school, "docstatus": 1}, fields=["program", "academic_year"])
	pairs = {(row.program, row.academic_year) for row in enrollments}
	memberships = frappe.get_all("Student Group Student", filters={"student": student,
		"active": 1, "parenttype": "Student Group"}, pluck="parent")
	groups = frappe.get_all("Student Group", filters={"name": ["in", memberships],
		"padars_school": school}, fields=["name", "program", "academic_year"]) if memberships else []
	group_names = [row.name for row in groups if (row.program, row.academic_year) in pairs]
	courses, sessions, attendance = [], [], []
	if group_names:
		courses = frappe.get_all("School Course Offering", filters={"school": school,
			"student_group": ["in", group_names], "status": ["!=", "Archived"]},
			fields=["name", "course", "instructor", "student_group"], order_by="course asc", limit_page_length=101)
		sessions = frappe.get_all("Course Schedule", filters={"student_group": ["in", group_names],
			"padars_school": school, "docstatus": ["<", 2], "schedule_date": ["between", [start, end]]},
			fields=["name", "course", "instructor", "schedule_date", "from_time", "to_time", "room"],
			order_by="schedule_date asc, from_time asc, name asc", limit_page_length=201)
	# Attendance history is owned by the student, including classes since left.
	attendance = frappe.get_all("Student Attendance", filters={"student": student,
		"padars_school": school, "docstatus": 1, "date": ["between", [start, end]]},
		fields=["date", "status", "course_schedule", "padars_late_minutes"], order_by="date asc, name asc", limit_page_length=201)
	course_ids = sorted({row.course for row in [*courses, *sessions] if row.course})
	teacher_ids = sorted({row.instructor for row in [*courses, *sessions] if row.instructor})
	course_names = dict(frappe.get_all("Course", filters={"name": ["in", course_ids]},
		fields=["name", "course_name"], as_list=True)) if course_ids else {}
	teacher_names = dict(frappe.get_all("Instructor", filters={"name": ["in", teacher_ids]},
		fields=["name", "instructor_name"], as_list=True)) if teacher_ids else {}
	links = _course_links(school, student, [row.name for row in courses])
	for row in [*courses, *sessions]:
		row.course_name = course_names.get(row.course, row.course)
		row.teacher_name = teacher_names.get(row.instructor, "")
	for row in courses:
		row.moodle_url = links.get(row.name)
	from padars.integrations.moodle.learning import _learning_for_student
	learning = _learning_for_student(student, [row.name for row in courses[:100]])
	return {"student": student, "student_name": frappe.db.get_value("Student", student, "student_name"),
		"week_start": str(start), "week_end": str(end),
		"previous_week": str(start - timedelta(days=7)), "next_week": str(start + timedelta(days=7)),
		"sessions": sessions[:200], "courses": courses[:100], "attendance": attendance[:200],
		"truncated": len(sessions) > 200 or len(courses) > 100 or len(attendance) > 200,
		"learning": learning, "learning_status": "Published selections" if learning else "Unavailable", "sso_verified": False}
