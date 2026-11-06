"""Manager workflows for Instructor identity and scoped staff assignments."""

import hashlib

import frappe
from frappe import _
from frappe.utils import cint

from padars.permissions import can_manage_school, is_platform_admin
from padars.school_context import get_primary_school


ASSIGNABLE_ROLES = {"Padars Teacher", "Padars Grade Coordinator", "Padars Class Supervisor", "Padars Sensitive Records"}


def _require_school_manager():
	school = get_primary_school(required=True)
	if not is_platform_admin() and not can_manage_school(school):
		frappe.throw(_("Only a School Manager can manage staff assignments."), frappe.PermissionError)
	return school


def _grant_scoped_role(user, role):
	if role not in ASSIGNABLE_ROLES:
		frappe.throw(_("This service cannot grant the requested role."), frappe.PermissionError)
	if not frappe.db.exists("Role", role):
		frappe.throw(_("Role {0} is not installed. Run migrate first.").format(role))
	user_doc = frappe.get_doc("User", user)
	if not user_doc.enabled or user_doc.user_type != "System User":
		frappe.throw(_("Staff assignments require an enabled System User."))
	if role not in {row.role for row in user_doc.roles}:
		user_doc.append("roles", {"role": role})
		user_doc.save(ignore_permissions=True)
		frappe.clear_cache(user=user)


def validate_instructor_mapping(doc, method=None):
	old = doc.get_doc_before_save()
	user = doc.get("padars_user")
	changed = (not old and bool(user)) or (old and old.padars_user != user)
	if changed and not frappe.flags.get("padars_staff_mapping_update"):
		frappe.throw(_("Use Link Frappe User to change the Instructor mapping."), frappe.PermissionError)
	if user:
		data = frappe.db.get_value("User", user, ["enabled", "user_type"], as_dict=True)
		if not data or not data.enabled or data.user_type != "System User":
			frappe.throw(_("An Instructor must link to an enabled System User."))
		other = frappe.db.get_value("Instructor", {"padars_user": user, "name": ["!=", doc.name or ""]}, "name")
		if other:
			frappe.throw(_("This User is already linked to Instructor {0}.").format(other))

	seen = set()
	for row in doc.get("padars_qualifications") or []:
		if not row.course or not frappe.db.exists("Course", row.course):
			frappe.throw(_("Every Instructor qualification must link to an Education Course."))
		grade = str(row.grade_level or "")
		if grade and grade not in {str(value) for value in range(7, 13)}:
			frappe.throw(_("Qualification Grade Level must be between 7 and 12."))
		identity = (row.course, grade)
		if identity in seen:
			frappe.throw(_("An Instructor qualification cannot be duplicated for the same Course and Grade."))
		seen.add(identity)
		row.qualification_key = hashlib.sha256(
			f"{doc.name}|{row.course}|{grade}".encode("utf-8")
		).hexdigest()


@frappe.whitelist(methods=["POST"])
def link_instructor_to_user(instructor, user):
	school = _require_school_manager()
	instructor_doc = frappe.get_doc("Instructor", instructor)
	instructor_doc.check_permission("write")
	if instructor_doc.status != "Active":
		frappe.throw(_("Only an active Instructor can be linked to a User."))
	user_data = frappe.db.get_value("User", user, ["enabled", "user_type"], as_dict=True)
	if not user_data or not user_data.enabled or user_data.user_type != "System User":
		frappe.throw(_("Choose an enabled System User."))
	if instructor_doc.padars_user and instructor_doc.padars_user != user and frappe.db.exists(
		"Academic Assignment", {
			"instructor": instructor_doc.name, "assignment_type": "Teacher", "status": "Active",
		}
	):
		frappe.throw(_("Unassign this Instructor from active Course Offerings before changing its User."))

	active_memberships = frappe.get_list("School Membership", filters={
		"school": school, "user": user, "school_role": "Teacher", "status": "Active",
	}, fields=["name", "instructor"])
	if any(row.instructor and row.instructor != instructor_doc.name for row in active_memberships):
		frappe.throw(_("This User already has an active Teacher membership for another Instructor."))

	_grant_scoped_role(user, "Padars Teacher")
	old_user = instructor_doc.padars_user
	if old_user and old_user != user:
		for row in frappe.get_list("School Membership", filters={
			"school": school, "user": old_user, "instructor": instructor_doc.name,
			"school_role": "Teacher", "status": "Active",
		}, fields=["name"]):
			frappe.db.set_value("School Membership", row.name, "status", "Inactive")
	instructor_doc.padars_user = user
	previous_flag = frappe.flags.get("padars_staff_mapping_update")
	previous_lms_flag = frappe.flags.get("padars_lms_teacher_identity_update")
	frappe.flags.padars_staff_mapping_update = True
	frappe.flags.padars_lms_teacher_identity_update = True
	try:
		instructor_doc.save()
	finally:
		frappe.flags.padars_staff_mapping_update = previous_flag
		frappe.flags.padars_lms_teacher_identity_update = previous_lms_flag

	membership = frappe.get_list("School Membership", filters={
		"school": school, "user": user, "school_role": "Teacher", "status": "Active",
	}, fields=["name", "instructor"], page_length=2)
	if membership and membership[0].instructor != instructor_doc.name:
		frappe.throw(_("Review the existing Teacher membership before linking this Instructor."))
	if not membership:
		frappe.get_doc({"doctype": "School Membership", "school": school, "user": user,
			"instructor": instructor_doc.name, "school_role": "Teacher", "status": "Active"}).insert()
	return {"instructor": instructor_doc.name, "user": user, "school": school}


