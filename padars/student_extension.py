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
