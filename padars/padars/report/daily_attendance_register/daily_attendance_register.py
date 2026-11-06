"""Permission-aware student attendance detail for the selected date range."""

import frappe
from frappe import _
from frappe.utils import getdate, today


def execute(filters=None):
	filters = frappe._dict(filters or {})
	start = getdate(filters.get("from_date") or today())
	end = getdate(filters.get("to_date") or start)
	if end < start:
		frappe.throw(_("To Date cannot be earlier than From Date."))
	if (end - start).days > 90:
		frappe.throw(_("Choose a date range of 90 days or less."))
	if filters.get("student_group") and not frappe.has_permission(
		"Student Group", "read", filters.student_group
	):
		frappe.throw(_("You are not authorized to view this Student Group."), frappe.PermissionError)

	conditions = {"docstatus": 1, "date": ["between", [start, end]]}
	if filters.get("student_group"):
		conditions["student_group"] = filters.student_group
	rows = []
	start_at = 0
	while True:
		batch = frappe.get_list(
			"Student Attendance", filters=conditions,
			fields=["date", "student_group", "course_schedule", "student", "student_name", "status", "padars_late_minutes", "leave_application"],
			order_by="date asc, student_group asc, student_name asc", start=start_at, page_length=1000,
		)
		rows.extend(batch)
		if len(batch) < 1000:
			break
		start_at += 1000
	columns = [
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 95},
		{"label": _("Student Group"), "fieldname": "student_group", "fieldtype": "Link", "options": "Student Group", "width": 190},
		{"label": _("Session"), "fieldname": "course_schedule", "fieldtype": "Link", "options": "Course Schedule", "width": 185},
		{"label": _("Student"), "fieldname": "student", "fieldtype": "Link", "options": "Student", "width": 170},
		{"label": _("Student Name"), "fieldname": "student_name", "fieldtype": "Data", "width": 180},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 95},
		{"label": _("Late Minutes"), "fieldname": "padars_late_minutes", "fieldtype": "Int", "width": 100},
		{"label": _("Leave Application"), "fieldname": "leave_application", "fieldtype": "Link", "options": "Student Leave Application", "width": 190},
	]
	return columns, rows
