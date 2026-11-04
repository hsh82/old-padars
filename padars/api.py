import frappe
from frappe import _

from padars.permissions import (
	can_manage_school,
	get_user_schools,
	has_school_access,
	is_platform_admin,
	is_school_manager,
)

from padars.integrations.moodle.service import (
	request_enrollment_sync as create_enrollment_sync,
	request_course_offering_sync as create_course_offering_sync,
	request_school_tenant_sync as create_school_tenant_sync,
	request_user_sync as create_user_sync,
	retry_sync_operation as retry_operation,
)


@frappe.whitelist()
def request_course_offering_sync(course_offering):
	offering = frappe.get_doc("School Course Offering", course_offering)
	if not is_school_manager(offering.school):
		frappe.throw(_("Only a School Manager can request Moodle course provisioning."), frappe.PermissionError)
	operation = create_course_offering_sync(offering)
	return operation.as_dict()


@frappe.whitelist()
def retry_sync_operation(operation):
	operation_doc = frappe.get_doc("LMS Sync Operation", operation)
	if not is_school_manager(operation_doc.school):
		frappe.throw(_("Only a School Manager can retry a synchronization operation."), frappe.PermissionError)
	return retry_operation(operation_doc.name).as_dict()


@frappe.whitelist()
def request_school_tenant_sync(school):
	school_doc = frappe.get_doc("School", school)
	if not is_platform_admin():
		frappe.throw(_("Only a Platform Administrator can provision a Moodle tenant."), frappe.PermissionError)
	return create_school_tenant_sync(school_doc).as_dict()


@frappe.whitelist()
def request_student_user_provisioning(student, school):
	student_doc = frappe.get_doc("Student", student)
	if not is_school_manager(school):
		frappe.throw(_("You do not have access to School {0}.").format(school), frappe.PermissionError)
	if not frappe.db.exists("School Membership", {"school": school, "user": student_doc.user, "school_role": "Student", "status": "Active"}):
		frappe.throw(_("Student {0} is not an active member of School {1}.").format(student, school), frappe.PermissionError)
	if not student_doc.user:
		frappe.throw(_("Student {0} does not have a linked Frappe User yet.").format(student))
	return create_user_sync(frappe.get_doc("User", student_doc.user), frappe.get_doc("School", school)).as_dict()


@frappe.whitelist()
def request_enrollment_state_sync(enrollment_state):
	enrollment_doc = frappe.get_doc("LMS Enrollment State", enrollment_state)
	if not is_school_manager(enrollment_doc.school):
		frappe.throw(_("Only a School Manager can request enrollment synchronization."), frappe.PermissionError)
	return create_enrollment_sync(enrollment_doc).as_dict()


@frappe.whitelist()
def get_authorized_schools():
	"""Return only active schools available to the current user for frontend context."""
	if is_platform_admin():
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
	if not school or not can_manage_school(school):
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
	if not membership_users:
		return []
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

