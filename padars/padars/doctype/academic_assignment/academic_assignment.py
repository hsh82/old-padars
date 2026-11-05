import hashlib

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


SCOPE_TYPES = {"Program", "Student Group", "School Course Offering"}


class AcademicAssignment(Document):
	def validate(self):
		if self.scope_type not in SCOPE_TYPES:
			frappe.throw(_("Choose a Program, Student Group, or School Course Offering scope."))
		if not frappe.db.exists(self.scope_type, self.scope_name):
			frappe.throw(_("The selected academic scope does not exist."))
		if not frappe.db.exists("User", {"name": self.user, "enabled": 1}):
			frappe.throw(_("The assigned User must be enabled."))
		if self.valid_from and self.valid_to and getdate(self.valid_from) > getdate(self.valid_to):
			frappe.throw(_("Valid To cannot be earlier than Valid From."))
		if self.instructor and self.scope_type == "School Course Offering":
			offering_instructor = frappe.db.get_value("School Course Offering", self.scope_name, "instructor")
			if offering_instructor != self.instructor:
				frappe.throw(_("Instructor must match the Course Offering's Instructor."))
		identity = "\0".join((self.user, self.scope_type, self.scope_name))
		self.active_key = hashlib.sha256(identity.encode()).hexdigest() if self.status == "Active" else None
