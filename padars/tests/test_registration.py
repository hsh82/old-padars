from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
import csv
import tempfile

import frappe
from cryptography.fernet import Fernet
from frappe.core.doctype.data_import.importer import ImportFile, INSERT
from frappe.tests.utils import FrappeTestCase

from padars.registration import _identity_key, _phone, enroll_returning_student, register_student
from padars.student_import import StudentImportProvider, validate_import
from padars.student_activation import activate, send_activation_code
from padars.student_activation import resolve_student_login
from padars import student_application
from padars.file_security import validate_private_attachment
from padars.tests.utils import get_or_create_test_school


class TestRegistration(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.key_patch = patch.dict(frappe.local.conf, {"encryption_key": Fernet.generate_key().decode()})
		self.key_patch.start()
		frappe.db.savepoint("padars_registration_test")
		self.key = frappe.generate_hash(length=8).upper()
		self.year = frappe.get_doc({"doctype": "Academic Year", "academic_year_name": f"R-{self.key}",
			"year_start_date": "2099-01-01", "year_end_date": "2099-12-31"}).insert()
		get_or_create_test_school(self.year.name, f"R-{self.key}")
		self.program = frappe.get_doc({"doctype": "Program", "program_name": f"R-{self.key}"}).insert()
		frappe.db.set_single_value("Education Settings", "user_creation_skip", 1)
		prefix = str(int(self.key, 16) % 900000000 + 100000000)
		remainder = sum(int(prefix[i]) * (10 - i) for i in range(9)) % 11
		self.row = {"first_name": "Learner", "national_id": prefix + str(remainder if remainder < 2 else 11 - remainder),
			"phone": "09121234567", "email": f"learner-{self.key}@example.invalid"}
		self.student_hook = patch("education.education.doctype.student.student.Student.on_update")
		self.student_hook.start()

	def tearDown(self):
		self.student_hook.stop()
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="padars_registration_test")
		frappe.clear_cache(doctype="Education Settings")
		self.key_patch.stop()

	def test_registration_is_repeatable_with_disabled_user(self):
		result = register_student(**self.row)
		self.assertTrue(result["created"])
		self.assertFalse(register_student(**self.row)["created"])
		self.assertFalse(frappe.db.get_value("User", self.row["email"].lower(), "enabled"))
		self.assertNotIn(self.row["national_id"], _identity_key(self.row["national_id"]))
		self.assertEqual(_identity_key(self.row["national_id"].translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))), _identity_key(self.row["national_id"]))
		self.assertEqual(_phone("09121234567"), "+989121234567")
		with self.assertRaises(frappe.ValidationError):
			_identity_key("1111111111")

	def test_existing_identity_with_changed_contact_is_not_silently_reused(self):
		register_student(**self.row)
		with self.assertRaises(frappe.ValidationError):
			register_student(**{**self.row, "phone": "09121234568"})

	def test_first_login_requires_a_new_password(self):
		from frappe.utils.password import check_password
		register_student(**self.row)
		user = self.row["email"].lower()
		self.assertEqual(check_password(user, self.row["phone"]), user)
		with self.assertRaises(frappe.ValidationError):
			activate(self.row["national_id"], self.row["phone"], self.row["phone"])
		self.assertFalse(frappe.db.get_value("User", user, "enabled"))
		activate(self.row["national_id"], self.row["phone"], "Raven!Cloud87Train")
		self.assertTrue(frappe.db.get_value("User", user, "enabled"))
		self.assertEqual(check_password(user, "Raven!Cloud87Train"), user)
		with patch.object(frappe.local, "form_dict", frappe._dict(usr=self.row["national_id"])):
			resolve_student_login(None)
			self.assertEqual(frappe.form_dict.usr, user)
		with self.assertRaises(frappe.AuthenticationError):
			activate(self.row["national_id"], self.row["phone"], "Raven!Cloud87Train")

	def test_enabled_sms_verification_cannot_be_bypassed(self):
		import pyotp
		register_student(**self.row)
		captured = {}
		callbacks = []
		def send(secret, token, phone_no):
			captured["otp"] = pyotp.HOTP(secret).at(token)
			return True
		with patch("padars.student_activation._sms_required", return_value=True), patch("padars.student_activation._sms_configured", return_value=True), patch("frappe.twofactor.send_token_via_sms", side_effect=send), patch.object(type(frappe.db.after_commit), "add", lambda self, callback: callbacks.append(callback)):
			with self.assertRaises(frappe.AuthenticationError):
				activate(self.row["national_id"], self.row["phone"], "Raven!Cloud87Train")
			send_activation_code(self.row["national_id"], self.row["phone"])
			self.assertFalse(captured)
			callbacks.pop()()
			with self.assertRaises(frappe.AuthenticationError):
				activate(self.row["national_id"], self.row["phone"], "Raven!Cloud87Train", otp="wrong")
			self.assertTrue(activate(self.row["national_id"], self.row["phone"], "Raven!Cloud87Train", otp=captured["otp"])["activated"])

	def test_sms_enabled_without_provider_does_not_fall_back(self):
		register_student(**self.row)
		with patch("padars.student_activation._sms_required", return_value=True), patch("padars.student_activation._sms_configured", return_value=False):
			with self.assertRaises(frappe.ValidationError):
				send_activation_code(self.row["national_id"], self.row["phone"])
			with self.assertRaises(frappe.AuthenticationError):
				activate(self.row["national_id"], self.row["phone"], "Raven!Cloud87Train")
		self.assertFalse(frappe.db.get_value("User", self.row["email"].lower(), "enabled"))

	def test_native_import_provider_reuses_identity(self):
		provider = StudentImportProvider()
		provider.doctype = "Student"
		importer = frappe._dict(import_type="Insert New Records")
		student, action = provider.import_row(importer, frappe._dict(self.row))
		self.assertEqual(action, "Insert")
		existing, action = provider.import_row(importer, frappe._dict(self.row))
		self.assertEqual(existing.name, student.name)
		self.assertEqual(action, "Update")

	def test_student_import_rejects_external_or_public_file(self):
		with self.assertRaises(frappe.ValidationError):
			validate_import(frappe._dict(reference_doctype="Student", google_sheets_url="https://example.invalid", import_file=None))
		with self.assertRaises(frappe.ValidationError):
			validate_import(frappe._dict(reference_doctype="Student", google_sheets_url=None, import_file="/files/students.csv"))
		with patch("frappe.db.get_value", return_value="Student"):
			with self.assertRaises(frappe.PermissionError):
				validate_private_attachment(frappe._dict(attached_to_doctype="Data Import", attached_to_name="test", is_private=0, file_url="/files/students.csv"))

	def test_public_application_requires_consent_and_staff_approval(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.ValidationError):
			student_application.submit(**self.row, guardian_consent=0)
		result = student_application.submit(**self.row, guardian_consent=1)
		self.assertEqual(student_application.status(result["status_token"])["status"], "Submitted")
		student_application.update_details(result["status_token"], "Updated", self.row["email"])
		self.assertFalse(frappe.db.exists("Student Identity", {"identity_key": _identity_key(self.row["national_id"])}))
		application = frappe.db.get_value("Student Registration Application", {"identity_key": _identity_key(self.row["national_id"])}, "name")
		with self.assertRaises(frappe.PermissionError):
			student_application.approve(application)
		frappe.set_user("Administrator")
		approved = student_application.approve(application)
		self.assertTrue(approved["created"])
		self.assertEqual(student_application.status(result["status_token"])["status"], "Approved")
		self.assertFalse(student_application.approve(application)["created"])
		with self.assertRaises(frappe.AuthenticationError):
			student_application.status("invalid")

	def test_public_application_requires_otp_when_enabled(self):
		import pyotp
		captured = {}
		def send(secret, token, phone_no):
			captured["otp"] = pyotp.HOTP(secret).at(token)
			return True
		with patch("padars.student_application._sms_required", return_value=True), patch("padars.student_application._sms_configured", return_value=True), patch("frappe.twofactor.send_token_via_sms", side_effect=send), patch.object(type(frappe.db.after_commit), "add", lambda self, callback: callback()):
			with self.assertRaises(frappe.AuthenticationError):
				student_application.submit(**self.row, guardian_consent=1)
			student_application.send_code(self.row["national_id"], self.row["phone"])
			result = student_application.submit(**self.row, guardian_consent=1, otp=captured["otp"])
			self.assertTrue(result["status_token"])

	def test_native_csv_parser_uses_registration_provider(self):
		with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", newline="", encoding="utf8") as source:
			writer = csv.DictWriter(source, fieldnames=list(self.row))
			writer.writeheader()
			writer.writerow(self.row)
			source.flush()
			file = ImportFile("Student", source.name, import_type=INSERT, console=True)
			parsed = file.data[0].parse_doc("Student")
			self.assertEqual({key: parsed.get(key) for key in self.row}, self.row)
			self.assertEqual(file.get_all_warnings(), [])
			self.assertEqual(file.data[0].parse_doc("Student")["national_id"], self.row["national_id"])

	def test_native_excel_parser_uses_registration_provider(self):
		from openpyxl import Workbook
		with tempfile.NamedTemporaryFile(suffix=".xlsx") as source:
			workbook = Workbook()
			workbook.active.append(list(self.row))
			workbook.active.append(list(self.row.values()))
			workbook.save(source.name)
			with open(source.name, "rb") as xlsx:
				attachment = frappe.get_doc({"doctype": "File", "file_name": f"test-{self.key}.xlsx",
					"content": xlsx.read(), "is_private": 1}).insert(ignore_permissions=True)
			try:
				file = ImportFile("Student", attachment.file_url, import_type=INSERT)
				self.assertEqual(file.get_all_warnings(), [])
				self.assertEqual(file.data[0].parse_doc("Student")["national_id"], self.row["national_id"])
			finally:
				attachment.delete(ignore_permissions=True)

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

	def test_public_application_page_renders_before_school_setup(self):
		from padars.www.student_application import get_context
		context = frappe._dict()
		with patch("padars.www.student_application.get_primary_school", return_value=None):
			get_context(context)
		self.assertFalse(context.sms_required)
		self.assertTrue(context.no_cache)

	def test_public_application_page_responds_before_school_setup(self):
		from frappe.utils import get_test_client
		site = frappe.local.site
		with patch("frappe.app.get_site_name", return_value=site), patch("padars.www.student_application.get_primary_school", return_value=None):
			with ThreadPoolExecutor(max_workers=1) as executor:
				response = executor.submit(lambda: get_test_client().get("/student-application")).result()
		self.assertEqual(response.status_code, 200)
		self.assertIn(b"Student Application", response.data)

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
