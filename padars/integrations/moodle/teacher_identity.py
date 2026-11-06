"""Minimal School-scoped Instructor-to-User link required for Moodle access."""

import frappe
from frappe import _

from padars.permissions import can_manage_school, is_lms_operator
from padars.school_context import get_primary_school


def validate_instructor_mapping(doc, method=None):
	old = doc.get_doc_before_save()
	user = doc.get("padars_user")
	changed = (not old and bool(user)) or (old and old.padars_user != user)
	if changed and not frappe.flags.get("padars_lms_teacher_identity_update"):
		frappe.throw(_("Use Link Frappe User to change the Instructor's Moodle identity."), frappe.PermissionError)
	if not user:
		return
	user_data = frappe.db.get_value("User", user, ["enabled", "user_type"], as_dict=True)
	if not user_data or not user_data.enabled or user_data.user_type != "System User":
		frappe.throw(_("An Instructor must link to an enabled Frappe System User."))
	other = frappe.db.get_value("Instructor", {"padars_user": user, "name": ["!=", doc.name or ""]}, "name")
	if other:
		frappe.throw(_("This Frappe User is already linked to Instructor {0}.").format(other))


@frappe.whitelist(methods=["POST"])
def link_instructor_to_user(instructor, user):
	school = get_primary_school(required=True)
	operator = is_lms_operator()
	if not (operator or can_manage_school(school)):
		frappe.throw(_("Only this School's Manager or company Moodle support can link Instructor accounts."), frappe.PermissionError)
	instructor_doc = frappe.get_doc("Instructor", instructor)
	if not operator:
		instructor_doc.check_permission("write")
	if instructor_doc.status != "Active":
		frappe.throw(_("Only an active Instructor can be linked to a Frappe User."))
	user_data = frappe.db.get_value("User", user, ["enabled", "user_type"], as_dict=True)
	if not user_data or not user_data.enabled or user_data.user_type != "System User":
		frappe.throw(_("Choose an enabled Frappe System User."))
	if instructor_doc.padars_user and instructor_doc.padars_user != user and frappe.db.exists(
		"School Course Offering", {"instructor": instructor_doc.name, "status": ["!=", "Archived"]}
	):
		frappe.throw(_("Unassign this Instructor from active Course Offerings before changing its linked User."))
	previous_flag = frappe.flags.get("padars_lms_teacher_identity_update")
	previous_staff_flag = frappe.flags.get("padars_staff_mapping_update")
	frappe.flags.padars_lms_teacher_identity_update = True
	frappe.flags.padars_staff_mapping_update = True
	try:
		instructor_doc.padars_user = user
		instructor_doc.save(ignore_permissions=operator)
	finally:
		frappe.flags.padars_lms_teacher_identity_update = previous_flag
		frappe.flags.padars_staff_mapping_update = previous_staff_flag
	return {"instructor": instructor_doc.name, "user": user, "school": school}
