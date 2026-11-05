import frappe
from frappe import _
from frappe.model.document import Document


class School(Document):
	def validate(self):
		from padars.file_security import assert_no_protected_shares
		from padars.permissions import is_platform_admin

		if not is_platform_admin() and (self.is_new() or self.has_value_changed("status")
			or self.has_value_changed("primary_school_manager")):
			frappe.throw(_("Only a System Manager can change the primary School or manager."), frappe.PermissionError)
		# The unique nullable key also protects concurrent inserts. Inactive
		# historical records have no key and do not represent another tenant.
		self.active_site_key = "primary" if self.status == "Active" else None
		if self.status == "Active" and frappe.db.exists(
			"School", {"status": "Active", "name": ["!=", self.name or ""]}
		):
			frappe.throw(_("Only one active School is allowed on a site."))
		if self.status == "Active":
			assert_no_protected_shares()
		if self.current_academic_year and not frappe.db.exists(
			"Academic Year", self.current_academic_year
		):
			frappe.throw(_("Current Academic Year {0} does not exist.").format(self.current_academic_year))
		if self.primary_school_manager and not frappe.db.exists(
			"User", {"name": self.primary_school_manager, "enabled": 1, "user_type": "System User"}
		):
			frappe.throw(_("Primary School Manager must be an enabled System User."))

	def on_update(self):
		if self.primary_school_manager and (self.is_new() or self.has_value_changed("primary_school_manager")):
			frappe.get_doc("User", self.primary_school_manager).add_roles("Padars School Manager", "Academics User")

