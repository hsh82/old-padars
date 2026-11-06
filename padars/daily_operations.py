"""Scoped daily attendance and approved-leave workflows around Education records."""

import json

import frappe
from erpnext.setup.doctype.holiday_list.holiday_list import is_holiday
from frappe import _
from frappe.utils import cint, getdate, today

from education.education.doctype.student_attendance.student_attendance import get_holiday_list


def _json_value(value, label):
	if isinstance(value, str):
		try:
			return json.loads(value)
		except (TypeError, ValueError):
			frappe.throw(_("{0} must be valid JSON.").format(label))
	return value


def _resolve_attendance_context(student_group=None, course_schedule=None, date=None):
	if course_schedule:
		schedule = frappe.db.get_value(
			"Course Schedule", course_schedule, ["student_group", "schedule_date"], as_dict=True
		)
		if not schedule:
			frappe.throw(_("Choose an existing Course Schedule."))
		if student_group and student_group != schedule.student_group:
			frappe.throw(_("Course Schedule and Student Group do not match."), frappe.PermissionError)
		if date and getdate(date) != getdate(schedule.schedule_date):
			frappe.throw(_("Attendance date must match the Course Schedule."), frappe.PermissionError)
		student_group, date = schedule.student_group, schedule.schedule_date
	if not student_group or not date:
		frappe.throw(_("Choose a Student Group and date, or a Course Schedule."))
	if not frappe.db.get_value("Student Group", student_group, "padars_school"):
		frappe.throw(_("Student Group has no Padars School context."), frappe.PermissionError)
	if course_schedule and not frappe.has_permission("Course Schedule", "read", course_schedule):
		frappe.throw(_("You are not authorized to access this Course Schedule."), frappe.PermissionError)
	return student_group, getdate(date)


def _attendance_doc(student_group, date, course_schedule=None, student=None):
	return frappe.get_doc({
		"doctype": "Student Attendance",
		"student_group": student_group,
		"course_schedule": course_schedule,
		"student": student,
		"date": date,
	})


def _require_attendance_action(student_group, date, course_schedule=None, student=None):
	if not student:
		student = frappe.db.get_value(
			"Student Group Student", {"parent": student_group, "active": 1}, "student"
		)
	if not student:
		frappe.throw(_("Attendance cannot be managed for a group without active students."))
	if not frappe.has_permission(
		"Student Attendance", "manage_attendance",
		doc=_attendance_doc(student_group, date, course_schedule, student),
		user=frappe.session.user,
		ignore_share_permissions=True,
	):
		frappe.throw(_("You are not authorized to manage attendance for this group."), frappe.PermissionError)


@frappe.whitelist()
def get_student_attendance_records(based_on, date=None, student_group=None, course_schedule=None):
	student_group, date = _resolve_attendance_context(student_group, course_schedule, date)
	if not frappe.has_permission("Student Group", "read", student_group):
		frappe.throw(_("You are not authorized to view attendance for this group."), frappe.PermissionError)
	students = frappe.get_all(
		"Student Group Student", filters={"parent": student_group, "active": 1},
		fields=["student", "student_name", "group_roll_number"], order_by="group_roll_number",
	)
	filters = {"student_group": student_group, "date": date}
	if course_schedule:
		filters["course_schedule"] = course_schedule
	attendance = frappe.get_list(
		"Student Attendance", filters=filters,
		or_filters=None if course_schedule else [
			["course_schedule", "is", "not set"], ["course_schedule", "=", ""],
		],
		fields=["student", "status", "padars_late_minutes"], page_length=1000,
	)
	by_student = {row.student: row for row in attendance}
	for student in students:
		row = by_student.get(student.student)
		if row:
			student.status = row.status
			student.padars_late_minutes = cint(row.padars_late_minutes)
	return students


@frappe.whitelist(methods=["POST"])
def check_attendance_records_exist(course_schedule=None, student_group=None, date=None):
	student_group, date = _resolve_attendance_context(student_group, course_schedule, date)
	_require_attendance_action(student_group, date, course_schedule)
	filters = {"course_schedule": course_schedule} if course_schedule else {"student_group": student_group, "date": date}
	return frappe.get_list(
		"Student Attendance", filters=filters,
		or_filters=None if course_schedule else [
			["course_schedule", "is", "not set"], ["course_schedule", "=", ""],
		], fields=["name", "student", "status"],
	)


