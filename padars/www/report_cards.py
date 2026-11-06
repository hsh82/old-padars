import frappe

from padars.publication import list_report_cards, read_report_card

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.throw("Please log in to view your report cards.", frappe.PermissionError)
	context.title = "Report Cards"
	if frappe.form_dict.get("publication"):
		context.report = read_report_card(frappe.form_dict.publication)
	else:
		context.reports = list_report_cards(frappe.form_dict.get("student"), frappe.form_dict.get("start", 0))
		context.next_start = int(frappe.form_dict.get("start", 0)) + 20 if len(context.reports) == 20 else None
	return context
