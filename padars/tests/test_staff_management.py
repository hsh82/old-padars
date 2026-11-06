from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from padars.curriculum import create_curriculum_adoption_from_program, generate_course_offerings
from padars.permissions_site import has_school_permission
from padars.staff import (
	assign_teacher_to_offering,
	get_teacher_workload_data,
	link_instructor_to_user,
)
from padars.tests.utils import get_or_create_test_school


class TestStaffManagement(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		frappe.db.savepoint("padars_staff_test")
		self.key = frappe.generate_hash(length=8).upper()
		self.student_number = 0
		self.year = frappe.get_doc({
			"doctype": "Academic Year", "academic_year_name": f"S-{self.key}",
			"year_start_date": "2099-01-01", "year_end_date": "2099-12-31",
		}).insert()
		self.school = get_or_create_test_school(self.year.name, f"S-{self.key}")
		self.course = self._course("Science")
		self.program = self._program("Science", "10", self.course)
		self.other_course = self._course("Math")
		self.other_program = self._program("Math", "11", self.other_course)
		self.group = self._group(self.program, "A")
		self.other_group = self._group(self.other_program, "B")

	def _course(self, label):
		return frappe.get_doc({"doctype": "Course", "course_name": f"{label}-{self.key}"}).insert()

	def _program(self, label, grade, course):
		return frappe.get_doc({
			"doctype": "Program", "program_name": f"Program-{label}-{self.key}",
			"padars_grade_level": grade, "padars_stream": label,
			"courses": [{"course": course.name, "required": 1}],
		}).insert()

	def _group(self, program, suffix):
		return frappe.get_doc({
			"doctype": "Student Group", "student_group_name": f"{suffix}-{self.key}",
			"academic_year": self.year.name, "group_based_on": "Batch", "program": program.name,
			"padars_school": self.school.name,
		}).insert()

	def _user(self, prefix, roles=()):
		old = frappe.flags.in_import
		frappe.flags.in_import = True
		try:
			user = frappe.get_doc({
				"doctype": "User", "email": f"{prefix}-{self.key}@example.invalid",
				"first_name": prefix, "send_welcome_email": 0, "enabled": 1,
				"user_type": "System User", "roles": [{"role": "Padars Read Only"}],
			}).insert(ignore_permissions=True)
		finally:
			frappe.flags.in_import = old
		if roles:
			user.add_roles(*roles)
		return user.name

	def _instructor(self, suffix):
		return frappe.get_doc({"doctype": "Instructor", "instructor_name": f"Teacher-{suffix}-{self.key}"}).insert()

	def _offering(self, group, course):
		return frappe.get_doc({
			"doctype": "School Course Offering", "school": self.school.name,
			"academic_year": self.year.name, "program": group.program, "course": course.name,
			"student_group": group.name, "offering_identifier": f"{group.name}-{course.name}",
		}).insert()

	def _student(self, group):
		self.student_number += 1
		user = self._user(f"student-{self.student_number}", ["Student"])
		with patch("education.education.doctype.student.student.Student.on_update"):
			student = frappe.get_doc({"doctype": "Student", "first_name": "Scoped Student",
				"student_email_id": user, "user": user, "enabled": 1}).insert()
		enrollment = frappe.get_doc({
			"doctype": "Program Enrollment", "student": student.name, "program": group.program,
			"academic_year": self.year.name, "enrollment_date": "2099-01-01",
			"padars_school": self.school.name,
		}).insert()
		enrollment.submit()
		group.append("students", {"student": student.name, "active": 1})
		group.save()
		return student.name

	def tearDown(self):
		frappe.set_user("Administrator")
		try:
			frappe.db.rollback(save_point="padars_staff_test")
		finally:
			super().tearDown()

	def _class_section(self):
		result = create_curriculum_adoption_from_program(self.program.name, self.year.name)
		adoption = frappe.get_doc("School Curriculum Adoption", result["name"])
		adoption.courses[0].weekly_hours = 5
		adoption.status = "Active"
		adoption.save()
		return frappe.get_doc({
			"doctype": "Student Group", "student_group_name": f"Section-{self.key}",
			"academic_year": self.year.name, "group_based_on": "Batch", "program": self.program.name,
			"padars_school": self.school.name, "padars_is_class_section": 1,
			"padars_section_code": f"A-{self.key}", "padars_curriculum_adoption": adoption.name,
		}).insert()

	def test_teacher_mapping_assignment_and_scope_are_enforced(self):
		user = self._user("teacher")
		instructor = self._instructor("one")
		link_instructor_to_user(instructor.name, user)
		self.assertIn("Padars Teacher", frappe.get_roles(user))
		self.assertEqual(frappe.db.get_value("Instructor", instructor.name, "padars_user"), user)
		self.assertTrue(frappe.db.exists("School Membership", {
			"school": self.school.name, "user": user, "instructor": instructor.name,
			"school_role": "Teacher", "status": "Active",
		}))
		first = self._offering(self.group, self.course)
		second = self._offering(self.other_group, self.other_course)
		assign_teacher_to_offering(first.name, instructor.name, can_enter_marks=1, can_manage_attendance=0)
		self.assertTrue(frappe.has_permission("School Course Offering", "read", first.name, user=user))
		self.assertFalse(frappe.has_permission("School Course Offering", "read", second.name, user=user))
		self.assertTrue(frappe.has_permission("Student Group", "read", self.group.name, user=user))
		self.assertFalse(frappe.has_permission("Student Group", "read", self.other_group.name, user=user))
		frappe.set_user(user)
		self.assertEqual(frappe.get_list("School Course Offering", pluck="name"), [first.name])
		frappe.set_user("Administrator")

		first_doc = frappe.get_doc("School Course Offering", first.name)
		first_doc.instructor = None
		with self.assertRaises(frappe.PermissionError):
			first_doc.save()
		assign_teacher_to_offering(first.name, None)
		self.assertFalse(frappe.has_permission("School Course Offering", "read", first.name, user=user))

	def test_grade_coordinator_and_class_supervisor_are_scope_bound(self):
		coordinator = self._user("coordinator")
		assignment = frappe.get_doc({
			"doctype": "Academic Assignment", "user": coordinator, "assignment_type": "Grade Coordinator",
			"scope_type": "Program", "scope_name": self.program.name, "can_edit": 1,
			"can_enter_marks": 1,
		}).insert()
		self.assertEqual(assignment.assignment_type, "Grade Coordinator")
		self.assertIn("Padars Grade Coordinator", frappe.get_roles(coordinator))
		self.assertTrue(frappe.has_permission("Student Group", "read", self.group.name, user=coordinator))
		self.assertFalse(frappe.has_permission("Student Group", "read", self.other_group.name, user=coordinator))
		student = self._student(self.group)
		offering = self._offering(self.group, self.course)
		result = frappe.new_doc("Assessment Result")
		result.update({"student": student, "student_group": self.group.name, "program": self.program.name,
			"academic_year": self.year.name, "course": self.course.name,
			"padars_course_offering": offering.name})
		self.assertTrue(frappe.has_permission("Assessment Result", "enter_grade", doc=result, user=coordinator))
		self.assertTrue(frappe.has_permission("Assessment Result", "create", doc=result, user=coordinator))
		result.student_group = self.other_group.name
		self.assertFalse(frappe.has_permission("Assessment Result", "enter_grade", doc=result, user=coordinator))
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({"doctype": "Academic Assignment", "user": coordinator,
				"assignment_type": "Grade Coordinator", "scope_type": "Student Group",
				"scope_name": self.group.name}).insert()

		section = self._class_section()
		student = self._student(section)
		supervisor = self._user("supervisor")
		frappe.get_doc({
			"doctype": "Academic Assignment", "user": supervisor, "assignment_type": "Class Supervisor",
			"scope_type": "Student Group", "scope_name": section.name,
			"can_manage_attendance": 1,
		}).insert()
		self.assertIn("Padars Class Supervisor", frappe.get_roles(supervisor))
		attendance = frappe.new_doc("Student Attendance")
		attendance.update({"student": student, "student_group": section.name,
			"date": "2099-01-01", "status": "Present"})
		self.assertTrue(has_school_permission(attendance, "manage_attendance", supervisor))
		self.assertTrue(frappe.has_permission("Student Attendance", "manage_attendance", doc=attendance, user=supervisor))
		self.assertTrue(frappe.has_permission("Student Attendance", "create", doc=attendance, user=supervisor))
		attendance.student_group = self.group.name
		self.assertFalse(has_school_permission(attendance, "manage_attendance", supervisor))
		self.assertFalse(frappe.has_permission("Student Attendance", "manage_attendance", doc=attendance, user=supervisor))

	def test_workload_report_aggregates_adopted_expected_hours(self):
		from padars.reports import _require_reviewed_report_access
		manager = self._user("report-manager", ["Padars School Manager"])
		frappe.set_user(manager)
		_require_reviewed_report_access("Teacher Workload")
		frappe.set_user(self._user("report-outsider"))
		with self.assertRaises(frappe.PermissionError):
			_require_reviewed_report_access("Teacher Workload")
		frappe.set_user("Administrator")
		section = self._class_section()
		offering_name = generate_course_offerings(section.name)["offerings"][0]
		instructor = self._instructor("workload")
		user = self._user("workload-teacher")
		link_instructor_to_user(instructor.name, user)
		assign_teacher_to_offering(offering_name, instructor.name)
		rows = get_teacher_workload_data({"academic_year": self.year.name})
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["instructor"], instructor.name)
		self.assertEqual(rows[0]["offering_count"], 1)
		self.assertEqual(rows[0]["expected_weekly_hours"], 5)

	def test_only_school_manager_can_link_or_assign_staff(self):
		user = self._user("unassigned")
		instructor = self._instructor("denied")
		offering = self._offering(self.group, self.course)
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			link_instructor_to_user(instructor.name, user)
		with self.assertRaises(frappe.PermissionError):
			assign_teacher_to_offering(offering.name, instructor.name)
		frappe.set_user("Administrator")

	def test_instructor_qualifications_reject_duplicates(self):
		instructor = self._instructor("qualified")
		instructor.append("padars_qualifications", {"course": self.course.name, "grade_level": "10"})
		instructor.save()
		self.assertTrue(instructor.padars_qualifications[0].qualification_key)
		instructor.append("padars_qualifications", {"course": self.course.name, "grade_level": "10"})
		with self.assertRaises(frappe.ValidationError):
			instructor.save()
