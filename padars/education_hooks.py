import frappe
from frappe import _

from padars.permissions import has_school_access, has_school_membership


def validate_student_identity(doc, method=None):
	if doc.student_email_id and not doc.user:
		existing_user = frappe.db.get_value("User", doc.student_email_id, "name")
		if existing_user:
			existing_student = frappe.db.get_value(
				"Student", {"user": existing_user, "name": ["!=", doc.name]}, "name"
			)
			if existing_student:
				frappe.throw(
					_("Student {0} already uses this email/User. Reuse the existing Student record.").format(
						existing_student
					)
				)
			doc.user = existing_user

	if doc.user and frappe.db.exists("Student", {"user": doc.user, "name": ["!=", doc.name]}):
		frappe.throw(_("This Frappe User is already linked to another Student record."))


def validate_program_enrollment(doc, method=None):
	if not frappe.get_meta("Program Enrollment").has_field("padars_school") or not doc.padars_school:
		return

	_validate_school_context(doc.padars_school)
	_validate_student_membership(doc.student, doc.padars_school)


def validate_student_group(doc, method=None):
	if not frappe.get_meta("Student Group").has_field("padars_school") or not doc.padars_school:
		return

	_validate_school_context(doc.padars_school)
	for row in doc.students:
		_validate_student_membership(
			row.student,
			doc.padars_school,
			academic_year=doc.academic_year,
			program=doc.program,
		)
	for row in doc.instructors:
		if row.instructor and not has_school_membership(
			doc.padars_school, instructor=row.instructor
		):
			frappe.throw(
				_("Instructor {0} must have an active membership in School {1}.").format(
					row.instructor, doc.padars_school
				)
			)


def _validate_school_context(school):
	if not frappe.db.exists("School", {"name": school, "status": "Active"}):
		frappe.throw(_("School {0} does not exist or is inactive.").format(school))
	if not has_school_access(school):
		frappe.throw(_("You do not have access to School {0}.").format(school), frappe.PermissionError)


def _validate_student_membership(student, school, academic_year=None, program=None):
	student_data = frappe.db.get_value("Student", student, ["user", "enabled"], as_dict=True)
	if not student_data or not student_data.user or not student_data.enabled:
		frappe.throw(
			_("Student {0} must be enabled and have an active User membership in School {1}.").format(
				student, school
			)
		)
	if not has_school_membership(school, user=student_data.user):
		frappe.throw(
			_("Student {0} must have an active User membership in School {1}.").format(student, school)
		)

	if academic_year and frappe.get_meta("Program Enrollment").has_field("padars_school"):
		filters = {
			"student": student,
			"padars_school": school,
			"academic_year": academic_year,
			"docstatus": 1,
		}
		if program:
			filters["program"] = program
		if not frappe.db.exists("Program Enrollment", filters):
			frappe.throw(
				_("Student {0} must have a submitted enrollment for School {1} and Academic Year {2}.").format(
					student, school, academic_year
				)
			)


def validate_linked_education_context(doc, method=None):
	if doc.doctype == "Student Attendance":
		school = frappe.db.get_value("Student Group", doc.student_group, "padars_school")
		if school:
			_validate_school_context(school)
		return

	if not frappe.get_meta(doc.doctype).has_field("padars_course_offering"):
		return
	offering_name = doc.get("padars_course_offering")
	if not offering_name:
		return
	offering = frappe.db.get_value(
		"School Course Offering",
		offering_name,
		["school", "academic_year", "program", "course", "student_group"],
		as_dict=True,
	)
	if not offering:
		frappe.throw(_("School Course Offering {0} does not exist.").format(offering_name))
	_validate_school_context(offering.school)
	for field in ("academic_year", "program", "course", "student_group"):
		if doc.get(field) and doc.get(field) != offering.get(field):
			frappe.throw(
				_("{0} must match School Course Offering {1}.").format(
					field.replace("_", " "), offering_name
				)
			)

