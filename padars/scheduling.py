"""Padars validation and safety rules around Education scheduling records."""

from calendar import day_name
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import add_days, get_time, getdate, today

from education.education.utils import validate_overlap_for

from padars.permissions import can_manage_school, is_platform_admin
from padars.school_context import get_primary_school

ASSESSMENT_PLAN_SCHEDULE_FIELDS = (
	"student_group", "program", "course", "academic_year", "academic_term",
	"schedule_date", "from_time", "to_time", "room", "examiner", "supervisor",
	"padars_school", "padars_course_offering",
)


def _get_group(name):
	group = frappe.db.get_value(
		"Student Group",
		name,
		["program", "academic_year", "academic_term", "course", "group_based_on", "padars_school"],
		as_dict=True,
	)
	if not group:
		frappe.throw(_("Choose an existing Education Student Group."))
	group.padars_is_class_section = (
		frappe.db.get_value("Student Group", name, "padars_is_class_section")
		if frappe.get_meta("Student Group").has_field("padars_is_class_section")
		else 0
	)
	return group


def _resolve_offering(doc, group, required=False):
	"""Resolve and validate the annual offering for a schedule or exam."""
	offering_name = doc.get("padars_course_offering")
	if offering_name:
		offering = frappe.db.get_value(
			"School Course Offering",
			offering_name,
			["name", "school", "academic_year", "course", "student_group", "instructor", "status"],
			as_dict=True,
		)
		if not offering:
			frappe.throw(_("The selected School Course Offering does not exist."))
		if (offering.student_group, offering.course, offering.academic_year) != (
			doc.student_group,
			doc.course,
			group.academic_year,
		):
			frappe.throw(_("The School Course Offering must match the group, course, and academic year."))
		if offering.status == "Archived":
			frappe.throw(_("Archived Course Offerings cannot be scheduled."))
		return offering

	offerings = frappe.get_list(
		"School Course Offering",
		filters={
			"student_group": doc.student_group,
			"course": doc.course,
			"academic_year": group.academic_year,
			"status": ["in", ["Draft", "Active"]],
		},
		fields=["name", "school", "academic_year", "course", "student_group", "instructor", "status"],
		page_length=2,
	)
	if len(offerings) > 1:
		frappe.throw(_("More than one active Course Offering matches this group and course."))
	if offerings:
		doc.padars_course_offering = offerings[0].name
		return offerings[0]
	if required:
		frappe.throw(_("Create a Course Offering before scheduling this class section."))
	return None


def _validate_group_fields(doc, group):
	for field in ("program", "academic_year", "academic_term"):
		expected = group.get(field)
		actual = doc.get(field)
		if actual and actual != expected:
			frappe.throw(_("{0} must match the selected Student Group.").format(field.replace("_", " ").title()))
		if expected and not actual:
			doc.set(field, expected)
	if group.group_based_on == "Course" and group.course:
		if doc.course and doc.course != group.course:
			frappe.throw(_("Course must match the selected Student Group."))
		doc.course = group.course


def _validate_date_within_group(doc, group):
	if group.academic_term:
		start_date, end_date = frappe.db.get_value(
			"Academic Term", group.academic_term, ["term_start_date", "term_end_date"]
		)
	else:
		start_date, end_date = frappe.db.get_value(
			"Academic Year", group.academic_year, ["year_start_date", "year_end_date"]
		)
	date = getdate(doc.schedule_date)
	if start_date and date < getdate(start_date) or end_date and date > getdate(end_date):
		frappe.throw(_("The scheduled date must fall within the Student Group's academic period."))


def validate_course_schedule(doc, method=None):
	group = _get_group(doc.student_group)
	offering = _resolve_offering(doc, group, required=bool(group.padars_is_class_section))
	if offering and offering.instructor and offering.instructor != doc.instructor:
		frappe.throw(_("The scheduled Instructor must match the Course Offering's assigned Teacher."))
	if group.padars_is_class_section and offering and not offering.instructor:
		frappe.throw(_("Assign a Teacher to the Course Offering before scheduling the class section."))
	_validate_date_within_group(doc, group)

	# Education checks group, room, and Course Schedule instructor conflicts.
	# It checks only Assessment Plan supervisors against that instructor; the
	# examiner is also a scheduled person and must not overlap a class.
	validate_overlap_for(doc, "Assessment Plan", "examiner", doc.instructor)


def validate_assessment_plan(doc, method=None):
	group = _get_group(doc.student_group)
	_validate_group_fields(doc, group)
	offering = _resolve_offering(doc, group, required=bool(group.padars_is_class_section))
	if offering:
		if doc.padars_school and doc.padars_school != offering.school:
			frappe.throw(_("Assessment Plan School must match its Course Offering."))
		doc.padars_school = offering.school
	else:
		doc.padars_school = doc.padars_school or group.padars_school or get_primary_school(required=True)

	if not doc.schedule_date or not doc.from_time or not doc.to_time:
		frappe.throw(_("Assessment Plan requires a date, start time, and end time."))
	old = doc.get_doc_before_save()
	if old and any(old.get(field) != doc.get(field) for field in ASSESSMENT_PLAN_SCHEDULE_FIELDS):
		has_results = frappe.db.exists(
			"Assessment Result", {"assessment_plan": doc.name, "docstatus": ["!=", 2]}
		)
		if getdate(old.schedule_date) <= getdate(today()) or has_results:
			frappe.throw(_("Past Assessment Plans and plans with results cannot be rescheduled or moved."))
	_validate_date_within_group(doc, group)
	if get_time(doc.from_time) >= get_time(doc.to_time):
		frappe.throw(_("Assessment From Time must be earlier than To Time."))

	# Education handles group, room, and supervisor-to-supervisor conflicts.
	# Check both examiner and supervisor against Course Schedule instructors,
	# and check examiner conflicts with either role on other Assessment Plans.
	for instructor in {doc.examiner, doc.supervisor} - {None, ""}:
		validate_overlap_for(doc, "Course Schedule", "instructor", instructor)
		for field in ("examiner", "supervisor"):
			validate_overlap_for(doc, "Assessment Plan", field, instructor)


