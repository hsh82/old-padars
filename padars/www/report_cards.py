import frappe

from padars.guardian_access import list_linked_students
from padars.permissions_site import get_student_for_user
from padars.publication import list_report_cards, read_report_card

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.throw("Please log in to view your report cards.", frappe.PermissionError)
	context.title = "Report Cards"
	context.linked_children = list_linked_students()
	if frappe.form_dict.get("publication"):
		context.report = read_report_card(frappe.form_dict.publication)
	else:
		selected = frappe.form_dict.get("student") or get_student_for_user()
		context.reports = list_report_cards(selected, frappe.form_dict.get("start", 0)) if selected else []
		context.next_start = int(frappe.form_dict.get("start", 0)) + 20 if len(context.reports) == 20 else None
	return context
