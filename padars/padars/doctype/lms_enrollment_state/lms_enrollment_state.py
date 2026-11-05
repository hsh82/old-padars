import frappe
from frappe import _
from frappe.model.document import Document

from padars.permissions import get_teacher_instructors, has_school_access


class LMSEnrollmentState(Document):
	def validate(self):
		if not has_school_access(self.school):
			frappe.throw(_("You do not have access to School {0}.").format(self.school), frappe.PermissionError)
		offering_school = frappe.db.get_value("School Course Offering", self.course_offering, "school")
		if not offering_school:
			frappe.throw(_("Course Offering {0} does not exist.").format(self.course_offering))
		if offering_school != self.school:
			frappe.throw(_("The enrollment state School must match the Course Offering School."))
		if not frappe.db.exists("User", {"name": self.user, "enabled": 1}):
			frappe.throw(_("The User must be enabled."))
		if self.role == "Student" and not frappe.db.exists("Student", {"user": self.user, "enabled": 1}):
			frappe.throw(_("The Student enrollment User must be linked to an enabled Student."))
		if self.role == "Teacher":
			instructor = frappe.db.get_value("School Course Offering", self.course_offering, "instructor")
			if not instructor or instructor not in get_teacher_instructors(self.user, self.school):
				frappe.throw(_("The Teacher must be assigned to the Course Offering's Instructor."))
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

