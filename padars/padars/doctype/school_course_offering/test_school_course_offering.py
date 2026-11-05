import frappe
from frappe.tests.utils import FrappeTestCase


class TestSchoolCourseOffering(FrappeTestCase):
	def setUp(self):
		self.key = frappe.generate_hash(length=6).upper()
		self.year = frappe.get_doc(
			{
				"doctype": "Academic Year",
				"academic_year_name": f"2099-{self.key}",
				"year_start_date": "2099-01-01",
				"year_end_date": "2100-01-01",
			}
		).insert()
		from padars.tests.utils import get_or_create_test_school
		self.school = get_or_create_test_school(self.year.name, f"OFFERING-{self.key}")
		self.program = frappe.get_doc(
			{"doctype": "Program", "program_name": f"Grade 12 {self.key}"}
		).insert()
		self.course = frappe.get_doc(
			{"doctype": "Course", "course_name": f"Biology {self.key}"}
		).insert()
		self.group = frappe.get_doc(
			{
				"doctype": "Student Group",
				"student_group_name": f"12-1 {self.key}",
				"academic_year": self.year.name,
				"group_based_on": "Course",
				"program": self.program.name,
				"course": self.course.name,
				"padars_school": self.school.name,
			}
		).insert()

	def test_duplicate_offering_is_rejected(self):
		values = {
			"doctype": "School Course Offering",
			"school": self.school.name,
			"academic_year": self.year.name,
			"program": self.program.name,
			"course": self.course.name,
			"student_group": self.group.name,
			"offering_identifier": f"BIO-12-1-{self.key}",
		}
		frappe.get_doc(values).insert()
		self.assertRaises(frappe.ValidationError, frappe.get_doc(values).insert)

	def test_cross_year_group_is_rejected(self):
		other_year = frappe.get_doc(
			{
				"doctype": "Academic Year",
				"academic_year_name": f"2100-{self.key}",
				"year_start_date": "2100-01-01",
				"year_end_date": "2101-01-01",
			}
		).insert()
		self.assertRaises(
			frappe.ValidationError,
			frappe.get_doc(
				{
					"doctype": "School Course Offering",
					"school": self.school.name,
					"academic_year": other_year.name,
					"program": self.program.name,
					"course": self.course.name,
					"student_group": self.group.name,
					"offering_identifier": "BIO-12-1-OTHER-YEAR",
				}
			).insert,
		)

