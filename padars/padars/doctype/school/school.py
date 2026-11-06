import frappe
from frappe import _
from frappe.model.document import Document
from uuid import uuid4


class School(Document):
	def validate(self):
		from padars.file_security import assert_no_protected_shares
		from padars.permissions import is_lms_operator, is_platform_admin

		if self.is_new():
			self.lms_installation_uuid = self.lms_installation_uuid or uuid4().hex
			self.lms_origin_site = self.lms_origin_site or frappe.local.site
		elif not frappe.flags.get("padars_lms_service_update"):
			old = self.get_doc_before_save()
			if old:
				binding_fields = (
					"lms_installation_uuid", "lms_origin_site", "lms_provisioned", "lms_tenant_name",
					"lms_tenant_id", "lms_tenant_idnumber", "lms_course_category_id",
					"lms_tenant_cohort_id", "lms_associated_cohort_id", "lms_moodle_url",
					"lms_status", "lms_last_sync", "lms_last_error", "lms_provisioning_generation",
				)
				if any(self.get(field) != old.get(field) for field in binding_fields):
					frappe.throw(_("Moodle tenant bindings and synchronization state are managed by Padars."), frappe.PermissionError)
				if self.lms_enabled != old.lms_enabled and not is_lms_operator():
					frappe.throw(_("Only company Moodle operators can enable or disable Moodle."), frappe.PermissionError)
				if self.lms_auto_enrollment != old.lms_auto_enrollment and not is_lms_operator():
					frappe.throw(_("Only company Moodle operators can change automatic Moodle enrollment."), frappe.PermissionError)
		if self.is_new() and self.lms_enabled and not is_lms_operator():
			frappe.throw(_("Only company Moodle operators can enable Moodle."), frappe.PermissionError)
		if self.has_value_changed("lms_enabled"):
			if not is_lms_operator():
				frappe.throw(_("Only company Moodle operators can enable or disable Moodle."), frappe.PermissionError)
			if self.lms_enabled:
				if self.status != "Active":
					frappe.throw(_("Moodle can be enabled only for an active School."))
				self.lms_provisioning_generation = int(self.lms_provisioning_generation or 0) + 1
				self.lms_status = "Provisioning"
				self.lms_last_error = None
			else:
				self.lms_status = "Disabled"

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
		if not self.lms_installation_uuid or len(self.lms_installation_uuid) != 32:
			frappe.throw(_("School LMS installation identity must be a 32-character UUID."))
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
			from padars.role_profiles import grant_fixed_role
			grant_fixed_role(frappe.get_doc("User", self.primary_school_manager), "Padars School Manager")
		if self.has_value_changed("lms_enabled") and self.lms_enabled:
			from padars.integrations.moodle.service import request_school_tenant_sync

			request_school_tenant_sync(self)
		elif self.has_value_changed("lms_auto_enrollment") and self.lms_enabled and self.lms_auto_enrollment:
			from padars.integrations.moodle.service import queue_school_auto_enrollment

			queue_school_auto_enrollment(self.name)