@frappe.whitelist(methods=["POST"])
def assign_teacher_to_offering(offering, instructor=None, can_enter_marks=1, can_manage_attendance=1):
	school = _require_school_manager()
	offering_doc = frappe.get_doc("School Course Offering", offering)
	offering_doc.check_permission("write")
	if offering_doc.school != school:
		frappe.throw(_("The Course Offering belongs to another School."), frappe.PermissionError)
	if offering_doc.status == "Archived":
		frappe.throw(_("An archived Course Offering cannot be assigned to a Teacher."))
	instructor = instructor or None
	user = None
	if instructor:
		instructor_data = frappe.db.get_value("Instructor", instructor,
			["status", "padars_user"], as_dict=True)
		if not instructor_data or instructor_data.status != "Active" or not instructor_data.padars_user:
			frappe.throw(_("Choose an active Instructor linked to a User."))
		user = instructor_data.padars_user
		_grant_scoped_role(user, "Padars Teacher")

	previous = frappe.get_list("Academic Assignment", filters={
		"scope_type": "School Course Offering", "scope_name": offering_doc.name,
		"assignment_type": "Teacher", "status": "Active",
	}, fields=["name", "user"], page_length=100)
	old_instructor = offering_doc.instructor
	offering_doc.instructor = instructor
	previous_flag = frappe.flags.get("padars_teacher_assignment_update")
	frappe.flags.padars_teacher_assignment_update = True
	try:
		offering_doc.save()
	finally:
		frappe.flags.padars_teacher_assignment_update = previous_flag

	active_assignment = None
	for row in previous:
		assignment = frappe.get_doc("Academic Assignment", row.name)
		if user and assignment.user == user:
			active_assignment = assignment
		else:
			assignment.status = "Inactive"
			assignment.save()
	if not user:
		_queue_teacher_lms_change(offering_doc, old_instructor)
		return {"offering": offering_doc.name, "instructor": None, "user": None}
	values = {
		"user": user, "scope_type": "School Course Offering", "scope_name": offering_doc.name,
		"instructor": instructor, "assignment_type": "Teacher", "status": "Active",
		"can_edit": 0, "can_enter_marks": cint(can_enter_marks),
		"can_manage_attendance": cint(can_manage_attendance), "can_view_sensitive": 0,
	}
	if active_assignment:
		active_assignment.update(values)
		active_assignment.save()
	else:
		frappe.get_doc({"doctype": "Academic Assignment", **values}).insert()
	_queue_teacher_lms_change(offering_doc, old_instructor)
	return {"offering": offering_doc.name, "instructor": instructor, "user": user,
		"previous_instructor": old_instructor}


def _queue_teacher_lms_change(offering, old_instructor):
	if old_instructor == offering.instructor or not frappe.db.get_value("School", offering.school, "lms_enabled"):
		return
	if not frappe.db.exists("LMS Entity Mapping", {
		"school": offering.school, "local_doctype": "School Course Offering",
		"local_name": offering.name, "status": "Active",
	}):
		return
	from padars.integrations.moodle.service import queue_offering_staff_enrollments
	queue_offering_staff_enrollments(offering.name)


def get_teacher_workload_data(filters):
	"""Return planned weekly hours using permission-aware Course Offering reads."""
	_require_school_manager()
	academic_year = (filters or {}).get("academic_year")
	if not academic_year:
		frappe.throw(_("Choose an Academic Year."))
	conditions = {"academic_year": academic_year, "status": ["in", ["Draft", "Active"]],
		"instructor": ["is", "set"]}
	if (filters or {}).get("instructor"):
		conditions["instructor"] = filters["instructor"]
	offerings = []
	start = 0
	while True:
		batch = frappe.get_list("School Course Offering", filters=conditions,
			fields=["instructor", "expected_weekly_hours"], order_by="instructor asc",
			start=start, page_length=500)
		offerings.extend(batch)
		if len(batch) < 500:
			break
		start += len(batch)
	workload = {}
	for offering in offerings:
		row = workload.setdefault(offering.instructor, {"offerings": 0, "hours": 0.0})
		row["offerings"] += 1
		row["hours"] += float(offering.expected_weekly_hours or 0)
	if not workload:
		return []
	instructors = frappe.get_list("Instructor", filters={"name": ["in", sorted(workload)]},
		fields=["name", "instructor_name", "padars_user"], page_length=500)
	return [{
		"instructor": instructor.name,
		"instructor_name": instructor.instructor_name,
		"user": instructor.padars_user,
		"offering_count": workload[instructor.name]["offerings"],
		"expected_weekly_hours": round(workload[instructor.name]["hours"], 2),
	} for instructor in instructors]
