import frappe
from frappe import _
from frappe.model.document import Document

from padars.permissions import has_school_access, has_school_membership


class LMSEnrollmentState(Document):
	def validate(self):
		if not has_school_access(self.school):
			frappe.throw(_("You do not have access to School {0}.").format(self.school), frappe.PermissionError)
		offering_school = frappe.db.get_value("School Course Offering", self.course_offering, "school")
		if not offering_school:
			frappe.throw(_("Course Offering {0} does not exist.").format(self.course_offering))
		if offering_school != self.school:
			frappe.throw(_("The enrollment state School must match the Course Offering School."))
		if not has_school_membership(self.school, user=self.user):
			frappe.throw(_("The User must have an active membership in this School."))
		if self.role == "Student" and not frappe.db.exists("Student", {"user": self.user, "enabled": 1}):
			frappe.throw(_("The Student enrollment User must be linked to an enabled Student."))
		if self.role == "Teacher" and not frappe.db.exists(
			"School Membership",
			{
				"school": self.school,
				"user": self.user,
				"status": "Active",
				"school_role": ["in", ["Teacher", "Academic Staff"]],
			},
		):
			frappe.throw(_("The Teacher enrollment User must have an instructor membership."))
		if frappe.db.exists(
			"LMS Enrollment State",
			{
				"user": self.user,
				"course_offering": self.course_offering,
				"role": self.role,
				"name": ["!=", self.name],
			},
		):
			frappe.throw(_("This user already has an enrollment state for this offering and role."))

