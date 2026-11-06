import frappe

from padars.guardian_access import list_linked_students
from padars.permissions_site import get_student_for_user
from padars.portal import get_academic_overview

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.throw("Please log in to view school information.", frappe.PermissionError)
	context.title = "My School"
	context.children = list_linked_students()
	student = frappe.form_dict.get("student") or get_student_for_user()
	context.overview = get_academic_overview(student, frappe.form_dict.get("week")) if student else None
	return context