def validate_assessment_result_relationships(doc, method=None):
	plan = frappe.db.get_value(
		"Assessment Plan",
		doc.assessment_plan,
		[
			"student_group", "program", "course", "academic_year", "academic_term",
			"assessment_group", "grading_scale", "padars_school", "padars_course_offering",
		],
		as_dict=True,
	)
	if not plan:
		frappe.throw(_("Choose an existing Assessment Plan."))
	for field in (
		"student_group", "program", "course", "academic_year", "academic_term",
		"assessment_group", "grading_scale", "padars_school", "padars_course_offering",
	):
		expected = plan.get(field)
		actual = doc.get(field)
		if actual and actual != expected:
			frappe.throw(_("Assessment Result {0} must match its Assessment Plan.").format(field.replace("_", " ")))
		if expected and not actual:
			doc.set(field, expected)


def validate_course_schedule_deletion(doc, method=None):
	if getdate(doc.schedule_date) <= getdate(today()):
		frappe.throw(_("Past and current Course Schedules are retained as academic history."))
	if frappe.db.exists(
		"Student Attendance",
		{"course_schedule": doc.name, "docstatus": ["!=", 2]},
	):
		frappe.throw(_("A Course Schedule with attendance records cannot be deleted."))


def validate_assessment_plan_deletion(doc, method=None):
	if doc.schedule_date and getdate(doc.schedule_date) <= getdate(today()):
		frappe.throw(_("Past and current Assessment Plans are retained as academic history."))
	if frappe.db.exists(
		"Assessment Result", {"assessment_plan": doc.name, "docstatus": ["!=", 2]}
	):
		frappe.throw(_("An Assessment Plan with results cannot be deleted or cancelled."))


class CourseSchedulingToolExtension:
	"""Keep Education's weekly scheduling UI and make replacement atomic and safe."""

	@frappe.whitelist(methods=["POST"])
	def schedule_course(self, days):
		school = get_primary_school(required=True)
		if not is_platform_admin() and not can_manage_school(school):
			frappe.throw(_("Only a School Manager can run weekly Course Scheduling."), frappe.PermissionError)

		self.validate_mandatory(days)
		self.validate_date()
		group = _get_group(self.student_group)
		if group.padars_school != school:
			frappe.throw(_("The Student Group belongs to another School."), frappe.PermissionError)
		start = getdate(self.course_start_date)
		end = getdate(self.course_end_date)
		if start >= end:
			frappe.throw(_("Course End Date must be later than Course Start Date."))
		if not isinstance(days, (list, tuple, set)) or not set(days).issubset(set(day_name)):
			frappe.throw(_("Choose one or more valid weekdays."))
		if not any(day_name[(start + timedelta(days=offset)).weekday()] in days for offset in range(min((end - start).days, 7))):
			frappe.throw(_("The selected weekdays do not occur within the date range."))

		period_doctype = "Academic Term" if group.academic_term else "Academic Year"
		period_name = group.academic_term or group.academic_year
		period_start, period_end = frappe.db.get_value(
			period_doctype,
			period_name,
			["term_start_date", "term_end_date"] if group.academic_term else ["year_start_date", "year_end_date"],
		)
		if period_start and start < getdate(period_start) or period_end and add_days(end, -1) > getdate(period_end):
			frappe.throw(_("The scheduling range must stay within the Student Group's academic period."))

		if not self.reschedule:
			return super().schedule_course(days)

		if start <= getdate(today()):
			frappe.throw(_("Rescheduling may replace future sessions only; past and current dates are protected."))

		course = group.course if group.group_based_on == "Course" else self.course
		filters = {
			"student_group": self.student_group,
			"course": course,
			"schedule_date": ["between", [start, end]],
		}
		existing = []
		start_at = 0
		while True:
			batch = frappe.get_list(
				"Course Schedule", filters=filters, fields=["name", "schedule_date"],
				start=start_at, page_length=500,
			)
			existing.extend(batch)
			if len(batch) < 500:
				break
			start_at += len(batch)
		weekday_names = set(days)
		target_names = [
			row.name for row in existing
			if day_name[getdate(row.schedule_date).weekday()] in weekday_names
		]
		if any(
			getdate(row.schedule_date) == end
			and day_name[getdate(row.schedule_date).weekday()] in weekday_names
			for row in existing
		):
			frappe.throw(_("Move the End Date forward: Education treats it as exclusive when creating sessions."))
		if target_names and frappe.get_list(
			"Student Attendance",
			filters={"course_schedule": ["in", target_names], "docstatus": ["!=", 2]},
			fields=["name"],
			page_length=1,
		):
			frappe.throw(_("A selected session has attendance and cannot be replaced."))

		frappe.db.savepoint("padars_safe_course_reschedule")
		try:
			result = super().schedule_course(days)
			if result.get("reschedule_errors") or result.get("course_schedules_errors"):
				frappe.db.rollback(save_point="padars_safe_course_reschedule")
				frappe.throw(_("Rescheduling was not applied because one or more sessions could not be safely replaced."))
			return result
		except Exception:
			frappe.db.rollback(save_point="padars_safe_course_reschedule")
			raise
