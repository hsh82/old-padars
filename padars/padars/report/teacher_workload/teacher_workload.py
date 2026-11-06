import frappe
from frappe import _

from padars.staff import get_teacher_workload_data


def execute(filters=None):
	columns = [
		{"label": _("Instructor"), "fieldname": "instructor", "fieldtype": "Link", "options": "Instructor", "width": 160},
		{"label": _("Instructor Name"), "fieldname": "instructor_name", "fieldtype": "Data", "width": 190},
		{"label": _("Frappe User"), "fieldname": "user", "fieldtype": "Link", "options": "User", "width": 180},
		{"label": _("Course Offerings"), "fieldname": "offering_count", "fieldtype": "Int", "width": 130},
		{"label": _("Expected Weekly Hours"), "fieldname": "expected_weekly_hours", "fieldtype": "Float", "width": 170},
	]
	return columns, get_teacher_workload_data(frappe._dict(filters or {}))
