"""Limit school managers' Data Import access to the student intake workflow."""

import frappe

from padars.permissions import is_platform_admin, is_school_manager
from padars.school_context import get_primary_school


def query_conditions(user=None, doctype=None):
	user = user or frappe.session.user
	if is_platform_admin(user):
		return ""
	if is_school_manager(get_primary_school(), user):
		return "`tabData Import`.`reference_doctype` = 'Student Identity' and `tabData Import`.`owner` = " + frappe.db.escape(user)
	return ""  # Preserve native permissions for users without the Padars manager role.


def has_permission(doc, ptype, user=None, **kwargs):
	user = user or frappe.session.user
	if is_platform_admin(user):
		return True
	if not is_school_manager(get_primary_school(), user):
		return True  # The native role-permission check still applies.
	if not doc or doc.reference_doctype != "Student Identity" or ptype not in {"read", "write", "create"}:
		return False
	if doc.is_new():
		return ptype == "create" and (not doc.owner or doc.owner == user)
	stored = frappe.db.get_value("Data Import", doc.name, ["owner", "reference_doctype"], as_dict=True)
	return bool(stored and stored.owner == user and stored.reference_doctype == "Student Identity"
		and doc.owner == stored.owner)
