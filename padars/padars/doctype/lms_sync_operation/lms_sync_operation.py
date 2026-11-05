import frappe
from frappe import _
from frappe.model.document import Document

from padars.permissions import has_school_access


MAX_SYNC_ATTEMPTS = 5
SUPPORTED_OPERATIONS = {
	"Provision Tenant": "School",
	"Provision User": "User",
	"Provision Course": "School Course Offering",
	"Sync Enrollment": "LMS Enrollment State",
}


class LMSSyncOperation(Document):
	def validate(self):
		if not has_school_access(self.school):
			frappe.throw(_("You do not have access to School {0}.").format(self.school), frappe.PermissionError)
		if SUPPORTED_OPERATIONS.get(self.operation_type) != self.target_doctype:
			frappe.throw(
				_("Operation {0} requires target DocType {1}.").format(
					self.operation_type, SUPPORTED_OPERATIONS.get(self.operation_type, "a supported target")
				)
			)
		if not frappe.db.exists(self.target_doctype, self.target_name):
			frappe.throw(_("Target record {0} does not exist.").format(self.target_name))
		target_school = self._get_target_school()
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
		elif not self.get_doc_before_save() and self.state not in {"Pending", "Queued"}:
			frappe.throw(_("A new sync operation must start in Pending or Queued state."))
		if (self.attempt_count or 0) < 0 or (self.attempt_count or 0) > MAX_SYNC_ATTEMPTS:
			frappe.throw(_("Sync attempt count is outside the allowed range."))

	def _get_target_school(self):
		if self.target_doctype in {"School", "School Course Offering", "LMS Enrollment State"}:
			return frappe.db.get_value(self.target_doctype, self.target_name, "name" if self.target_doctype == "School" else "school")
		if self.target_doctype == "User":
			return self.school if frappe.db.exists("User", {"name": self.target_name, "enabled": 1}) else None
		return None

