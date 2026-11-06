"""Default role landing pages; permissions remain enforced at their endpoints."""

import frappe

from padars.permissions_site import is_platform_admin


def get_user_home_page(user):
	if not user or user == "Guest":
		return None
	roles = set(frappe.get_roles(user))
	if is_platform_admin(user) or "Padars School Manager" in roles:
		return "app/padars"
	if "Padars Teacher" in roles:
		return "teacher"
	if roles.intersection({"Student", "Padars Guardian"}):
		return "school"
	if roles.intersection({"Padars Academic Staff", "Padars Grade Coordinator", "Padars Class Supervisor", "Padars Grade Entry Staff", "Padars Read Only"}):
		return "app/padars"
	return None
