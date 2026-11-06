from padars.teaching import get_teaching_overview
import frappe

no_cache = 1


def get_context(context):
	context.title = "My Teaching"
	context.overview = get_teaching_overview(frappe.form_dict.get("week"))
	return context