@frappe.whitelist(methods=["POST"])
def mark_attendance(
	students_present, students_absent, course_schedule=None, student_group=None, date=None,
	students_late=None,
):
	student_group, date = _resolve_attendance_context(student_group, course_schedule, date)
	if date > getdate(today()):
		frappe.throw(_("Attendance cannot be marked for a future date."))
	_require_attendance_action(student_group, date, course_schedule)

	present = _json_value(students_present, _("Present students"))
	absent = _json_value(students_absent, _("Absent students"))
	late = _json_value(students_late or {}, _("Late arrival minutes"))
	if not isinstance(present, list) or not isinstance(absent, list) or not isinstance(late, dict):
		frappe.throw(_("Attendance entries have an invalid format."))

	roster = frappe.get_all(
		"Student Group Student", filters={"parent": student_group, "active": 1},
		fields=["student", "student_name"],
	)
	by_student = {row.student: row for row in roster}
	provided = [row.get("student") for row in present + absent if isinstance(row, dict)]
	if len(provided) != len(present) + len(absent) or len(provided) != len(set(provided)):
		frappe.throw(_("Each active student must appear exactly once in the attendance list."))
	if set(provided) != set(by_student):
		frappe.throw(_("Attendance must include the complete active group roster."), frappe.PermissionError)
	if set(late) - set(by_student):
		frappe.throw(_("Late arrival entries must belong to active students in this group."), frappe.PermissionError)

	for status, rows in (("Present", present), ("Absent", absent)):
		for row in rows:
			student = row["student"]
			minutes = cint(late.get(student) or 0)
			if minutes < 0 or minutes > 1440:
				frappe.throw(_("Late arrival minutes must be between 0 and 1440."))
			if status != "Present" and minutes:
				frappe.throw(_("Late minutes can be recorded only for a Present student."))
			_require_attendance_action(student_group, date, course_schedule, student)
			filters = {"student": student, "docstatus": ["!=", 2]}
			if course_schedule:
				filters["course_schedule"] = course_schedule
				existing_name = frappe.db.get_value("Student Attendance", filters, "name")
			else:
				filters.update({"student_group": student_group, "date": date})
				existing = frappe.get_list(
					"Student Attendance", filters=filters,
					or_filters=[["course_schedule", "is", "not set"], ["course_schedule", "=", ""]],
					fields=["name", "leave_application", "status", "docstatus", "padars_late_minutes"],
					page_length=1,
				)
				existing_name = existing[0].name if existing else None
			if existing_name:
				doc = frappe.get_doc("Student Attendance", existing_name)
				if doc.leave_application or doc.status == "Leave":
					frappe.throw(_("Attendance linked to an approved leave cannot be changed here."), frappe.PermissionError)
				if doc.status != status or cint(doc.padars_late_minutes) != minutes:
					doc.status = status
					doc.padars_late_minutes = minutes
					doc.save()
				if doc.docstatus == 0:
					doc.submit()
				continue
			doc = _attendance_doc(student_group, date, course_schedule, student)
			doc.student_name = by_student[student].student_name
			doc.status = status
			doc.padars_late_minutes = minutes
			doc.insert()
			doc.submit()

	frappe.msgprint(_("Attendance has been saved."))
	return {"marked": len(provided), "student_group": student_group, "date": str(date)}


@frappe.whitelist()
def get_student_leave_groups(student):
	from padars.permissions_site import get_student_for_user

	user = frappe.session.user
	if user != "Administrator" and student != get_student_for_user(user) and not frappe.has_permission(
		"Student", "read", student, user=user
	):
		frappe.throw(_("You are not authorized to view this student's groups."), frappe.PermissionError)
	groups = frappe.get_all(
		"Student Group Student", filters={"student": student, "active": 1}, pluck="parent",
	)
	if student == get_student_for_user(user):
		return sorted(groups)
	return [name for name in groups if frappe.has_permission("Student Group", "read", name, user=user)]


def _leave_group(doc):
	if doc.attendance_based_on == "Student Group":
		return doc.student_group
	if doc.attendance_based_on == "Course Schedule" and doc.course_schedule:
		return frappe.db.get_value("Course Schedule", doc.course_schedule, "student_group")
	return None


