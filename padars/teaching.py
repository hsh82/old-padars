"""Assigned teacher lesson/course overview using native permission-aware queries."""

from collections import Counter
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import get_system_timezone, getdate, today

from padars.daily_operations import _attendance_doc
from padars.permissions_site import get_teacher_instructors, is_school_manager
from padars.portal import _enrolled_course_links
from padars.school_context import get_primary_school


@frappe.whitelist()
def get_teaching_overview(week=None):
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in to view teaching information."), frappe.PermissionError)
	school = get_primary_school(required=True)
	manager = is_school_manager(school)
	if not manager and "Padars Teacher" not in frappe.get_roles():
		frappe.throw(_("Teaching overview is restricted to teachers and school managers."), frappe.PermissionError)
	date = getdate(week or today())
	start = date - timedelta(days=date.weekday())
	end = start + timedelta(days=6)
	instructors = get_teacher_instructors(school=school)
	session_filters = {"padars_school": school, "schedule_date": ["between", [start, end]], "docstatus": ["<", 2]}
	course_filters = {"school": school, "status": ["!=", "Archived"]}
	if not manager:
		session_filters["instructor"] = ["in", instructors]
		course_filters["instructor"] = ["in", instructors]
	sessions = frappe.get_list("Course Schedule", filters=session_filters,
		fields=["name", "schedule_date", "from_time", "to_time", "course", "student_group", "room", "padars_session_mode", "padars_course_offering"],
		order_by="schedule_date asc, from_time asc, name asc", page_length=201)
	courses = frappe.get_list("School Course Offering", filters=course_filters,
		fields=["name", "course", "student_group", "status"], order_by="course asc, name asc", page_length=101)
	group_ids = sorted({row.student_group for row in [*sessions, *courses] if row.student_group})
	groups = frappe.get_list("Student Group", filters={"name": ["in", group_ids]},
		fields=["name", "student_group_name"], page_length=1000) if group_ids else []
	group_names = {row.name: row.student_group_name for row in groups}
	members = frappe.get_all("Student Group Student", filters={"parent": ["in", list(group_names)], "active": 1},
		fields=["parent", "student"]) if group_names else []
	counts = Counter(row.parent for row in members)
	first = {}
	for row in members:
		first.setdefault(row.parent, row.student)
	course_ids = sorted({row.course for row in [*sessions, *courses] if row.course})
	course_names = dict(frappe.get_all("Course", filters={"name": ["in", course_ids]},
		fields=["name", "course_name"], as_list=True)) if course_ids else {}
	links = _enrolled_course_links(school, [row.name for row in courses[:100]], "School Manager" if manager else "Teacher")
	for row in [*sessions, *courses]:
		row.course_name = course_names.get(row.course, row.course)
		row.group_name = group_names.get(row.student_group, row.student_group)
		row.roster_count = counts[row.student_group] if row.student_group in group_names else None
	for row in sessions:
		row.is_today = str(row.schedule_date) == today()
		student = first.get(row.student_group)
		row.can_mark_attendance = bool(student and getdate(row.schedule_date) <= getdate(today())
			and frappe.has_permission("Student Attendance", "manage_attendance",
				_attendance_doc(row.student_group, row.schedule_date, row.name, student)))
	for row in courses:
		row.moodle_url = links.get(row.name)
	return {"week_start": str(start), "week_end": str(end), "timezone": get_system_timezone(),
		"previous_week": str(start - timedelta(days=7)), "next_week": str(start + timedelta(days=7)),
		"sessions": sessions[:200], "today_lessons": [row for row in sessions[:200] if row.is_today],
		"courses": courses[:100], "truncated": len(sessions) > 200 or len(courses) > 100, "sso_verified": False}
