import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class SchoolMembership(Document):
	def validate(self):
		if not self.user and not self.instructor:
			frappe.throw(_("A membership must identify a User or Instructor."))
		if not frappe.db.exists("School", {"name": self.school, "status": "Active"}):
			frappe.throw(_("Membership School {0} does not exist or is inactive.").format(self.school))
		if self.school_role in {"Student", "Guardian", "School Administrator"} and not self.user:
			frappe.throw(_("This School Role requires a User."))
		if self.school_role in {"Academic Staff", "Teacher"} and not self.instructor:
			frappe.throw(_("This School Role requires an Instructor."))
		if self.valid_from and self.valid_to and getdate(self.valid_from) > getdate(self.valid_to):
			frappe.throw(_("Valid To cannot be earlier than Valid From."))
		if self.status != "Active":
			return

		filters = {
			"school": self.school,
			"school_role": self.school_role,
			"status": "Active",
			"name": ["!=", self.name],
		}
		if self.user:
			filters["user"] = self.user
		if self.instructor:
			filters["instructor"] = self.instructor
		if frappe.db.exists("School Membership", filters):
			frappe.throw(_("This active school membership already exists."))

