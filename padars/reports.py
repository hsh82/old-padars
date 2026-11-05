"""Fail closed for reports that have not yet been reviewed for academic scopes."""

import frappe
from frappe import _

from padars.permissions import is_platform_admin
from padars.permissions_site import STAFF_ROLES


def _require_reviewed_report_access():
	user = frappe.session.user
	if is_platform_admin(user):
		return
	if set(frappe.get_roles(user)).intersection(STAFF_ROLES | {"Padars School Manager", "Academics User", "Instructor", "Student", "Guardian"}):
		frappe.throw(_("Reports are not yet available for scoped academic access."), frappe.PermissionError)


@frappe.whitelist()
def run(*args, **kwargs):
	_require_reviewed_report_access()
	from frappe.desk.query_report import run as native_run

	return frappe.call(native_run, *args, **kwargs)


@frappe.whitelist()
def export_query():
	_require_reviewed_report_access()
	from frappe.desk.query_report import export_query as native_export

	return native_export()
