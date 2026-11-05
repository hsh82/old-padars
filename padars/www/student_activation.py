import frappe

from padars.school_context import get_primary_school


def get_context(context):
	school = get_primary_school()
	context.sms_required = bool(school and frappe.db.get_value("School", school, "require_sms_verification"))
	context.no_cache = 1
