from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from padars.curriculum import (
	add_enrolled_students_to_section,
	create_curriculum_adoption_from_program,
	generate_course_offerings,
)
from padars.tests.utils import get_or_create_test_school


class TestCurriculum(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.savepoint("padars_curriculum_test")
		self.key = frappe.generate_hash(length=8).upper()
		self.year = frappe.get_doc({
			"doctype": "Academic Year", "academic_year_name": f"C-{self.key}",
			"year_start_date": "2099-01-01", "year_end_date": "2099-12-31",
		}).insert()
		self.school = get_or_create_test_school(self.year.name, f"C-{self.key}")
		self.course = frappe.get_doc({"doctype": "Course", "course_name": f"Science-{self.key}"}).insert()
		self.program = self._program("Science")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="padars_curriculum_test")

	def _program(self, stream):
		return frappe.get_doc({
			"doctype": "Program", "program_name": f"Grade 10 {stream} {self.key}",
			"padars_grade_level": "10", "padars_stream": stream,
			"courses": [{"course": self.course.name, "required": 1}],
		}).insert()

	def _adoption(self):
		result = create_curriculum_adoption_from_program(self.program.name, self.year.name)
		adoption = frappe.get_doc("School Curriculum Adoption", result["name"])
		adoption.courses[0].weekly_hours = 4
		adoption.status = "Active"
		adoption.save()
		return adoption

	def _section(self, adoption, code="A", term=None, name_suffix=None):
		return frappe.get_doc({
			"doctype": "Student Group", "student_group_name": f"10-{name_suffix or code}-{self.key}",
			"academic_year": self.year.name, "academic_term": term, "group_based_on": "Batch",
			"program": self.program.name, "padars_school": self.school.name,
			"padars_is_class_section": 1, "padars_section_code": code,
			"padars_curriculum_adoption": adoption.name,
		}).insert()

	def test_grade_stream_pair_is_normalized_and_unique(self):
		self.assertEqual(self.program.padars_stream, "Science")
		duplicate = frappe.get_doc({
			"doctype": "Program", "program_name": f"Duplicate-{self.key}",
			"padars_grade_level": "10", "padars_stream": "  SCIENCE  ",
		})
		with self.assertRaises(frappe.ValidationError):
			duplicate.insert()
		incomplete = frappe.get_doc({
			"doctype": "Program", "program_name": f"Incomplete-{self.key}", "padars_grade_level": "10",
		})
		with self.assertRaises(frappe.ValidationError):
			incomplete.insert()

	def test_adoption_is_a_snapshot_and_active_content_is_immutable(self):
		adoption = self._adoption()
		self.assertEqual(adoption.courses[0].course, self.course.name)
		self.assertEqual(adoption.courses[0].course_name, self.course.course_name)
		program = frappe.get_doc("Program", self.program.name)
		program.courses[0].required = 0
		program.save()
		adoption.reload()
		self.assertEqual(adoption.courses[0].required, 1)
		adoption.courses[0].weekly_hours = 5
		with self.assertRaises(frappe.ValidationError):
			adoption.save()

		next_version = frappe.get_doc("School Curriculum Adoption",
			create_curriculum_adoption_from_program(self.program.name, self.year.name)["name"])
		self.assertEqual(next_version.version, 2)
		next_version.status = "Active"
		with self.assertRaises(frappe.ValidationError):
			next_version.save()
		adoption.reload()
		adoption.status = "Archived"
		adoption.save()
		next_version.reload()
		next_version.status = "Active"
		next_version.save()
		adoption.reload()
		adoption.status = "Active"
		with self.assertRaises(frappe.ValidationError):
			adoption.save()

	def test_term_must_belong_to_the_class_year(self):
		adoption = self._adoption()
		other_year = frappe.get_doc({
			"doctype": "Academic Year", "academic_year_name": f"CY-{self.key}",
			"year_start_date": "2100-01-01", "year_end_date": "2100-12-31",
		}).insert()
		term = frappe.get_doc({
			"doctype": "Academic Term", "term_name": f"Term-{self.key}",
			"academic_year": other_year.name, "term_start_date": "2100-01-01", "term_end_date": "2100-06-30",
		}).insert()
		with self.assertRaises(frappe.ValidationError):
			self._section(adoption, term=term.name)

	def test_section_roster_and_offerings_are_scoped_and_idempotent(self):
		adoption = self._adoption()
		group = self._section(adoption)
		with self.assertRaises(frappe.ValidationError):
			self._section(adoption, name_suffix="duplicate")
		generated = generate_course_offerings(group.name)
		self.assertEqual(generated["created"], 1)
		repeated = generate_course_offerings(group.name)
		self.assertEqual(repeated["created"], 0)
		self.assertEqual(repeated["reused"], 1)
		offering = frappe.get_doc("School Course Offering", generated["offerings"][0])
		self.assertEqual(offering.curriculum_adoption, adoption.name)
		self.assertEqual(offering.curriculum_course_required, 1)
		self.assertEqual(offering.expected_weekly_hours, 4)
		other_course = frappe.get_doc({"doctype": "Course", "course_name": f"Other-{self.key}"}).insert()
		offering.course = other_course.name
		with self.assertRaises(frappe.ValidationError):
			offering.save()

		user = frappe.get_doc({
			"doctype": "User", "email": f"curriculum-{self.key}@example.invalid",
			"first_name": "Curriculum Student", "send_welcome_email": 0,
			"enabled": 1, "user_type": "System User",
		}).insert(ignore_permissions=True)
		user.add_roles("Student")
		with patch("education.education.doctype.student.student.Student.on_update"):
			student = frappe.get_doc({"doctype": "Student", "first_name": "Curriculum",
				"student_email_id": user.name, "user": user.name, "enabled": 1}).insert()
		enrollment = frappe.get_doc({
			"doctype": "Program Enrollment", "student": student.name, "program": self.program.name,
			"academic_year": self.year.name, "enrollment_date": "2099-01-01",
			"padars_school": self.school.name,
		}).insert()
		enrollment.submit()
		added = add_enrolled_students_to_section(group.name)
		self.assertEqual(added["added"], 1)
		self.assertEqual(add_enrolled_students_to_section(group.name)["added"], 0)

		second = self._section(adoption, code="B")
		second.append("students", {"student": student.name, "active": 1})
		with self.assertRaises(frappe.ValidationError):
			second.save()
		adoption.status = "Archived"
		adoption.save()
		self.assertEqual(generate_course_offerings(group.name)["reused"], 1)

	def test_manual_group_accepts_site_student_without_program_enrollment(self):
		group = self._section(self._adoption())
		user = frappe.get_doc({"doctype": "User", "email": f"manual-{self.key}@example.invalid",
			"first_name": "Manual Student", "enabled": 1, "send_welcome_email": 0}).insert(ignore_permissions=True)
		with patch("education.education.doctype.student.student.Student.on_update"):
			student = frappe.get_doc({"doctype": "Student", "first_name": "Manual Student",
				"student_email_id": user.name, "user": user.name, "enabled": 1}).insert()
		self.assertFalse(frappe.db.exists("Program Enrollment", {"student": student.name}))
		group.append("students", {"student": student.name, "active": 1})
		group.save()
		self.assertEqual(group.reload().students[0].student, student.name)
		frappe.db.set_value("Student", student.name, "enabled", 0)
		with self.assertRaises(frappe.ValidationError):
			group.save()

	def test_non_manager_cannot_create_school_adoption(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			create_curriculum_adoption_from_program(self.program.name, self.year.name)
