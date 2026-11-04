import frappe
from frappe import _
from frappe.model.document import Document


class LMSSyncOperation(Document):
	def validate(self):
		if not frappe.db.exists(self.target_doctype, self.target_name):
			frappe.throw(_("Target record {0} does not exist.").format(self.target_name))
		if self.target_doctype == "School Course Offering":
			target_school = frappe.db.get_value(self.target_doctype, self.target_name, "school")
			if target_school != self.school:
				frappe.throw(_("The operation School must match the target School."))

		if self.get_doc_before_save() and self.state != self.get_doc_before_save().state:
			allowed = {
				"Pending": {"Queued", "Running", "Failed"},
				"Queued": {"Running", "Failed"},
				"Running": {"Succeeded", "Failed"},
				"Failed": {"Queued"},
				"Succeeded": set(),
			}
			old_state = self.get_doc_before_save().state
			if self.state not in allowed.get(old_state, set()):
				frappe.throw(_("Invalid sync state transition from {0} to {1}.").format(old_state, self.state))

