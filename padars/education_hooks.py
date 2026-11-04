import frappe
from frappe import _


def validate_program_enrollment(doc, method=None):
	if not frappe.get_meta("Program Enrollment").has_field("padars_school") or not doc.padars_school:
		return

	_validate_student_membership(doc.student, doc.padars_school)


def validate_student_group(doc, method=None):
	if not frappe.get_meta("Student Group").has_field("padars_school") or not doc.padars_school:
		return

	for row in doc.students:
		_validate_student_membership(row.student, doc.padars_school)


def _validate_student_membership(student, school):
	user = frappe.db.get_value("Student", student, "user")
	if not user or not frappe.db.exists(
		"School Membership", {"school": school, "user": user, "status": "Active"}
	):
		frappe.throw(
			_("Student {0} must have an active User membership in School {1}.").format(student, school)
		)

