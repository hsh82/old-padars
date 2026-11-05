import frappe

from padars.school_context import get_primary_school


def get_or_create_test_school(academic_year, code):
	name = get_primary_school()
	if name:
		return frappe.get_doc("School", name)
	return frappe.get_doc({
		"doctype": "School", "school_code": code, "school_name": "Test School",
		"current_academic_year": academic_year, "primary_school_manager": "Administrator",
	}).insert()
