"""Installable coarse role presets; Academic Assignments remain the scope layer."""

import frappe

DEFAULT_ROLE_PROFILES = {
	"Padars School Manager": ("Padars School Manager",),
	"Padars Academic Staff": ("Padars Academic Staff",),
	"Padars Teacher": ("Padars Teacher",),
	"Padars Grade Coordinator": ("Padars Grade Coordinator",),
	"Padars Class Supervisor": ("Padars Class Supervisor",),
	"Padars Grade Entry Staff": ("Padars Grade Entry Staff",),
	"Padars Read Only": ("Padars Read Only",),
	"Padars Student Care": ("Padars Academic Staff", "Padars Sensitive Records"),
	"Padars Student": ("Student",),
	"Padars Guardian": ("Padars Guardian",),
	"Padars Company Administrator": ("System Manager", "Padars Platform Administrator"),
	"Padars Moodle Operator": ("Padars Moodle Manager",),
}


def ensure_default_role_profiles():
	"""Create missing presets; preserve profiles an operator has already customized."""
	for name, roles in DEFAULT_ROLE_PROFILES.items():
		if frappe.db.exists("Role Profile", name):
			continue
		for role in roles:
			if not frappe.db.exists("Role", role):
				frappe.throw(f"Required role for default profile is missing: {role}")
		frappe.get_doc({"doctype": "Role Profile", "role_profile": name,
			"roles": [{"role": role} for role in roles]}).insert(ignore_permissions=True)


def grant_fixed_role(account, role):
	"""Retain Frappe profile semantics while granting only a service-authorized role."""
	allowed = {"Padars School Manager", "Padars Teacher", "Padars Grade Coordinator", "Padars Class Supervisor",
		"Padars Sensitive Records", "Padars Guardian", "Student"}
	if role not in allowed:
		frappe.throw("This service cannot grant that role.", frappe.PermissionError)
	current = {row.role for row in account.roles}
	if role in current:
		return
	if account.role_profiles:
		candidates = [(name, roles) for name, roles in DEFAULT_ROLE_PROFILES.items()
			if role in roles and set(roles).issubset(current | {role})]
		for name, expected in sorted(candidates, key=lambda item: len(item[1])):
			if not frappe.db.exists("Role Profile", name):
				continue
			profile = frappe.get_doc("Role Profile", name)
			actual = {row.role for row in profile.roles}
			if role in actual and actual.issubset(current | {role}):
				account.append("role_profiles", {"role_profile": name})
				break
		else:
			frappe.throw("A company operator must configure a compatible Role Profile before this role can be granted.", frappe.PermissionError)
	else:
		account.append("roles", {"role": role})
	account.save(ignore_permissions=True)
	if role not in {row.role for row in account.roles}:
		frappe.throw("The Role Profile did not retain the required role.", frappe.PermissionError)
