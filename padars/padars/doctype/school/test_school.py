from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from padars.permissions import has_school_permission, school_permission_query_conditions


class TestSchool(FrappeTestCase):
	def test_school_code_is_unique(self):
		code = f"TEST-{frappe.generate_hash(length=6).upper()}"
		school = frappe.get_doc(
			{
				"doctype": "School",
				"school_code": code,
				"school_name": "Test School",
			}
		).insert()
		self.assertTrue(frappe.db.exists("School", school.name))
		self.assertRaises(
			frappe.UniqueValidationError,
			frappe.get_doc(
				{
					"doctype": "School",
					"school_code": code,
					"school_name": "Another Test School",
				}
			).insert,
		)

	def test_school_permission_is_scoped_to_membership(self):
		doc = frappe._dict({"doctype": "School Course Offering", "school": "SCHOOL-A"})
		with patch("padars.permissions.is_school_admin", return_value=False), patch(
			"padars.permissions.get_user_schools", return_value=["SCHOOL-A"]
		):
			self.assertTrue(has_school_permission(doc, "read", user="student@example.com"))
			self.assertFalse(
				has_school_permission(
					frappe._dict({"doctype": "School Course Offering", "school": "SCHOOL-B"}),
					"read",
					user="student@example.com",
				)
			)

		with patch("padars.permissions.is_school_admin", return_value=False), patch(
			"padars.permissions.get_user_schools", return_value=["SCHOOL-A"]
		):
			condition = school_permission_query_conditions("student@example.com", "School Course Offering")
		self.assertIn("SCHOOL-A", condition)
		self.assertNotIn("SCHOOL-B", condition)

