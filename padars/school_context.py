"""Site-level school context; a Frappe site belongs to one school."""

import frappe
from frappe import _


def get_primary_school(required=False):
	rows = frappe.get_all("School", filters={"status": "Active"}, pluck="name", limit=2)
	if len(rows) > 1:
		frappe.throw(_("This site has more than one active School."))
	if not rows and required:
		frappe.throw(_("Create the site's School before continuing."))
	return rows[0] if rows else None
