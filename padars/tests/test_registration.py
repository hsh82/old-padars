from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from padars.registration import _identity_key, enroll_returning_student, register_batch, register_student
from padars.tests.utils import get_or_create_test_school


class TestRegistration(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.key_patch = patch.dict(frappe.local.conf, {"encryption_key": "test-only-key-do-not-use-in-production"})
		self.key_patch.start()
		frappe.db.savepoint("padars_registration_test")
		self.key = frappe.generate_hash(length=8).upper()
		self.year = frappe.get_doc({"doctype": "Academic Year", "academic_year_name": f"R-{self.key}",
			"year_start_date": "2099-01-01", "year_end_date": "2099-12-31"}).insert()
		get_or_create_test_school(self.year.name, f"R-{self.key}")
		self.program = frappe.get_doc({"doctype": "Program", "program_name": f"R-{self.key}"}).insert()
		frappe.db.set_single_value("Education Settings", "user_creation_skip", 1)
		self.row = {"first_name": "Learner", "national_id": "ID" + self.key,
			"phone": "+12025550100", "email": f"learner-{self.key}@example.invalid"}
		self.student_hook = patch("education.education.doctype.student.student.Student.on_update")
		self.student_hook.start()

	def tearDown(self):
		self.student_hook.stop()
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="padars_registration_test")
		frappe.clear_cache(doctype="Education Settings")
		self.key_patch.stop()

	def test_registration_is_repeatable_without_creating_user(self):
		result = register_student(**self.row)
		self.assertTrue(result["created"])
		self.assertFalse(register_student(**self.row)["created"])
		self.assertFalse(frappe.db.exists("User", self.row["email"]))
		self.assertNotIn(self.row["national_id"], _identity_key(self.row["national_id"]))
		self.assertEqual(_identity_key("۱۲۳۴۵۶"), _identity_key("123456"))

	def test_existing_identity_with_changed_contact_is_not_silently_reused(self):
		register_student(**self.row)
		with self.assertRaises(frappe.ValidationError):
			register_student(**{**self.row, "phone": "+12025550101"})

	def test_skip_user_creation_is_required(self):
		frappe.db.set_single_value("Education Settings", "user_creation_skip", 0)
		with self.assertRaises(frappe.ValidationError):
			register_student(**self.row)
		self.assertFalse(frappe.db.exists("Student Identity", {"identity_key": _identity_key(self.row["national_id"])}))

	def test_batch_preview_partial_success_and_retry(self):
		rows = [self.row, {**self.row, "national_id": "bad"}]
		preview = register_batch(rows, preview=1)
		self.assertEqual([r["status"] for r in preview], ["valid", "error"])
		self.assertFalse(frappe.db.exists("Student Identity", {"identity_key": _identity_key(self.row["national_id"])}))
		result = register_batch(rows, preview=0)
		self.assertEqual([r["status"] for r in result], ["success", "error"])
		self.assertFalse(register_batch([self.row], preview=0)[0]["created"])
		self.assertNotIn(self.row["national_id"], str(result))

	def test_returning_enrollment_is_a_repeatable_draft(self):
		student = register_student(**self.row)["student"]
		result = enroll_returning_student(student, self.program.name, self.year.name)
		self.assertTrue(result["created"])
		self.assertEqual(frappe.db.get_value("Program Enrollment", result["enrollment"], "docstatus"), 0)
		self.assertFalse(enroll_returning_student(student, self.program.name, self.year.name)["created"])

	def test_guest_cannot_register(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			register_student(**self.row)

	def test_registration_runs_native_student_hooks(self):
		self.student_hook.stop()
		try:
			student = register_student(**self.row)["student"]
			self.assertTrue(frappe.db.get_value("Student", student, "customer"))
		finally:
			self.student_hook.start()

	def test_school_manager_can_register_with_native_student_hooks(self):
		frappe.flags.in_import = True
		try:
			manager = frappe.get_doc({"doctype": "User", "email": f"manager-{self.key}@example.invalid",
				"first_name": "Manager", "user_type": "System User", "send_welcome_email": 0}).insert()
		finally:
			frappe.flags.in_import = False
		manager.add_roles("Padars School Manager", "Academics User")
		self.student_hook.stop()
		frappe.set_user(manager.name)
		try:
			self.assertTrue(register_student(**self.row)["student"])
		finally:
			self.student_hook.start()
