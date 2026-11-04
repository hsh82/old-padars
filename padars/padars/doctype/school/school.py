import frappe
from frappe import _
from frappe.model.document import Document


class School(Document):
	def validate(self):
		if self.current_academic_year and not frappe.db.exists(
			"Academic Year", self.current_academic_year
		):
			frappe.throw(_("Current Academic Year {0} does not exist.").format(self.current_academic_year))

