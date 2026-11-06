import hashlib

import frappe
from frappe import _
from frappe.model.document import Document

from padars.permissions import has_school_access


ALLOWED_LOCAL_DOCTYPES = {
	"School",
	"User",
	"Student",
	"Instructor",
	"School Course Offering",
	"LMS Enrollment State",
}


class LMSEntityMapping(Document):
	def validate(self):
		self.local_mapping_key = hashlib.sha256(
			f"{self.local_doctype}\0{self.local_name}".encode()
		).hexdigest()
		self.remote_mapping_key = hashlib.sha256(
			f"{self.remote_context}\0{self.remote_type}\0{self.remote_id}".encode()
		).hexdigest()
		if self.local_doctype not in ALLOWED_LOCAL_DOCTYPES:
			frappe.throw(_("Local DocType {0} cannot be mapped by Padars.").format(self.local_doctype))
		if not frappe.db.exists(self.local_doctype, self.local_name):
			frappe.throw(_("Local record {0} does not exist.").format(self.local_name))
		if not has_school_access(self.school):
			frappe.throw(_("You do not have access to School {0}.").format(self.school), frappe.PermissionError)
		if self._get_local_school() != self.school:
			frappe.throw(_("The mapping School must match the local record's School."))
		old = self.get_doc_before_save()
		if old and not frappe.flags.get("padars_lms_service_update") and any(
			old.get(field) != self.get(field)
			for field in ("local_doctype", "local_name", "remote_type", "remote_id", "remote_context", "remote_url")
		):
			frappe.throw(_("LMS entity mappings are immutable and managed by Padars."), frappe.PermissionError)
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

	def _get_local_school(self):
		if self.local_doctype == "School":
			return self.local_name
		if self.local_doctype in {"School Course Offering", "LMS Enrollment State"}:
			return frappe.db.get_value(self.local_doctype, self.local_name, "school")
		if self.local_doctype == "User":
			return self.school if frappe.db.exists("User", {"name": self.local_name, "enabled": 1}) else None
		if self.local_doctype == "Student":
			return self.school if frappe.db.exists("Student", {"name": self.local_name, "enabled": 1}) else None
		if self.local_doctype == "Instructor":
			return self.school if frappe.db.exists("Instructor", {"name": self.local_name, "status": "Active"}) else None

