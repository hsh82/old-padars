"""Education Student extension for the verified provisional onboarding path."""

import frappe

_ONBOARDING = object()


class StudentOnboardingExtension:
	def update_linked_customer(self):
		# Education saves the linked Customer even for relationship-only changes.
		# Avoid that unrelated write when all synchronized fields already match.
		customer = frappe.get_doc("Customer", self.customer)
		if (customer.customer_name == self.student_name
			and (customer.image or "") == (self.image or "")
			and (not self.customer_group or customer.customer_group == self.customer_group)):
			return
		old = self.get_doc_before_save()
		if (old and old.customer == self.customer
			and (not self.customer_group or self.customer_group == customer.customer_group)
			and frappe.has_permission("Student", "write", self)
			and not frappe.has_permission("Customer", "write", customer)):
			# A permitted academic name/image update projects only to its existing
			# Education-owned customer link. Financial fields and grouping stay intact.
			customer.customer_name = self.student_name
			customer.image = self.image
			customer.save(ignore_permissions=True)
			return
		return super().update_linked_customer()

	def set_missing_customer_details(self):
		if getattr(frappe.flags, "padars_onboarding_student", None) is not _ONBOARDING:
			return super().set_missing_customer_details()
		# Only a new, server-constructed Student can enter this branch.
		if self.customer:
			raise frappe.PermissionError
		self.set_customer_group()
		customer = frappe.get_doc({"doctype": "Customer", "customer_name": self.student_name,
			"customer_group": self.customer_group or frappe.db.get_single_value("Selling Settings", "customer_group"),
			"customer_type": "Individual", "image": self.image}).insert(ignore_permissions=True)
		frappe.db.set_value("Student", self.name, "customer", customer.name)


def validate_customer_projection_binding(doc, method=None):
	"""An academic Student write cannot retarget arbitrary ERPNext customers."""
	old = doc.get_doc_before_save()
	changed = bool((old and old.customer != doc.customer) or (not old and doc.customer))
	group_changed = bool((old and doc.customer_group != old.customer_group)
		or (not old and doc.customer_group and doc.customer_group != "Student"))
	if changed or group_changed:
		allowed = frappe.has_permission("Customer", "write") and (not doc.customer or frappe.has_permission("Customer", "write", doc.customer))
		if not allowed:
			frappe.throw(frappe._("Customer bindings and groups require customer-management authority."), frappe.PermissionError)
