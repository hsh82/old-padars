import frappe
from frappe.tests.utils import FrappeTestCase

from padars.setup import configure_school
from padars.tests.utils import get_or_create_test_school


class TestSchool(FrappeTestCase):
	def setUp(self):
		key = frappe.generate_hash(length=6).upper()
		self.year = frappe.get_doc({"doctype": "Academic Year", "academic_year_name": f"Y-{key}",
			"year_start_date": "2099-01-01", "year_end_date": "2099-12-31"}).insert()
		self.school = get_or_create_test_school(self.year.name, f"S-{key}")

	def test_only_one_active_school(self):
		other = frappe.get_doc({"doctype": "School", "school_code": frappe.generate_hash(length=8),
			"school_name": "Another School", "current_academic_year": self.year.name,
			"primary_school_manager": "Administrator"})
		self.assertRaises(frappe.ValidationError, other.insert)

	def test_setup_is_repeatable(self):
		args = (self.school.school_name, self.school.school_code, self.year.name, "Administrator")
		self.assertEqual(configure_school(*args), configure_school(*args))
		self.assertEqual(frappe.db.count("School", {"status": "Active"}), 1)

