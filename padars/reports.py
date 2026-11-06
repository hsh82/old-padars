"""Fail closed for reports that have not yet been reviewed for academic scopes."""

import frappe
from frappe import _

from padars.permissions import is_platform_admin, is_school_manager
from padars.school_context import get_primary_school
from padars.permissions_site import STAFF_ROLES

DAILY_ATTENDANCE_REPORT = "Padars Daily Attendance Register"


def _require_reviewed_report_access(report_name=None):
	user = frappe.session.user
	if is_platform_admin(user):
		return
	if report_name == "Teacher Workload" and is_school_manager(get_primary_school(), user):
		return
	roles = set(frappe.get_roles(user))
	if report_name == DAILY_ATTENDANCE_REPORT and roles.intersection(STAFF_ROLES | {"Padars School Manager"}) \
		and frappe.has_permission("Student Attendance", "report", user=user):
		return
	if roles.intersection(STAFF_ROLES | {"Padars School Manager", "Academics User", "Instructor", "Student", "Guardian"}):
		frappe.throw(_("Reports are not yet available for scoped academic access."), frappe.PermissionError)


@frappe.whitelist()
def run(*args, **kwargs):
	report_name = kwargs.get("report_name") or frappe.form_dict.get("report_name")
	_require_reviewed_report_access(report_name)
	from frappe.desk.query_report import run as native_run

	return frappe.call(native_run, *args, **kwargs)


@frappe.whitelist()
def export_query():
	_require_reviewed_report_access(frappe.form_dict.get("report_name"))
	from frappe.desk.query_report import export_query as native_export

	return native_export()
