import frappe
from frappe import _
from frappe.model.document import Document


class LMSEnrollmentState(Document):
	def validate(self):
		offering_school = frappe.db.get_value("School Course Offering", self.course_offering, "school")
		if offering_school != self.school:
			frappe.throw(_("The enrollment state School must match the Course Offering School."))
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

