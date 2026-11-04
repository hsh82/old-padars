import frappe
from frappe import _

from padars.permissions import get_user_schools, has_school_access, is_school_admin

from padars.integrations.moodle.service import (
	request_course_offering_sync as create_course_offering_sync,
	retry_sync_operation as retry_operation,
)


@frappe.whitelist()
def request_course_offering_sync(course_offering):
	offering = frappe.get_doc("School Course Offering", course_offering)
	offering.check_permission("read")
	operation = create_course_offering_sync(offering)
	return operation.as_dict()


@frappe.whitelist()
def retry_sync_operation(operation):
	operation_doc = frappe.get_doc("LMS Sync Operation", operation)
	operation_doc.check_permission("write")
	return retry_operation(operation_doc.name).as_dict()


@frappe.whitelist()
def get_authorized_schools():
	"""Return only active schools available to the current user for frontend context."""
	if is_school_admin():
		filters = {"status": "Active"}
	else:
		schools = get_user_schools() or []
		if not schools:
			return []
		filters = {"name": ["in", schools], "status": "Active"}

	return frappe.get_all(
		"School",
		filters=filters,
		fields=["name", "school_name", "school_code", "current_academic_year"],
		order_by="school_name asc",
		ignore_permissions=True,
	)


def _get_link_query_filters(filters):
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)
	return filters or {}


def _require_school_context(school):
	if not school or not has_school_access(school):
		frappe.throw(_("You do not have access to this School."), frappe.PermissionError)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_school_students(doctype, txt, searchfield, start, page_len, filters):
	filters = _get_link_query_filters(filters)
	school = filters.get("school")
	_require_school_context(school)

	membership_users = frappe.get_all(
		"School Membership",
		filters={"school": school, "status": "Active", "school_role": ["in", ["Student", "Guardian"]]},
		pluck="user",
		ignore_permissions=True,
	)
	student_filters = {"user": ["in", membership_users], "enabled": 1}

	if frappe.get_meta("Program Enrollment").has_field("padars_school"):
		enrollment_filters = {
			"padars_school": school,
			"academic_year": filters.get("academic_year"),
			"program": filters.get("program"),
			"docstatus": 1,
		}
		enrollment_filters = {key: value for key, value in enrollment_filters.items() if value}
		if len(enrollment_filters) > 1:
			student_filters["name"] = [
				"in",
				frappe.get_all(
					"Program Enrollment", filters=enrollment_filters, pluck="student", ignore_permissions=True
				),
			]

	return frappe.get_list(
		"Student",
		filters=student_filters,
		or_filters=[["Student", searchfield, "like", f"%{txt}%"], ["Student", "student_name", "like", f"%{txt}%"]],
		fields=["name", "student_name"],
		order_by="student_name asc",
		start=start,
		page_length=page_len,
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_school_instructors(doctype, txt, searchfield, start, page_len, filters):
	filters = _get_link_query_filters(filters)
	school = filters.get("school")
	_require_school_context(school)

	instructors = frappe.get_all(
		"School Membership",
		filters={"school": school, "status": "Active", "instructor": ["is", "set"]},
		pluck="instructor",
		ignore_permissions=True,
	)
	if not instructors:
		return []

	return frappe.get_list(
		"Instructor",
		filters={"name": ["in", instructors]},
		or_filters=[
			["Instructor", searchfield, "like", f"%{txt}%"],
			["Instructor", "instructor_name", "like", f"%{txt}%"],
		],
		fields=["name", "instructor_name"],
		order_by="instructor_name asc",
		start=start,
		page_length=page_len,
	)

