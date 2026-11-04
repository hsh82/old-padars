import frappe
from frappe import _
from frappe.model.document import Document

from padars.permissions import has_school_access, has_school_membership


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
		if self.local_doctype not in ALLOWED_LOCAL_DOCTYPES:
			frappe.throw(_("Local DocType {0} cannot be mapped by Padars.").format(self.local_doctype))
		if not frappe.db.exists(self.local_doctype, self.local_name):
			frappe.throw(_("Local record {0} does not exist.").format(self.local_name))
		if not has_school_access(self.school):
			frappe.throw(_("You do not have access to School {0}.").format(self.school), frappe.PermissionError)
		if self._get_local_school() != self.school:
			frappe.throw(_("The mapping School must match the local record's School."))
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
			memberships = frappe.get_all(
				"School Membership",
				filters={"school": self.school, "user": self.local_name, "status": "Active"},
				pluck="name",
				ignore_permissions=True,
			)
			return self.school if memberships else None
		if self.local_doctype == "Student":
			user = frappe.db.get_value("Student", self.local_name, "user")
			return self.school if user and has_school_membership(self.school, user=user) else None
		if self.local_doctype == "Instructor":
			return self.school if has_school_membership(self.school, instructor=self.local_name) else None

