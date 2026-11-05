"""Keep Education's broad User permission away from school-manager sessions."""

import frappe


PLATFORM_ROLES = {"System Manager", "Padars Platform Administrator"}


def is_restricted_school_manager(user=None):
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	return "Padars School Manager" in roles and not roles.intersection(PLATFORM_ROLES)


def query_conditions(user=None, doctype=None):
	user = user or frappe.session.user
	if not is_restricted_school_manager(user):
		return ""
	return f"`tabUser`.`name` = {frappe.db.escape(user)}"


def has_permission(doc, ptype, user=None, **kwargs):
	user = user or frappe.session.user
	if not is_restricted_school_manager(user):
		return None

	if ptype not in {"read", "write"}:
		return False
	if doc is None:
		# Frappe's role permission remains the coarse DocType-level decision;
		# cross-account access is decided only when a specific User doc is named.
		return None

	name = doc if isinstance(doc, str) else doc.get("name")
	return name == user
