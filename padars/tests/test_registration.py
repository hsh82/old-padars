from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
import csv
import tempfile

import frappe
from cryptography.fernet import Fernet
from frappe.core.doctype.data_import.importer import ImportFile, INSERT
from frappe.tests.utils import FrappeTestCase

from padars.registration import _identity_key, _phone, enroll_returning_student, register_student
from padars.student_import import ProvisionalStudentImportProvider, create_student_intake, validate_import
from padars.student_activation import activate, send_activation_code, verify_first_login
from padars.student_activation import resolve_student_login
from padars import student_application
from padars.file_security import validate_private_attachment
from padars.student_identity import reserve_provisional, reconcile_existing_student, reset_provisional_credentials
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
			"phone": "09" + str(int(self.key, 16) % 1000000000).zfill(9), "email": f"learner-{self.key}@example.invalid"}
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

	def test_two_column_import_requires_no_student_or_user(self):
		provider = ProvisionalStudentImportProvider()
		provider.doctype = "Student Identity"
		importer = frappe._dict(import_type="Insert New Records")
		row = frappe._dict(national_id=self.row["national_id"], phone=self.row["phone"])
		identity, action = provider.import_row(importer, row)
		self.assertEqual(action, "Insert")
		self.assertFalse(identity.user)
		self.assertFalse(identity.student)
		self.assertEqual(provider.import_row(importer, row)[0].name, identity.name)
		self.assertTrue(verify_first_login(row.national_id, row.phone)["needs_details"])
		with self.assertRaises(frappe.AuthenticationError):
			verify_first_login(row.national_id, "09120000000")

	def test_distinct_students_can_share_a_phone(self):
		first, _ = reserve_provisional(self.row["national_id"], self.row["phone"])
		prefix = "123456789"
		remainder = sum(int(prefix[i]) * (10 - i) for i in range(9)) % 11
		other_id = prefix + str(remainder if remainder < 2 else 11 - remainder)
		second, _ = reserve_provisional(other_id, self.row["phone"])
		self.assertNotEqual(first.name, second.name)
		with self.assertRaises(frappe.ValidationError):
			reserve_provisional(self.row["national_id"], "09121234568")

	def test_shared_phone_supports_two_completed_student_accounts(self):
		prefix = "123456789"
		remainder = sum(int(prefix[i]) * (10 - i) for i in range(9)) % 11
		other_id = prefix + str(remainder if remainder < 2 else 11 - remainder)
		reserve_provisional(self.row["national_id"], self.row["phone"])
		reserve_provisional(other_id, self.row["phone"])
		frappe.set_user("Guest")
		for index, national_id in enumerate((self.row["national_id"], other_id)):
			email = f"shared{index}{self.key.lower()}@gmail.com"
			self.assertTrue(activate(national_id, self.row["phone"], "Raven!Cloud87Train", email=email,
				first_name="Learner", confirm_password="Raven!Cloud87Train")["activated"])
			user = frappe.db.get_value("User", email, ["phone", "mobile_no"], as_dict=True)
			self.assertEqual(user.phone, _phone(self.row["phone"]))
			self.assertFalse(user.mobile_no)

	def test_shared_phone_supports_two_staff_registrations(self):
		prefix = "123456789"
		remainder = sum(int(prefix[i]) * (10 - i) for i in range(9)) % 11
		other_id = prefix + str(remainder if remainder < 2 else 11 - remainder)
		first = register_student(**self.row)
		second = register_student(**{**self.row, "national_id": other_id, "email": f"other-{self.key}@example.invalid"})
		self.assertNotEqual(first["student"], second["student"])

	def test_provisional_recovery_replaces_phone_credential(self):
		reserve_provisional(self.row["national_id"], self.row["phone"])
		self.assertTrue(reset_provisional_credentials(self.row["national_id"], "09121234568")["reset"])
		with self.assertRaises(frappe.AuthenticationError):
			verify_first_login(self.row["national_id"], self.row["phone"])
		self.assertTrue(verify_first_login(self.row["national_id"], "09121234568")["needs_details"])

	def test_provisional_sms_enabled_requires_code(self):
		import pyotp
		reserve_provisional(self.row["national_id"], self.row["phone"])
		captured = {}
		def send(secret, token, phone_no):
			captured["otp"] = pyotp.HOTP(secret).at(token)
			return True
		with patch("padars.student_activation._sms_required", return_value=True), patch("padars.student_activation._sms_configured", return_value=True), patch("frappe.twofactor.send_token_via_sms", side_effect=send), patch.object(type(frappe.db.after_commit), "add", lambda self, callback: callback()):
			with self.assertRaises(frappe.AuthenticationError):
				activate(self.row["national_id"], self.row["phone"], "Raven!Cloud87Train", email=f"sms{self.key.lower()}@gmail.com", first_name="Learner", confirm_password="Raven!Cloud87Train")
			send_activation_code(self.row["national_id"], self.row["phone"])
			self.assertTrue(activate(self.row["national_id"], self.row["phone"], "Raven!Cloud87Train", email=f"sms{self.key.lower()}@gmail.com", first_name="Learner", confirm_password="Raven!Cloud87Train", otp=captured["otp"])["activated"])

	def test_education_student_import_keeps_native_provider(self):
		from frappe.core.doctype.data_import.import_provider import get_import_provider
		self.assertIsNone(get_import_provider("Student"))

	def test_provisional_onboarding_creates_normal_education_user(self):
		from frappe.utils.password import check_password
		identity, _ = reserve_provisional(self.row["national_id"], self.row["phone"])
		self.student_hook.stop()
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.ValidationError):
				activate(self.row["national_id"], self.row["phone"], "Raven!Cloud87Train", email="bad@example.com", first_name="Learner", confirm_password="Raven!Cloud87Train")
			with self.assertRaises(frappe.ValidationError):
				activate(self.row["national_id"], self.row["phone"], "Raven!Cloud87Train", email=f"learner{self.key.lower()}@gmail.com", first_name="Learner", confirm_password="different")
			email = f"learner{self.key.lower()}@gmail.com"
			self.assertTrue(activate(self.row["national_id"], self.row["phone"], "Raven!Cloud87Train", email=email, first_name="Learner", confirm_password="Raven!Cloud87Train")["activated"])
			self.assertEqual(frappe.session.user, "Guest")
			self.assertEqual(check_password(email, "Raven!Cloud87Train"), email)
			with self.assertRaises(frappe.AuthenticationError):
				check_password(email, self.row["phone"])
			with self.assertRaises(frappe.AuthenticationError):
				verify_first_login(self.row["national_id"], self.row["phone"])
			self.assertTrue(frappe.db.get_value("Student Identity", identity.name, "student"))
			self.assertTrue(frappe.db.get_value("Student", {"user": email}, "customer"))
		finally:
			self.student_hook.start()

	def test_provisional_duplicate_email_does_not_consume_credentials(self):
		identity, _ = reserve_provisional(self.row["national_id"], self.row["phone"])
		email = f"used{self.key.lower()}@gmail.com"
		frappe.get_doc({"doctype": "User", "email": email, "first_name": "Existing",
			"user_type": "Website User", "send_welcome_email": 0}).insert()
		frappe.set_user("Guest")
		with self.assertRaises(frappe.ValidationError):
			activate(self.row["national_id"], self.row["phone"], "Raven!Cloud87Train", email=email,
				first_name="Learner", confirm_password="Raven!Cloud87Train")
		self.assertTrue(frappe.db.get_value("Student Identity", identity.name, "pending_activation"))
		self.assertTrue(verify_first_login(self.row["national_id"], self.row["phone"])["needs_details"])

	def test_failed_student_creation_rolls_back_provisional_claim(self):
		identity, _ = reserve_provisional(self.row["national_id"], self.row["phone"])
		email = f"rollback{self.key.lower()}@gmail.com"
		frappe.db.savepoint("padars_failed_claim")
		self.student_hook.stop()
		frappe.set_user("Guest")
		try:
			with patch("padars.student_extension.StudentOnboardingExtension.set_missing_customer_details", side_effect=frappe.ValidationError("failed")):
				with self.assertRaises(frappe.ValidationError):
					activate(self.row["national_id"], self.row["phone"], "Raven!Cloud87Train", email=email,
						first_name="Learner", confirm_password="Raven!Cloud87Train")
			frappe.db.rollback(save_point="padars_failed_claim")
			self.assertFalse(frappe.db.exists("User", email))
			self.assertTrue(frappe.db.get_value("Student Identity", identity.name, "pending_activation"))
			self.assertTrue(verify_first_login(self.row["national_id"], self.row["phone"])["needs_details"])
		finally:
			self.student_hook.start()

	def test_two_column_csv_and_excel_use_native_parser(self):
		from openpyxl import Workbook
		row = {"national_id": self.row["national_id"], "phone": self.row["phone"]}
		with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", newline="", encoding="utf8") as source:
			writer = csv.DictWriter(source, fieldnames=list(row))
			writer.writeheader()
			writer.writerow(row)
			source.flush()
			file = ImportFile("Student Identity", source.name, import_type=INSERT, console=True)
			self.assertEqual(file.get_all_warnings(), [])
			self.assertEqual(file.data[0].parse_doc("Student Identity")["phone"], row["phone"])
		with tempfile.NamedTemporaryFile(suffix=".xlsx") as source:
			workbook = Workbook()
			workbook.active.append(list(row))
			workbook.active.append(list(row.values()))
			workbook.save(source.name)
			with open(source.name, "rb") as xlsx:
				attachment = frappe.get_doc({"doctype": "File", "file_name": f"intake-{self.key}.xlsx",
					"content": xlsx.read(), "is_private": 1}).insert(ignore_permissions=True)
			try:
				file = ImportFile("Student Identity", attachment.file_url, import_type=INSERT)
				self.assertEqual(file.get_all_warnings(), [])
				self.assertEqual(file.data[0].parse_doc("Student Identity")["national_id"], row["national_id"])
			finally:
				attachment.delete(ignore_permissions=True)

	def test_school_manager_import_access_is_scoped(self):
		frappe.flags.in_import = True
		try:
			manager = frappe.get_doc({"doctype": "User", "email": f"import-{self.key}@example.invalid",
				"first_name": "Manager", "user_type": "System User", "send_welcome_email": 0}).insert()
		finally:
			frappe.flags.in_import = False
		manager.add_roles("Padars School Manager")
		self.assertTrue(frappe.has_permission("Student Identity", "import", user=manager.name))
		good = frappe.new_doc("Data Import")
		good.reference_doctype = "Student Identity"
		good.owner = manager.name
		bad = frappe.new_doc("Data Import")
		bad.reference_doctype = "User"
		bad.owner = manager.name
		self.assertTrue(frappe.has_permission("Data Import", "create", good, user=manager.name))
		self.assertFalse(frappe.has_permission("Data Import", "create", bad, user=manager.name))
		self.assertFalse(frappe.has_permission("Student Identity", "write", user=manager.name))
		other = frappe.get_doc({"doctype": "Data Import", "reference_doctype": "Student",
			"import_type": "Insert New Records"}).insert()
		self.assertFalse(frappe.has_permission("Data Import", "read", other.name, user=manager.name))
		frappe.set_user(manager.name)
		self.assertNotIn(other.name, frappe.get_list("Data Import", pluck="name"))

	def test_manager_runs_native_two_column_import(self):
		frappe.flags.in_import = True
		try:
			manager = frappe.get_doc({"doctype": "User", "email": f"batch-{self.key}@example.invalid",
				"first_name": "Manager", "user_type": "System User", "send_welcome_email": 0}).insert()
		finally:
			frappe.flags.in_import = False
		manager.add_roles("Padars School Manager")
		frappe.set_user(manager.name)
		data_import = frappe.get_doc("Data Import", create_student_intake()["name"])
		frappe.set_user("Administrator")
		content = f"national_id,phone\n{self.row['national_id']},{self.row['phone']}\n"
		attachment = frappe.get_doc({"doctype": "File", "file_name": f"batch-{self.key}.csv", "content": content,
			"is_private": 1, "attached_to_doctype": "Data Import", "attached_to_name": data_import.name}).insert(ignore_permissions=True)
		try:
			frappe.set_user(manager.name)
			data_import.import_file = attachment.file_url
			data_import.save()
			with patch.object(frappe.db, "commit"):
				data_import.start_import()
			self.assertEqual(frappe.db.get_value("Data Import", data_import.name, "status"), "Success")
			self.assertTrue(frappe.db.exists("Student Identity", {"identity_key": _identity_key(self.row["national_id"])}))
		finally:
			frappe.set_user("Administrator")
			attachment.delete(ignore_permissions=True)

	def test_import_file_owner_loses_access_with_manager_role(self):
		frappe.flags.in_import = True
		try:
			manager = frappe.get_doc({"doctype": "User", "email": f"file-{self.key}@example.invalid",
				"first_name": "Manager", "user_type": "System User", "send_welcome_email": 0}).insert()
		finally:
			frappe.flags.in_import = False
		manager.add_roles("Padars School Manager")
		frappe.set_user(manager.name)
		data_import = create_student_intake()["name"]
		attachment = frappe.get_doc({"doctype": "File", "file_name": f"private-{self.key}.csv",
			"content": "synthetic", "is_private": 1, "attached_to_doctype": "Data Import",
			"attached_to_name": data_import}).insert()
		try:
			self.assertTrue(frappe.has_permission("File", "read", attachment.name, user=manager.name))
			frappe.set_user("Administrator")
			manager.remove_roles("Padars School Manager")
			self.assertFalse(frappe.has_permission("File", "read", attachment.name, user=manager.name))
			frappe.set_user(manager.name)
			self.assertNotIn(attachment.name, frappe.get_list("File", pluck="name"))
		finally:
			frappe.set_user("Administrator")
			attachment.delete(ignore_permissions=True)

	def test_native_uploader_parent_checks_and_manager_isolation(self):
		from frappe.handler import check_write_permission
		managers = []
		frappe.flags.in_import = True
		try:
			for suffix in ("a", "b"):
				user = frappe.get_doc({"doctype": "User", "email": f"upload-{suffix}-{self.key}@example.invalid",
					"first_name": "Manager", "user_type": "System User", "send_welcome_email": 0}).insert()
				user.add_roles("Padars School Manager")
				managers.append(user.name)
		finally:
			frappe.flags.in_import = False
		frappe.set_user(managers[0])
		with self.assertRaisesRegex(frappe.PermissionError, "Not permitted"):
			check_write_permission("Data Import", "new-data-import-regression")
		name = create_student_intake()["name"]
		self.assertEqual(frappe.db.get_value("Data Import", name, "reference_doctype"), "Student Identity")
		self.assertEqual(frappe.db.get_value("Data Import", name, "owner"), managers[0])
		check_write_permission("Data Import", name)
		attachment = frappe.get_doc({"doctype": "File", "file_name": f"isolation-{self.key}.csv",
			"content": "synthetic", "is_private": 1, "attached_to_doctype": "Data Import",
			"attached_to_name": name}).insert()
		try:
			self.assertTrue(frappe.has_permission("File", "read", attachment.name, user=managers[0]))
			self.assertFalse(frappe.has_permission("Data Import", "read", name, user=managers[1]))
			self.assertFalse(frappe.has_permission("File", "read", attachment.name, user=managers[1]))
			frappe.set_user(managers[1])
			with self.assertRaisesRegex(frappe.PermissionError, "Not permitted"):
				check_write_permission("Data Import", name)
			self.assertNotIn(attachment.name, frappe.get_list("File", pluck="name"))
			frappe.set_user("Administrator")
			forged = frappe.get_doc("Data Import", name)
			forged.owner = managers[1]
			self.assertFalse(frappe.has_permission("Data Import", "write", forged, user=managers[1]))
			unrelated = frappe.get_doc({"doctype": "Data Import", "reference_doctype": "Student",
				"import_type": "Insert New Records"}).insert()
			frappe.set_user(managers[0])
			with self.assertRaisesRegex(frappe.PermissionError, "Not permitted"):
				check_write_permission("Data Import", unrelated.name)
		finally:
			frappe.set_user("Administrator")
			attachment.delete(ignore_permissions=True)

	def test_reconcile_native_student_without_blocking_creation(self):
		frappe.flags.in_import = True
		try:
			user = frappe.get_doc({"doctype": "User", "email": f"native-{self.key}@example.invalid",
				"first_name": "Native", "user_type": "Website User", "send_welcome_email": 0}).insert()
		finally:
			frappe.flags.in_import = False
		student = frappe.get_doc({"doctype": "Student", "first_name": "Native", "student_email_id": user.name,
			"user": user.name}).insert()
		self.assertTrue(reconcile_existing_student(student.name, self.row["national_id"])["created"])
		self.assertFalse(reconcile_existing_student(student.name, self.row["national_id"])["created"])

	def test_native_student_api_and_matching_user_association(self):
		import frappe.client
		frappe.flags.in_import = True
		try:
			user = frappe.get_doc({"doctype": "User", "email": f"api-{self.key}@example.invalid",
				"first_name": "Native", "user_type": "Website User", "send_welcome_email": 0}).insert()
		finally:
			frappe.flags.in_import = False
		identity = frappe.get_doc({"doctype": "Student Identity", "identity_key": _identity_key(self.row["national_id"]),
			"user": user.name}).insert(ignore_permissions=True)
		student = frappe.client.insert({"doctype": "Student", "first_name": "Native",
			"student_email_id": user.name, "user": user.name})
		self.assertEqual(frappe.db.get_value("Student Identity", identity.name, "student"), student["name"])
		doc = frappe.get_doc("Student", student["name"])
		doc.last_name = "Edited"
		doc.save()
		self.assertEqual(frappe.db.get_value("Student", doc.name, "last_name"), "Edited")

	def test_student_import_rejects_external_or_public_file(self):
		with self.assertRaises(frappe.ValidationError):
			validate_import(frappe._dict(reference_doctype="Student", google_sheets_url="https://example.invalid", import_file=None))
		with self.assertRaises(frappe.ValidationError):
			validate_import(frappe._dict(reference_doctype="Student", google_sheets_url=None, import_file="/files/students.csv"))
		with patch("frappe.db.get_value", return_value="Student"):
			with self.assertRaises(frappe.PermissionError):
				validate_private_attachment(frappe._dict(attached_to_doctype="Data Import", attached_to_name="test", is_private=0, file_url="/files/students.csv"))
		with patch("frappe.db.get_value", return_value=None):
			# Unknown targets retain Frappe's native behavior; the uploader
			# cannot attach to an unsaved intake without parent permission.
			validate_private_attachment(frappe._dict(attached_to_doctype="Data Import", attached_to_name="new-data-import", is_private=0, file_url="/files/students.csv"))

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

	def test_http_activation_error_does_not_echo_credentials(self):
		from frappe.utils import get_test_client
		site = frappe.local.site
		body = {"national_id": "1111111111", "temporary_password": "09129999999"}
		with patch("frappe.app.get_site_name", return_value=site):
			with ThreadPoolExecutor(max_workers=1) as executor:
				response = executor.submit(lambda: get_test_client().post(
					"/api/method/padars.student_activation.verify_first_login", json=body)).result()
		self.assertGreaterEqual(response.status_code, 400)
		self.assertNotIn(body["national_id"].encode(), response.data)
		self.assertNotIn(body["temporary_password"].encode(), response.data)
		self.assertNotIn(b"Traceback", response.data)

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
