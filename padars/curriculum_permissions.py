"""School-manager authorization for annual curriculum snapshots."""

import frappe

from padars.permissions import is_platform_admin
from padars.school_context import get_primary_school


def _is_manager(user):
	return "Padars School Manager" in frappe.get_roles(user)


def query_conditions(user=None, doctype=None):
	user = user or frappe.session.user
	if is_platform_admin(user):
		return ""
	if not _is_manager(user):
		return "1=0"
	school = get_primary_school()
	if not school:
		return "1=0"
	return "`tabSchool Curriculum Adoption`.`school` = " + frappe.db.escape(school)


def has_permission(doc, ptype, user=None, **kwargs):
	user = user or frappe.session.user
	if is_platform_admin(user):
		return True
	if not _is_manager(user) or ptype not in {"read", "write", "create"}:
		return False
	if doc is None:
		return ptype in {"read", "create"}
	name = doc if isinstance(doc, str) else doc.get("name")
	school = doc.get("school") if not isinstance(doc, str) else None
	if name and not getattr(doc, "is_new", lambda: False)():
		stored_school = frappe.db.get_value("School Curriculum Adoption", name, "school")
		if stored_school != get_primary_school():
			return False
		if school and school != stored_school:
			return False
		return True
	return not school or school == get_primary_school()
