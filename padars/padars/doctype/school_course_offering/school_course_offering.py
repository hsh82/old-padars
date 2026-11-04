import frappe
from frappe import _
from frappe.model.document import Document

from padars.permissions import has_school_access, has_school_membership


class SchoolCourseOffering(Document):
	def validate(self):
		self.validate_school()
		self.validate_education_context()
		self.validate_instructor_membership()
		self.validate_duplicate()

	def validate_school(self):
		if not frappe.db.exists("School", self.school):
			frappe.throw(_("School {0} does not exist.").format(self.school))
		if frappe.db.get_value("School", self.school, "status") != "Active":
			frappe.throw(_("School {0} is not active.").format(self.school))
		if not has_school_access(self.school):
			frappe.throw(_("You do not have access to School {0}.").format(self.school), frappe.PermissionError)

	def validate_education_context(self):
		group = frappe.db.get_value(
			"Student Group",
			self.student_group,
			["academic_year", "program", "course", "group_based_on"],
			as_dict=True,
		)
		if not group:
			frappe.throw(_("Student Group {0} does not exist.").format(self.student_group))
		if group.academic_year != self.academic_year:
			frappe.throw(_("The Student Group must belong to the offering's Academic Year."))
		if group.program and group.program != self.program:
			frappe.throw(_("The Student Group Program does not match the offering."))
		if group.group_based_on == "Course" and group.course != self.course:
			frappe.throw(_("The Student Group Course does not match the offering."))

		if frappe.get_meta("Student Group").has_field("padars_school"):
			group_school = frappe.db.get_value("Student Group", self.student_group, "padars_school")
			if group_school != self.school:
				frappe.throw(_("The Student Group belongs to another School."))

	def validate_instructor_membership(self):
		if self.instructor and not has_school_membership(self.school, instructor=self.instructor):
			frappe.throw(_("The Instructor must have an active membership in this School."))

	def validate_duplicate(self):
		if frappe.db.exists(
			"School Course Offering",
			{
				"school": self.school,
				"academic_year": self.academic_year,
				"course": self.course,
				"student_group": self.student_group,
				"offering_identifier": self.offering_identifier,
				"name": ["!=", self.name],
			},
		):
			frappe.throw(_("A matching School Course Offering already exists."))

