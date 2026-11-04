import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class SchoolMembership(Document):
	def validate(self):
		if not self.user and not self.instructor:
			frappe.throw(_("A membership must identify a User or Instructor."))
		if self.valid_from and self.valid_to and getdate(self.valid_from) > getdate(self.valid_to):
			frappe.throw(_("Valid To cannot be earlier than Valid From."))

		filters = {
			"school": self.school,
			"school_role": self.school_role,
			"status": self.status,
			"name": ["!=", self.name],
		}
		if self.user:
			filters["user"] = self.user
		if self.instructor:
			filters["instructor"] = self.instructor
		if frappe.db.exists("School Membership", filters):
			frappe.throw(_("This active school membership already exists."))

