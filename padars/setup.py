"""Minimal, resumable setup for one school site."""

import frappe
from frappe import _

from padars.permissions import is_platform_admin
from padars.school_context import get_primary_school


def _require_setup_admin():
	if not is_platform_admin():
		frappe.throw(_("Only a System Manager can configure the school."), frappe.PermissionError)


@frappe.whitelist()
def get_setup_status():
	_require_setup_admin()
	name = get_primary_school()
	if not name:
		return {}
	return frappe.db.get_value("School", name,
		["school_code", "school_name", "current_academic_year", "primary_school_manager"], as_dict=True)


@frappe.whitelist(methods=["POST"])
def configure_school(school_name, school_code, academic_year, primary_manager):
	_require_setup_admin()
	school_name = (school_name or "").strip()
	school_code = (school_code or "").strip()
	if not school_name or not school_code or not academic_year or not primary_manager:
		frappe.throw(_("School name, code, academic year and manager are required."))
	if not frappe.db.exists("Academic Year", academic_year):
		frappe.throw(_("Select an existing Academic Year."))
	if not frappe.db.exists("User", {"name": primary_manager, "enabled": 1, "user_type": "System User"}):
		frappe.throw(_("Select an enabled System User as manager."))
	name = get_primary_school()
	if name:
		school = frappe.get_doc("School", name)
		if school.school_code != school_code:
			frappe.throw(_("This site already has a School with a different code."))
	else:
		school = frappe.new_doc("School")
		school.school_code = school_code
	school.school_name = school_name
	school.current_academic_year = academic_year
	school.primary_school_manager = primary_manager
	school.status = "Active"
	school.save()
	return {"school": school.name}
