"""Installation helpers for Padars-owned security primitives."""

import frappe


STAGE1_ROLES = (
	"Padars Platform Administrator",
	"Padars School Manager",
	"Padars Academic Staff",
	"Padars Teacher",
	"Padars Grade Coordinator",
	"Padars Class Supervisor",
	"Padars Grade Entry Staff",
	"Padars Read Only",
	"Padars Sensitive Records",
	"Padars Moodle Manager",
)


def ensure_stage1_roles():
	if not frappe.db.exists("Role", "Padars Guardian"):
		frappe.get_doc({"doctype": "Role", "role_name": "Padars Guardian", "desk_access": 0}).insert(ignore_permissions=True)
	for role_name in STAGE1_ROLES:
		if not frappe.db.exists("Role", role_name):
			frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": 1}).insert(
				ignore_permissions=True
			)


def after_install():
	ensure_stage1_roles()
	ensure_academic_permissions()
	ensure_phase5_action_permissions()
	ensure_phase7_permissions()
	ensure_assessment_tool_permissions()
	ensure_assessment_approval_permissions()
	ensure_guardian_management_permissions()
	ensure_registration_import_permissions()
	validate_security_baseline()


def ensure_registration_import_permissions():
	from frappe.permissions import add_permission, update_permission_property

	filters = {"parent": "Data Import", "role": "Padars School Manager", "permlevel": 0, "if_owner": 0}
	if not frappe.db.exists("Custom DocPerm", filters):
		add_permission("Data Import", "Padars School Manager", 0, "read")
		for ptype in ("write", "create"):
			update_permission_property("Data Import", "Padars School Manager", 0, ptype, 1, validate=False)
	frappe.clear_cache(doctype="Data Import")


def validate_security_baseline():
	from padars.file_security import assert_no_protected_shares

	assert_no_protected_shares()


def ensure_action_permissions():
	"""Install role defaults once; later administrator changes are preserved."""
	from frappe import defaults
	from frappe.permissions import setup_custom_perms, update_permission_property

	marker = "padars_action_permissions_v1"
	permissions = {
		("Assessment Result", "enter_grade"): ("System Manager", "Padars Platform Administrator", "Padars School Manager", "Padars Academic Staff", "Padars Teacher", "Padars Grade Entry Staff"),
		("Student Attendance", "manage_attendance"): ("System Manager", "Padars Platform Administrator", "Padars School Manager", "Padars Academic Staff", "Padars Teacher", "Padars Grade Entry Staff"),
		("Student Log", "view_sensitive_student_data"): ("System Manager", "Padars Platform Administrator", "Padars Sensitive Records"),
		("Student Log", "manage_student_care"): ("System Manager", "Padars Platform Administrator", "Padars Sensitive Records"),
		("LMS Sync Operation", "manage_moodle"): ("System Manager", "Padars Platform Administrator", "Padars Moodle Manager"),
	}
	if not defaults.get_global_default(marker):
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
	ensure_phase7_permissions()
	ensure_student_care_action_permission()


def ensure_student_care_action_permission():
	"""Make the student-care action usable only through an assigned scope."""
	from frappe.permissions import add_permission, setup_custom_perms, update_permission_property

	if not frappe.db.exists("Permission Type", {"doc_type": "Student Log", "perm_type": "manage_student_care"}):
		return
	setup_custom_perms("Student Log")
	role = "Padars Sensitive Records"
	filters = {"parent": "Student Log", "role": role, "permlevel": 0, "if_owner": 0}
	if not frappe.db.exists("Custom DocPerm", filters):
		add_permission("Student Log", role, 0, "read")
	update_permission_property("Student Log", role, 0, "manage_student_care", 1, validate=False)
	frappe.clear_cache(doctype="Student Log")


