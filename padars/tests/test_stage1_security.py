import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from padars import education_api
from padars.permissions import is_platform_admin, school_permission_query_conditions


@unittest.skip("Superseded shared-site model; see test_site_security")
class TestStage1Security(FrappeTestCase):
	def setUp(self):
		self.key = frappe.generate_hash(length=8).upper()
		self.school_a = self._school("A")
		self.school_b = self._school("B")
		self.manager_a = self._user("manager-a", ["Padars School Manager", "Academics User"])
		self.manager_b = self._user("manager-b", ["Padars School Manager", "Academics User"])
		self.student_a_user = self._user("student-a", ["Student"])
		self.student_b_user = self._user("student-b", ["Student"])
		self.teacher_user = self._user("teacher", ["Padars Teacher", "Instructor"])
		self.student_a = self._student("A", self.student_a_user)
		self.student_b = self._student("B", self.student_b_user)
		self.instructor = frappe.get_doc({"doctype": "Instructor", "instructor_name": f"Teacher {self.key}"}).insert()
		self._membership(self.school_a, self.manager_a, "School Administrator")
		self._membership(self.school_b, self.manager_b, "School Administrator")
		self._membership(self.school_a, self.student_a_user, "Student")
		self._membership(self.school_b, self.student_b_user, "Student")
		self._membership(self.school_a, self.teacher_user, "Teacher", self.instructor.name)

	def tearDown(self):
		frappe.set_user("Administrator")

	def _school(self, suffix):
		return frappe.get_doc({
			"doctype": "School", "school_code": f"T{suffix}-{self.key}", "school_name": f"Test {suffix} {self.key}"
		}).insert()

	def _user(self, prefix, roles):
		# Synthetic tests may create several users in one minute; bypass only the
		# rate limiter, never document permission checks.
		previous_import_flag = frappe.flags.in_import
		frappe.flags.in_import = True
		try:
			user = frappe.get_doc({
				"doctype": "User", "email": f"{prefix}-{self.key}@example.invalid", "first_name": prefix,
				"send_welcome_email": 0,
			}).insert(ignore_permissions=True)
		finally:
			frappe.flags.in_import = previous_import_flag
		user.add_roles(*roles)
		return user.name

	def _student(self, suffix, user):
		return frappe.get_doc({
			"doctype": "Student", "first_name": f"Student {suffix} {self.key}", "gender": "Female",
			"date_of_birth": "2010-01-01", "student_email_id": user, "user": user,
		}).insert()

	def _membership(self, school, user, school_role, instructor=None):
		return frappe.get_doc({
			"doctype": "School Membership", "school": school.name, "user": user,
			"instructor": instructor, "school_role": school_role,
		}).insert()

	def test_platform_recovery_and_roles_exist(self):
		self.assertTrue(is_platform_admin("Administrator"))
		for role in ("Padars Platform Administrator", "Padars School Manager", "Padars Academic Staff", "Padars Teacher"):
			self.assertTrue(frappe.db.exists("Role", role))

	def test_school_manager_list_condition_excludes_other_school(self):
		condition = school_permission_query_conditions(self.manager_a, "School")
		self.assertIn(self.school_a.name, condition)
		self.assertNotIn(self.school_b.name, condition)
		frappe.set_user(self.manager_a)
		self.assertEqual(frappe.get_list("School", pluck="name"), [self.school_a.name])

	def test_student_cannot_read_another_students_document(self):
		frappe.set_user(self.student_a_user)
		self.assertTrue(frappe.has_permission("Student", "read", self.student_a.name))
		self.assertFalse(frappe.has_permission("Student", "read", self.student_b.name))

	def test_unsafe_education_entry_points_fail_closed(self):
		frappe.set_user(self.student_a_user)
		with self.assertRaises(frappe.PermissionError):
			education_api.get_students("2099", "Batch")
		with self.assertRaises(frappe.PermissionError):
			education_api.preview_report_card("{}")
		with self.assertRaises(frappe.PermissionError):
			education_api.enroll_student("untrusted-applicant")

	def test_required_school_context_custom_fields_are_installed(self):
		for doctype in ("Program Enrollment", "Student Group", "Course Schedule", "Assessment Plan", "Assessment Result", "Student Attendance"):
			field = frappe.get_meta(doctype).get_field("padars_school")
			self.assertIsNotNone(field, doctype)
			self.assertEqual(field.options, "School")

	def test_stage1_constraints_are_present(self):
		self.assertTrue(self._has_index("School Membership", ("school", "user", "school_role")))
		self.assertTrue(self._has_index("School Course Offering", ("school", "academic_year", "course", "student_group")))
		self.assertTrue(self._has_index("LMS Sync Operation", ("school", "state")))

	def _has_index(self, doctype, columns):
		indexes = {}
		for row in frappe.db.sql(f"show index from `tab{doctype}`", as_dict=True):
			indexes.setdefault(row.Key_name, []).append((row.Seq_in_index, row.Column_name))
		return any(tuple(name for _, name in sorted(parts)) == columns for parts in indexes.values())


def run_runtime_smoke():
	"""Run the isolated assertions when an upstream fixture blocks the runner.

	Not whitelisted: this is called explicitly with ``bench execute`` on a
	disposable site and remains a complement—not a replacement—for the suite.
	"""
	test = TestStage1Security("test_platform_recovery_and_roles_exist")
	test.setUp()
	try:
		for test_name in (
			"test_platform_recovery_and_roles_exist",
			"test_school_manager_list_condition_excludes_other_school",
			"test_student_cannot_read_another_students_document",
			"test_unsafe_education_entry_points_fail_closed",
			"test_required_school_context_custom_fields_are_installed",
			"test_stage1_constraints_are_present",
		):
			getattr(test, test_name)()
	finally:
		test.tearDown()
	return {"status": "passed", "checks": 6}
