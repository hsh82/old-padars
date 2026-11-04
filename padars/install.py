"""Installation helpers for Padars-owned security primitives."""

import frappe


STAGE1_ROLES = (
	"Padars Platform Administrator",
	"Padars School Manager",
	"Padars Academic Staff",
	"Padars Teacher",
)


def ensure_stage1_roles():
	for role_name in STAGE1_ROLES:
		if not frappe.db.exists("Role", role_name):
			frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": 1}).insert(
				ignore_permissions=True
			)


def after_install():
	ensure_stage1_roles()