def ensure_academic_permissions():
	"""Add narrow Padars role permissions without replacing existing rules."""
	from frappe.permissions import add_permission, update_permission_property

	read_doctypes = ("Academic Year", "Course", "Program", "Student", "Instructor", "Student Group",
		"Program Enrollment", "Course Enrollment", "Course Schedule", "Assessment Plan", "Assessment Result",
		"Student Attendance")
	roles = ("Padars School Manager", "Padars Academic Staff", "Padars Teacher", "Padars Grade Coordinator",
		"Padars Class Supervisor", "Padars Grade Entry Staff", "Padars Read Only")
	editable = {
		"Padars School Manager": set(read_doctypes),
		"Padars Academic Staff": {"Student Group", "Course Schedule", "Assessment Plan", "Assessment Result", "Student Attendance"},
		"Padars Teacher": {"Student Group", "Course Schedule", "Assessment Result", "Student Attendance"},
		"Padars Grade Coordinator": {"Student Group", "Course Schedule", "Assessment Plan", "Assessment Result", "Student Attendance"},
		"Padars Class Supervisor": {"Student Attendance"},
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


def ensure_assessment_tool_permissions():
	"""Give scoped grade-entry roles read access to the draft result tool."""
	from frappe.permissions import add_permission
	for role in ("Padars School Manager", "Padars Academic Staff", "Padars Teacher",
		"Padars Grade Coordinator", "Padars Grade Entry Staff"):
		if not frappe.db.exists("Custom DocPerm", {"parent": "Assessment Result Tool", "role": role, "permlevel": 0, "if_owner": 0}):
			add_permission("Assessment Result Tool", role, 0, "read")
	frappe.clear_cache(doctype="Assessment Result Tool")


def ensure_assessment_approval_permissions():
	"""Grant school managers result approval once, preserving later changes."""
	from frappe import defaults
	from frappe.permissions import add_permission, update_permission_property

	marker = "padars_assessment_approval_v1"
	if defaults.get_global_default(marker):
		return
	if not frappe.db.exists("Permission Type", {"doc_type": "Assessment Result", "perm_type": "approve_grade"}):
		frappe.throw("Missing Padars Assessment Result approve_grade permission type")
	role = "Padars School Manager"
	if not frappe.db.exists("Custom DocPerm", {"parent": "Assessment Result", "role": role, "permlevel": 0, "if_owner": 0}):
		add_permission("Assessment Result", role, 0, "read")
	for ptype in ("submit", "approve_grade"):
		update_permission_property("Assessment Result", role, 0, ptype, 1, validate=False)
	frappe.clear_cache(doctype="Assessment Result")
	defaults.set_global_default(marker, "1")


def ensure_phase5_action_permissions():
	"""Add action permission rows for the new scoped roles without changing administrator choices."""
	from frappe import defaults
	from frappe.permissions import add_permission, update_permission_property

	marker = "padars_phase5_action_permissions_v1"
	if defaults.get_global_default(marker):
		return

	permissions = {
		("Assessment Result", "enter_grade"): ("Padars Grade Coordinator",),
		("Student Attendance", "manage_attendance"): ("Padars Class Supervisor",),
	}
	for (doctype, ptype), roles in permissions.items():
		if not frappe.db.exists("Permission Type", {"doc_type": doctype, "perm_type": ptype}):
			frappe.throw(f"Missing Padars Permission Type: {doctype} / {ptype}")
		for role in roles:
			filters = {"parent": doctype, "role": role, "permlevel": 0, "if_owner": 0}
			if not frappe.db.exists("Custom DocPerm", filters):
				add_permission(doctype, role, 0, "read")
			update_permission_property(doctype, role, 0, ptype, 1, validate=False)
		frappe.clear_cache(doctype=doctype)
	defaults.set_global_default(marker, "1")


def ensure_phase7_permissions():
	"""Install only the native DocPerm rows needed by scoped daily operations."""
	from frappe.permissions import add_permission, update_permission_property

	permissions = {
		"Student Attendance": {
			"Padars School Manager": ("read", "create", "write", "submit", "cancel", "report", "export"),
			"Padars Academic Staff": ("read", "create", "write", "submit", "cancel", "report", "export"),
			"Padars Teacher": ("read", "create", "write", "submit", "cancel", "report"),
			"Padars Grade Coordinator": ("read", "create", "write", "submit", "cancel", "report", "export"),
			"Padars Class Supervisor": ("read", "create", "write", "submit", "cancel", "report", "export"),
			"Padars Grade Entry Staff": ("read", "create", "write", "submit", "cancel", "report"),
			"Padars Read Only": ("read", "report"),
		},
		"Student Attendance Tool": {
			"Padars School Manager": ("read", "create"),
			"Padars Academic Staff": ("read", "create"),
			"Padars Teacher": ("read", "create"),
			"Padars Grade Coordinator": ("read", "create"),
			"Padars Class Supervisor": ("read", "create"),
			"Padars Grade Entry Staff": ("read", "create"),
			"Padars Read Only": ("read",),
		},
		"Student Leave Application": {
			"Padars School Manager": ("read", "create", "write", "submit", "cancel"),
			"Padars Academic Staff": ("read", "create", "write", "submit", "cancel"),
			"Padars Teacher": ("read", "create", "write", "submit", "cancel"),
			"Padars Grade Coordinator": ("read", "create", "write", "submit", "cancel"),
			"Padars Class Supervisor": ("read", "create", "write", "submit", "cancel"),
			"Padars Grade Entry Staff": ("read", "create", "write", "submit", "cancel"),
			"Padars Read Only": ("read",),
		},
		"Student Log": {"Padars Sensitive Records": ("read", "create", "write")},
	}
	for doctype, role_permissions in permissions.items():
		for role, ptypes in role_permissions.items():
			filters = {"parent": doctype, "role": role, "permlevel": 0, "if_owner": 0}
			if not frappe.db.exists("Custom DocPerm", filters):
				add_permission(doctype, role, 0, "read")
			for ptype in ptypes:
				update_permission_property(doctype, role, 0, ptype, 1, validate=False)
		frappe.clear_cache(doctype=doctype)


def ensure_guardian_management_permissions():
	"""School managers maintain native relationships without User administration."""
	from frappe.permissions import add_permission, update_permission_property

	role = "Padars School Manager"
	filters = {"parent": "Guardian", "role": role, "permlevel": 0, "if_owner": 0}
	if not frappe.db.exists("Custom DocPerm", filters):
		add_permission("Guardian", role, 0, "read")
		for ptype in ("create", "write"):
			update_permission_property("Guardian", role, 0, ptype, 1, validate=False)
	frappe.clear_cache(doctype="Guardian")
