import frappe
from frappe import _
from frappe.model.document import Document

from padars.permissions import has_school_access


class SchoolCourseOffering(Document):
	def validate(self):
		self.validate_school()
		self.validate_education_context()
		from padars.curriculum import validate_offering_curriculum
		validate_offering_curriculum(self)
		self.validate_instructor()
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

	def validate_instructor(self):
		old = self.get_doc_before_save()
		changed = (not old and bool(self.instructor)) or (old and old.instructor != self.instructor)
		if changed and not frappe.flags.get("padars_teacher_assignment_update"):
			frappe.throw(_("Use Assign Teacher to update this Course Offering."), frappe.PermissionError)
		if self.instructor:
			instructor = frappe.db.get_value("Instructor", self.instructor,
				["status", "padars_user"], as_dict=True)
			if not instructor or instructor.status != "Active" or not instructor.padars_user:
				frappe.throw(_("The Instructor must be active and linked to a Frappe User."))
			user = frappe.db.get_value("User", instructor.padars_user, ["enabled", "user_type"], as_dict=True)
			if not user or not user.enabled or user.user_type != "System User":
				frappe.throw(_("The Instructor's Frappe User must be enabled."))
			if "Padars Teacher" not in frappe.get_roles(instructor.padars_user):
				frappe.throw(_("The Instructor's User must have the Padars Teacher role."))

	def validate_duplicate(self):
		if frappe.db.exists(
			"School Course Offering",
			{
				"school": self.school,
				"academic_year": self.academic_year,
				"course": self.course,
				"student_group": self.student_group,
				"name": ["!=", self.name],
			},
		):
			frappe.throw(_("A matching School Course Offering already exists."))