def _validate_leave_scope(doc):
	group = _leave_group(doc)
	if not group:
		frappe.throw(_("Choose a Student Group or Course Schedule for this leave application."))
	school = frappe.db.get_value("Student Group", group, "padars_school")
	if not school:
		frappe.throw(_("The selected Student Group has no Padars School context."), frappe.PermissionError)
	if not frappe.db.exists("Student Group Student", {"parent": group, "student": doc.student, "active": 1}):
		frappe.throw(_("The Student must be an active member of the selected Student Group."), frappe.PermissionError)
	if not doc.from_date or not doc.to_date or getdate(doc.from_date) > getdate(doc.to_date):
		frappe.throw(_("Choose a valid leave date range."))
	if doc.attendance_based_on == "Course Schedule":
		schedule_date = frappe.db.get_value("Course Schedule", doc.course_schedule, "schedule_date")
		if not schedule_date or getdate(doc.from_date) != getdate(schedule_date) or getdate(doc.to_date) != getdate(schedule_date):
			frappe.throw(_("Course Schedule leave must cover exactly the selected session date."))
	return group


def _leave_sessions(doc, group):
	filters = {"student_group": group, "schedule_date": ["between", [doc.from_date, doc.to_date]]}
	if doc.attendance_based_on == "Course Schedule":
		filters["name"] = doc.course_schedule
	sessions = frappe.get_list(
		"Course Schedule", filters=filters, fields=["name", "schedule_date"],
		order_by="schedule_date asc, name asc", page_length=1000,
	)
	if not sessions:
		frappe.throw(_("No scheduled class sessions fall within this leave period."))
	return sessions


def validate_student_leave_application(doc, method=None):
	group = _validate_leave_scope(doc)
	sessions = _leave_sessions(doc, group)
	holiday_list = get_holiday_list()
	sessions = [session for session in sessions if not is_holiday(holiday_list, session.schedule_date)]
	if not sessions:
		frappe.throw(_("The selected leave period contains no teaching sessions."))
	doc.total_leave_days = len({getdate(session.schedule_date) for session in sessions})


def apply_approved_leave(doc):
	group = _validate_leave_scope(doc)
	sessions = _leave_sessions(doc, group)
	holiday_list = get_holiday_list()
	sessions = [session for session in sessions if not is_holiday(holiday_list, session.schedule_date)]
	if not sessions:
		frappe.throw(_("The selected leave period contains no teaching sessions."))
	for session in sessions:
		_require_attendance_action(group, session.schedule_date, session.name, doc.student)
		filters = {"student": doc.student, "course_schedule": session.name, "docstatus": ["!=", 2]}
		existing = frappe.db.get_value("Student Attendance", filters, "name")
		if existing:
			attendance = frappe.get_doc("Student Attendance", existing)
			if attendance.leave_application == doc.name:
				continue
			if attendance.leave_application or attendance.docstatus != 1 or attendance.status not in {"Present", "Absent"}:
				frappe.throw(_("Attendance for session {0} cannot be reconciled with this leave application.").format(session.name))
			if attendance.status == "Present" and not doc.mark_as_present:
				frappe.throw(_("The Student is marked Present for session {0}; review attendance before approving leave.").format(session.name))
			previous = frappe.flags.get("padars_leave_attendance_update")
			frappe.flags.padars_leave_attendance_update = doc.name
			try:
				attendance.padars_leave_previous_status = attendance.status
				attendance.padars_leave_created_by_application = 0
				attendance.leave_application = doc.name
				if attendance.status == "Absent":
					attendance.status = "Present" if doc.mark_as_present else "Leave"
				attendance.flags.ignore_validate_update_after_submit = True
				attendance.save()
			finally:
				frappe.flags.padars_leave_attendance_update = previous
			continue
		attendance = _attendance_doc(group, session.schedule_date, session.name, doc.student)
		attendance.student_name = doc.student_name
		attendance.leave_application = doc.name
		attendance.status = "Present" if doc.mark_as_present else "Leave"
		attendance.padars_leave_created_by_application = 1
		previous = frappe.flags.get("padars_leave_attendance_update")
		frappe.flags.padars_leave_attendance_update = doc.name
		try:
			attendance.insert()
			attendance.submit()
		finally:
			frappe.flags.padars_leave_attendance_update = previous


