import frappe
from frappe import _
from frappe.model.document import Document


class LMSSettings(Document):
	def validate(self):
		from padars.permissions import is_lms_operator
		from padars.integrations.moodle.rest import validate_moodle_base_url

		if not is_lms_operator():
			frappe.throw(_("Only company Moodle operators can change LMS connection settings."), frappe.PermissionError)
		if int(self.connection_timeout or 0) < 1 or int(self.connection_timeout or 0) > 120:
			frappe.throw(_("Connection timeout must be between 1 and 120 seconds."))
		if int(self.default_member_limit or 0) < 0:
			frappe.throw(_("Default tenant member limit cannot be negative."))
		for field in ("teacher_role_id", "student_role_id", "school_manager_role_id"):
			if int(self.get(field) or 0) < 0:
				frappe.throw(_("Moodle role IDs cannot be negative."))
		if self.enabled and self.adapter == "Moodle":
			if not self.base_url or not self.get_password("api_token", raise_exception=False):
				frappe.throw(_("Base URL and API Token are required for the live Moodle adapter."))
			try:
				self.base_url = validate_moodle_base_url(
					self.base_url, frappe.conf.get("padars_moodle_allowed_hosts")
				)
			except (TypeError, ValueError) as exc:
				frappe.throw(_("Invalid Moodle connection URL: {0}").format(str(exc)))

