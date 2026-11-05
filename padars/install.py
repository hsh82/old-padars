"""Installation helpers for Padars-owned security primitives."""

import frappe


STAGE1_ROLES = (
	"Padars Platform Administrator",
	"Padars School Manager",
	"Padars Academic Staff",
	"Padars Teacher",
	"Padars Grade Entry Staff",
	"Padars Read Only",
	"Padars Sensitive Records",
	"Padars Moodle Manager",
)


def ensure_stage1_roles():
	for role_name in STAGE1_ROLES:
		if not frappe.db.exists("Role", role_name):
			frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": 1}).insert(
				ignore_permissions=True
			)


def after_install():
	ensure_stage1_roles()
	ensure_academic_permissions()
	validate_security_baseline()


def validate_security_baseline():
	from padars.file_security import assert_no_protected_shares

	assert_no_protected_shares()


def ensure_action_permissions():
	"""Install role defaults once; later administrator changes are preserved."""
	from frappe import defaults
	from frappe.permissions import setup_custom_perms, update_permission_property

	marker = "padars_action_permissions_v1"
	if defaults.get_global_default(marker):
		return
	permissions = {
		("Assessment Result", "enter_grade"): ("System Manager", "Padars Platform Administrator", "Padars School Manager", "Padars Academic Staff", "Padars Teacher", "Padars Grade Entry Staff"),
		("Student Attendance", "manage_attendance"): ("System Manager", "Padars Platform Administrator", "Padars School Manager", "Padars Academic Staff", "Padars Teacher", "Padars Grade Entry Staff"),
		("Student Log", "view_sensitive_student_data"): ("System Manager", "Padars Platform Administrator", "Padars Sensitive Records"),
		("LMS Sync Operation", "manage_moodle"): ("System Manager", "Padars Platform Administrator", "Padars Moodle Manager"),
	}
	for (doctype, ptype), roles in permissions.items():
		if not frappe.db.exists("Permission Type", {"doc_type": doctype, "perm_type": ptype}):
			frappe.throw(f"Missing Padars Permission Type: {doctype} / {ptype}")
		setup_custom_perms(doctype)
		for role in roles:
			if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0, "if_owner": 0}):
				frappe.permissions.add_permission(doctype, role, 0, "read")
			update_permission_property(doctype, role, 0, ptype, 1, validate=False)
		frappe.clear_cache(doctype=doctype)
	defaults.set_global_default(marker, "1")


def ensure_academic_permissions():
	"""Add narrow Padars role permissions without replacing existing rules."""
	from frappe.permissions import add_permission, update_permission_property

	read_doctypes = ("Academic Year", "Course", "Program", "Student", "Instructor", "Student Group",
		"Program Enrollment", "Course Enrollment", "Course Schedule", "Assessment Plan", "Assessment Result",
		"Student Attendance")
	roles = ("Padars School Manager", "Padars Academic Staff", "Padars Teacher", "Padars Grade Entry Staff", "Padars Read Only")
	editable = {
		"Padars School Manager": set(read_doctypes),
		"Padars Academic Staff": {"Student Group", "Course Schedule", "Assessment Plan", "Assessment Result", "Student Attendance"},
		"Padars Teacher": {"Student Group", "Course Schedule", "Assessment Result", "Student Attendance"},
		"Padars Grade Entry Staff": {"Assessment Result", "Student Attendance"},
		"Padars Read Only": set(),
	}
	for doctype in read_doctypes:
		for role in roles:
			filters = {"parent": doctype, "role": role, "permlevel": 0, "if_owner": 0}
			if frappe.db.exists("Custom DocPerm", filters):
				continue
			add_permission(doctype, role, 0, "read")
			if doctype in editable[role]:
				for ptype in ("write", "create"):
					update_permission_property(doctype, role, 0, ptype, 1, validate=False)
		frappe.clear_cache(doctype=doctype)
	if not frappe.db.exists("Custom DocPerm", {"parent": "Student Log", "role": "Padars Sensitive Records", "permlevel": 0}):
		add_permission("Student Log", "Padars Sensitive Records", 0, "read")
	frappe.clear_cache(doctype="Student Log")