def cancel_approved_leave_attendance(doc):
	rows = frappe.get_list(
		"Student Attendance", filters={"leave_application": doc.name, "docstatus": 1}, fields=["name"],
		page_length=1000,
	)
	previous = frappe.flags.get("padars_leave_attendance_cancel")
	frappe.flags.padars_leave_attendance_cancel = doc.name
	try:
		for row in rows:
			attendance = frappe.get_doc("Student Attendance", row.name)
			if attendance.leave_application == doc.name:
				if attendance.padars_leave_created_by_application:
					attendance.cancel()
				else:
					previous_status = attendance.padars_leave_previous_status
					if previous_status not in {"Present", "Absent"}:
						frappe.throw(_("Attendance linked to this leave has no valid prior status."))
					attendance.status = previous_status
					attendance.leave_application = None
					attendance.padars_leave_previous_status = None
					attendance.padars_leave_created_by_application = 0
					attendance.flags.ignore_validate_update_after_submit = True
					attendance.save()
	finally:
		frappe.flags.padars_leave_attendance_cancel = previous


def validate_student_attendance(doc, method=None):
	minutes = cint(doc.get("padars_late_minutes"))
	if minutes < 0 or minutes > 1440:
		frappe.throw(_("Late arrival minutes must be between 0 and 1440."))
	doc.padars_late_minutes = minutes
	if minutes and doc.status != "Present":
		frappe.throw(_("Late minutes can be recorded only for a Present student."))
	# Education defines this check but leaves it disabled in its validate method.
	doc.validate_date()
	old = doc.get_doc_before_save()
	internal_leave_update = frappe.flags.get("padars_leave_attendance_update")
	if doc.leave_application and not old and internal_leave_update != doc.leave_application:
		frappe.throw(_("Only an approved leave workflow can link attendance to a Leave Application."), frappe.PermissionError)
	if old:
		leave_fields_changed = any(old.get(field) != doc.get(field) for field in (
			"leave_application", "padars_leave_previous_status", "padars_leave_created_by_application",
		))
		if leave_fields_changed and internal_leave_update not in {old.leave_application, doc.leave_application}:
			frappe.throw(_("Leave-linked attendance can only be updated by its Leave Application workflow."), frappe.PermissionError)
		if old.leave_application and internal_leave_update != old.leave_application:
			frappe.throw(_("Attendance linked to an approved leave cannot be changed directly."), frappe.PermissionError)
	if doc.leave_application:
		leave = frappe.db.get_value(
			"Student Leave Application", doc.leave_application,
			["student", "attendance_based_on", "student_group", "course_schedule", "from_date", "to_date"],
			as_dict=True,
		)
		if not leave or leave.student != doc.student:
			frappe.throw(_("Leave Application must belong to the same Student."), frappe.PermissionError)
		if not doc.course_schedule:
			frappe.throw(_("Approved leave attendance must identify its Course Schedule."))
		schedule = frappe.db.get_value("Course Schedule", doc.course_schedule, ["student_group", "schedule_date"], as_dict=True)
		if not schedule or schedule.student_group != doc.student_group or not (
			getdate(leave.from_date) <= getdate(schedule.schedule_date) <= getdate(leave.to_date)
		):
			frappe.throw(_("Leave attendance must match a scheduled session in the approved period."), frappe.PermissionError)


def validate_attendance_cancellation(doc, method=None):
	leave_name = frappe.flags.get("padars_leave_attendance_cancel")
	if not leave_name or doc.leave_application != leave_name:
		frappe.throw(_("Attendance can only be cancelled through its approved Leave Application."), frappe.PermissionError)


def validate_student_log(doc, method=None):
	if not doc.student or not frappe.db.exists("Student", doc.student):
		frappe.throw(_("Choose an existing Student."))
	if not frappe.has_permission("Student Log", "manage_student_care", doc=doc, user=frappe.session.user):
		frappe.throw(_("You are not authorized to manage student-care records for this Student."), frappe.PermissionError)


class StudentLeaveApplicationExtension:
	"""Keep Education's form and validation while replacing unsafe attendance side effects."""

	def validate(self):
		super().validate()
		validate_student_leave_application(self)

	def on_submit(self):
		apply_approved_leave(self)

	def on_cancel(self):
		cancel_approved_leave_attendance(self)
