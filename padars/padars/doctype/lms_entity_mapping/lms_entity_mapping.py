import frappe
from frappe import _
from frappe.model.document import Document


class LMSEntityMapping(Document):
	def validate(self):
		if not frappe.db.exists(self.local_doctype, self.local_name):
			frappe.throw(_("Local record {0} does not exist.").format(self.local_name))
		if frappe.db.exists(
			"LMS Entity Mapping",
			{
				"local_doctype": self.local_doctype,
				"local_name": self.local_name,
				"remote_context": self.remote_context,
				"name": ["!=", self.name],
			},
		):
			frappe.throw(_("This local record is already mapped in the remote context."))
		if frappe.db.exists(
			"LMS Entity Mapping",
			{
				"remote_type": self.remote_type,
				"remote_id": self.remote_id,
				"remote_context": self.remote_context,
				"name": ["!=", self.name],
			},
		):
			frappe.throw(_("This remote entity is already mapped to another local record."))

