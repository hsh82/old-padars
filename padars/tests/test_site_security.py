from unittest.mock import patch

import frappe
import frappe.client
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from padars import education_api
from padars import api as padars_api
from padars.file_security import validate_private_attachment
from padars.install import ensure_action_permissions
from padars.permissions import can_manage_moodle, can_manage_school
from padars.permissions_site import has_school_permission
from padars.reports import _require_reviewed_report_access
from padars.setup import configure_school
from padars.tests.utils import get_or_create_test_school


class TestSiteSecurity(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.savepoint("padars_site_test")
		self.key = frappe.generate_hash(length=8).upper()
		self.year = frappe.get_doc({"doctype": "Academic Year", "academic_year_name": f"Y-{self.key}",
			"year_start_date": "2099-01-01", "year_end_date": "2099-12-31"}).insert()
		self.school = get_or_create_test_school(self.year.name, f"S-{self.key}")
		self.program = frappe.get_doc({"doctype": "Program", "program_name": f"Grade-{self.key}"}).insert()
		self.group_a = self._group("A")
		self.group_b = self._group("B")
		self.user = self._user("scoped", ["Padars Read Only"])
		self.other = self._user("other", ["Padars Read Only"])
		self._assignment(self.user, self.group_a.name)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="padars_site_test")
		frappe.clear_cache(doctype="Assessment Result")
		frappe.local.role_permissions.clear()

	def _group(self, suffix):
		return frappe.get_doc({"doctype": "Student Group", "student_group_name": f"{suffix}-{self.key}",
			"academic_year": self.year.name, "group_based_on": "Batch", "program": self.program.name,
			"padars_school": self.school.name}).insert()

	def _user(self, prefix, roles):
		old = frappe.flags.in_import
		frappe.flags.in_import = True
		try:
			user = frappe.get_doc({"doctype": "User", "email": f"{prefix}-{self.key}@example.invalid",
				"first_name": prefix, "send_welcome_email": 0, "enabled": 1, "user_type": "System User"}).insert(ignore_permissions=True)
		finally:
			frappe.flags.in_import = old
		user.add_roles(*roles)
		return user.name

	def _assignment(self, user, group, **values):
		return frappe.get_doc({"doctype": "Academic Assignment", "user": user,
			"scope_type": "Student Group", "scope_name": group, **values}).insert()

	def _student(self, suffix, group):
		user = self._user(f"student-{suffix}", ["Student"])
		with patch("education.education.doctype.student.student.Student.on_update"):
			student = frappe.get_doc({"doctype": "Student", "first_name": suffix,
				"student_email_id": user, "user": user, "enabled": 1}).insert()
		frappe.get_doc({"doctype": "Program Enrollment", "student": student.name, "program": self.program.name,
			"academic_year": self.year.name, "enrollment_date": "2099-01-01",
			"padars_school": self.school.name}).insert().submit()
		group.append("students", {"student": student.name, "active": 1})
		group.save()
		return student.name, user

	def test_group_scope_direct_list_and_write(self):
		self.assertTrue(frappe.has_permission("Student Group", "read", self.group_a.name, user=self.user))
		self.assertFalse(frappe.has_permission("Student Group", "read", self.group_b.name, user=self.user))
		self.assertFalse(frappe.has_permission("Student Group", "write", self.group_a.name, user=self.user))
		self.assertFalse(frappe.has_permission("Student Group", "read", self.group_a.name, user=self.other))
		frappe.set_user(self.user)
		groups = frappe.get_list("Student Group", pluck="name")
		self.assertIn(self.group_a.name, groups)
		self.assertNotIn(self.group_b.name, groups)
		self.assertEqual(education_api.get_school_group_students(self.group_a.name), [])
		with self.assertRaises(frappe.PermissionError):
			education_api.get_school_group_students(self.group_b.name)

	def test_expired_assignment_denies_access(self):
		self._assignment(self.other, self.group_b.name, valid_to=add_days(today(), -1))
		self.assertFalse(frappe.has_permission("Student Group", "read", self.group_b.name, user=self.other))

	def test_program_scope_allows_its_classes_only(self):
		other_program = frappe.get_doc({"doctype": "Program", "program_name": f"Other-{self.key}"}).insert()
		other_group = frappe.get_doc({"doctype": "Student Group", "student_group_name": f"C-{self.key}",
			"academic_year": self.year.name, "group_based_on": "Batch", "program": other_program.name,
			"padars_school": self.school.name}).insert()
		staff = self._user("staff", ["Padars Academic Staff"])
		frappe.get_doc({"doctype": "Academic Assignment", "user": staff, "scope_type": "Program",
			"scope_name": self.program.name, "can_edit": 1}).insert()
		self.assertTrue(frappe.has_permission("Student Group", "write", self.group_a.name, user=staff))
		self.assertTrue(frappe.has_permission("Student Group", "read", self.group_b.name, user=staff))
		self.assertFalse(frappe.has_permission("Student Group", "read", other_group.name, user=staff))
		frappe.set_user(staff)
		self.assertEqual(education_api.get_program_courses("Course", "", "name", 0, 20,
			{"program": self.program.name}), [])
		with self.assertRaises(frappe.PermissionError):
			education_api.get_program_courses("Course", "", "name", 0, 20, {"program": other_program.name})

	def test_duplicate_assignment_rejected(self):
		with self.assertRaises(frappe.UniqueValidationError):
			self._assignment(self.user, self.group_a.name)

	def test_setup_is_admin_only_and_repeatable(self):
		manager = self._user("manager", ["Padars Read Only"])
		args = (self.school.school_name, self.school.school_code, self.year.name, manager)
		self.assertEqual(configure_school(*args), configure_school(*args))
		self.assertIn("Padars School Manager", frappe.get_roles(manager))
		self.assertTrue(can_manage_school(self.school.name, manager))
		self.assertFalse(can_manage_moodle(self.school.name, manager))
		frappe.set_user(self.user)
		with self.assertRaises(frappe.PermissionError):
			configure_school(*args)

	def test_scoped_staff_cannot_run_unreviewed_reports(self):
		frappe.set_user(self.user)
		with self.assertRaises(frappe.PermissionError):
			_require_reviewed_report_access()

	def test_unreviewed_finance_and_enrollment_rpcs_are_closed(self):
		for method in ("education.education.api.collect_fees", "education.education.billing.handle_payment_success",
			"education.education.utils.enroll_in_program", "education.education.doctype.guardian.guardian.invite_guardian"):
			self.assertEqual(frappe.override_whitelisted_method(method), "padars.education_api.deny_unreviewed")

	def test_manager_cannot_change_primary_manager(self):
		manager = self._user("manager", ["Padars School Manager"])
		frappe.set_user(manager)
		school = frappe.get_doc("School", self.school.name)
		school.primary_school_manager = manager
		with self.assertRaises(frappe.PermissionError):
			school.save()

	def test_student_records_are_scoped_without_membership(self):
		students = [self._student("a", self.group_a), self._student("b", self.group_b)]
		self.assertFalse(frappe.db.exists("School Membership", {"user": students[0][1]}))
		self.assertTrue(frappe.has_permission("Student", "read", students[0][0], user=self.user))
		self.assertFalse(frappe.has_permission("Student", "read", students[1][0], user=self.user))
		frappe.set_user(self.user)
		self.assertEqual(frappe.client.get("Student", students[0][0])["name"], students[0][0])
		with self.assertRaises(frappe.PermissionError):
			frappe.client.get("Student", students[1][0])
		self.assertFalse(frappe.client.get_value("Student", "name", students[1][0]))
		frappe.set_user(students[0][1])
		self.assertTrue(frappe.has_permission("Student", "read", students[0][0]))
		self.assertFalse(frappe.has_permission("Student", "read", students[1][0]))
		# A Student Group contains the complete roster, so membership alone must
		# not grant direct document access to it.
		self.assertFalse(frappe.has_permission("Student Group", "read", self.group_a.name))
		with self.assertRaises(frappe.PermissionError):
			frappe.get_list("Student Group", pluck="name")
		self.assertEqual(education_api.get_student_context(students[0][0])["name"], students[0][0])
		with self.assertRaises(frappe.PermissionError):
			education_api.get_student_context(students[1][0])

	def test_guardian_portal_is_closed_until_relationship_verification_exists(self):
		student, _ = self._student("guardian", self.group_a)
		guardian = self._user("guardian", ["Guardian"])
		frappe.set_user(guardian)
		with self.assertRaises(frappe.PermissionError):
			education_api.get_student_context(student)
		with self.assertRaises(frappe.PermissionError):
			education_api.get_portal_context()

	def test_sensitive_attachments_must_be_private(self):
		with self.assertRaises(frappe.PermissionError):
			validate_private_attachment(frappe._dict(attached_to_doctype="Student", is_private=0, file_url="/files/test"))
		with self.assertRaises(frappe.PermissionError):
			validate_private_attachment(frappe._dict(attached_to_doctype="Student", is_private=1, file_url="https://example.invalid/test"))
		validate_private_attachment(frappe._dict(attached_to_doctype="Student", is_private=1, file_url="/private/files/test"))

	def test_academic_records_cannot_be_shared_directly(self):
		import frappe.share

		with self.assertRaises(frappe.PermissionError):
			frappe.share.add_docshare("Student Group", self.group_b.name, user=self.user)

	def test_existing_academic_shares_block_setup_without_deletion(self):
		import frappe.share

		with patch("padars.file_security.validate_share"):
			share = frappe.share.add_docshare("Student Group", self.group_b.name, user=self.user)
		with self.assertRaises(frappe.ValidationError):
			configure_school(self.school.school_name, self.school.school_code, self.year.name, "Administrator")
		self.assertTrue(frappe.db.exists("DocShare", share.name))

	def test_private_file_obeys_parent_scope_even_for_owner(self):
		file_doc = frappe.get_doc({"doctype": "File", "file_name": f"scope-{self.key}.txt", "is_private": 1,
			"content": f"synthetic-{self.key}", "attached_to_doctype": "Student Group",
			"attached_to_name": self.group_b.name}).insert(ignore_permissions=True)
		try:
			frappe.db.set_value("File", file_doc.name, "owner", self.user)
			self.assertFalse(frappe.has_permission("File", "read", file_doc.name, user=self.user))
			frappe.set_user(self.user)
			self.assertNotIn(file_doc.name, frappe.get_list("File", filters={"name": file_doc.name}, pluck="name"))
		finally:
			frappe.set_user("Administrator")
			file_doc.on_rollback()

	def test_marks_entry_is_limited_to_assigned_offering(self):
		student, _ = self._student("marks", self.group_a)
		courses = [frappe.get_doc({"doctype": "Course", "course_name": f"{suffix}-{self.key}"}).insert()
			for suffix in ("One", "Two")]
		offerings = [frappe.get_doc({"doctype": "School Course Offering", "school": self.school.name,
			"academic_year": self.year.name, "program": self.program.name, "course": course.name,
			"student_group": self.group_a.name, "offering_identifier": f"O-{course.name}"}).insert()
			for course in courses]
		user = self._user("marks", ["Padars Grade Entry Staff"])
		frappe.get_doc({"doctype": "Academic Assignment", "user": user, "scope_type": "School Course Offering",
			"scope_name": offerings[0].name, "can_enter_marks": 1}).insert()
		result = frappe.new_doc("Assessment Result")
		result.update({"student": student, "student_group": self.group_a.name, "program": self.program.name,
			"academic_year": self.year.name, "course": courses[0].name, "padars_course_offering": offerings[0].name})
		self.assertTrue(has_school_permission(result, "create", user))
		self.assertTrue(frappe.has_permission("Assessment Result", "create", doc=result, user=user))
		self.assertTrue(frappe.has_permission("Assessment Result", "enter_grade", doc=result, user=user))
		self.assertFalse(frappe.has_permission("Assessment Result", "approve_grade", doc=result, user=user))
		self.assertFalse(has_school_permission(result, "submit", user))
		result.course = courses[1].name
		result.padars_course_offering = offerings[1].name
		self.assertFalse(has_school_permission(result, "create", user))
		result.course = courses[0].name
		result.padars_course_offering = offerings[0].name
		permission = frappe.db.get_value("Custom DocPerm", {"parent": "Assessment Result", "role": "Padars Grade Entry Staff", "permlevel": 0}, "name")
		frappe.db.set_value("Custom DocPerm", permission, "enter_grade", 0)
		frappe.clear_cache(doctype="Assessment Result")
		frappe.local.role_permissions.clear()
		self.assertFalse(frappe.has_permission("Assessment Result", "create", doc=result, user=user))
		ensure_action_permissions()
		self.assertFalse(frappe.db.get_value("Custom DocPerm", permission, "enter_grade"))

	def test_attendance_write_requires_the_assigned_group_and_action(self):
		student, _ = self._student("attendance", self.group_a)
		staff = self._user("attendance", ["Padars Academic Staff"])
		self._assignment(staff, self.group_a.name, can_manage_attendance=1)
		attendance = frappe.new_doc("Student Attendance")
		attendance.update({"student": student, "student_group": self.group_a.name, "date": "2099-01-01", "status": "Present"})
		self.assertTrue(frappe.has_permission("Student Attendance", "create", doc=attendance, user=staff))
		attendance.student_group = self.group_b.name
		self.assertFalse(frappe.has_permission("Student Attendance", "create", doc=attendance, user=staff))

	def test_scoped_staff_cannot_move_an_offering_to_another_class(self):
		course = frappe.get_doc({"doctype": "Course", "course_name": f"Scope-{self.key}"}).insert()
		offering = frappe.get_doc({"doctype": "School Course Offering", "school": self.school.name,
			"academic_year": self.year.name, "program": self.program.name, "course": course.name,
			"student_group": self.group_a.name, "offering_identifier": f"S-{self.key}"}).insert()
		staff = self._user("editor", ["Padars Academic Staff"])
		frappe.get_doc({"doctype": "Academic Assignment", "user": staff, "scope_type": "School Course Offering",
			"scope_name": offering.name, "can_edit": 1}).insert()
		self.assertTrue(frappe.has_permission("School Course Offering", "write", doc=offering, user=staff))
		offering.student_group = self.group_b.name
		self.assertFalse(frappe.has_permission("School Course Offering", "write", doc=offering, user=staff))

	def test_native_onboarding_uses_records(self):
		self.assertTrue(frappe.db.exists("Workspace", "Padars"))
		self.assertTrue(frappe.db.exists("Module Onboarding", "Padars School Onboarding"))
		for name in ("Padars Academic Year", "Padars School", "Padars Program", "Padars Student Group"):
			self.assertTrue(frappe.get_doc("Onboarding Step", name).is_work_done(), name)

	def test_sensitive_notes_require_role_and_scope(self):
		student, _ = self._student("sensitive", self.group_a)
		log = frappe.get_doc({"doctype": "Student Log", "student": student, "type": "Medical"}).insert()
		reader = self._user("sensitive", ["Padars Read Only", "Padars Sensitive Records"])
		self._assignment(reader, self.group_a.name, can_view_sensitive=1)
		self.assertTrue(frappe.has_permission("Student Log", "read", log.name, user=reader))
		self.assertFalse(frappe.has_permission("Student Log", "read", log.name, user=self.user))

	def test_moodle_role_is_separate_and_requests_are_idempotent(self):
		course = frappe.get_doc({"doctype": "Course", "course_name": f"Moodle-{self.key}"}).insert()
		offering = frappe.get_doc({"doctype": "School Course Offering", "school": self.school.name,
			"academic_year": self.year.name, "program": self.program.name, "course": course.name,
			"student_group": self.group_a.name, "offering_identifier": f"M-{self.key}"}).insert()
		manager = self._user("manager", ["Padars School Manager", "Education Manager"])
		moodle_user = self._user("moodle", ["Padars Moodle Manager"])
		frappe.set_user(moodle_user)
		with patch("frappe.enqueue"):
			first = padars_api.request_course_offering_sync(offering.name)
			second = padars_api.request_course_offering_sync(offering.name)
		self.assertEqual(first["name"], second["name"])
		self.assertTrue(frappe.has_permission("LMS Sync Operation", "read", first["name"], user=moodle_user))
		self.assertFalse(frappe.has_permission("LMS Sync Operation", "read", first["name"], user=manager))
		frappe.set_user(manager)
		with self.assertRaises(frappe.PermissionError):
			padars_api.request_course_offering_sync(offering.name)

	def test_second_active_school_is_denied(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({"doctype": "School", "school_code": f"OTHER-{self.key}", "school_name": "Other",
				"current_academic_year": self.year.name, "primary_school_manager": "Administrator"}).insert()


def run_runtime_checks():
	"""Run isolated checks on an allow_tests site when upstream preloading fails."""
	if not frappe.conf.allow_tests:
		frappe.throw("Runtime checks require an isolated allow_tests site.")
	tests = ("test_group_scope_direct_list_and_write", "test_expired_assignment_denies_access", "test_program_scope_allows_its_classes_only",
		"test_duplicate_assignment_rejected", "test_setup_is_admin_only_and_repeatable",
		"test_scoped_staff_cannot_run_unreviewed_reports", "test_manager_cannot_change_primary_manager",
		"test_unreviewed_finance_and_enrollment_rpcs_are_closed", "test_attendance_write_requires_the_assigned_group_and_action",
		"test_student_records_are_scoped_without_membership", "test_sensitive_attachments_must_be_private", "test_academic_records_cannot_be_shared_directly", "test_existing_academic_shares_block_setup_without_deletion",
		"test_guardian_portal_is_closed_until_relationship_verification_exists",
		"test_private_file_obeys_parent_scope_even_for_owner",
		"test_marks_entry_is_limited_to_assigned_offering", "test_native_onboarding_uses_records",
		"test_scoped_staff_cannot_move_an_offering_to_another_class",
		"test_sensitive_notes_require_role_and_scope", "test_moodle_role_is_separate_and_requests_are_idempotent",
		"test_second_active_school_is_denied")
	for name in tests:
		case = TestSiteSecurity(name)
		try:
			case.setUp()
			getattr(case, name)()
		finally:
			case.tearDown()
	return {"passed": len(tests), "scope": "single-school permission and setup checks"}
