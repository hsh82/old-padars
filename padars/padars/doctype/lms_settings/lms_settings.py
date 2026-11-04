import frappe
from frappe import _
from frappe.model.document import Document


class LMSSettings(Document):
	def validate(self):
		if self.adapter == "Moodle" and (not self.base_url or not self.api_token):
			frappe.throw(_("Base URL and API Token are required for the live Moodle adapter."))

