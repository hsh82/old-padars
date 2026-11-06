from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from padars.daily_operations import get_student_attendance_records, get_student_leave_groups, mark_attendance
from padars.padars.report.daily_attendance_register.daily_attendance_register import execute as run_attendance_report
from padars.permissions_site import has_school_permission
from padars.reports import DAILY_ATTENDANCE_REPORT, _require_reviewed_report_access
from padars.tests.utils import get_or_create_test_school


class TestDailyOperations(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		frappe.db.savepoint("padars_daily_operations_test")
		self.key = frappe.generate_hash(length=8).upper()
		self.year = frappe.get_doc({
			"doctype": "Academic Year", "academic_year_name": f"OPS-{self.key}",
			"year_start_date": "2020-01-01", "year_end_date": "2100-12-31",
		}).insert()
		self.school = get_or_create_test_school(self.year.name, f"OPS-{self.key}")
		self.course = frappe.get_doc({"doctype": "Course", "course_name": f"Course-{self.key}"}).insert()
		self.program = frappe.get_doc({
			"doctype": "Program", "program_name": f"Program-{self.key}",
			"padars_grade_level": "11", "padars_stream": f"Stream-{self.key}",
			"courses": [{"course": self.course.name, "required": 1}],
		}).insert()
		self.group = self._group("A")
		self.other_group = self._group("B")
		self.instructor = frappe.get_doc({"doctype": "Instructor", "instructor_name": f"Instructor-{self.key}"}).insert()
		self.room = frappe.get_doc({"doctype": "Room", "room_name": f"Room-{self.key}"}).insert()
		self.staff = self._user("staff", ["Padars Academic Staff"])
		self.student_a, self.student_a_user = self._student("a", self.group)
		self.student_b, self.student_b_user = self._student("b", self.group)
		self.student_other, _ = self._student("other", self.other_group)
		self._assignment(self.staff, self.group, can_manage_attendance=1)

	def tearDown(self):
		frappe.set_user("Administrator")
		try:
			frappe.db.rollback(save_point="padars_daily_operations_test")
		finally:
			super().tearDown()

	def _group(self, suffix):
		return frappe.get_doc({
			"doctype": "Student Group", "student_group_name": f"{suffix}-{self.key}",
			"academic_year": self.year.name, "group_based_on": "Course",
			"program": self.program.name, "course": self.course.name,
			"padars_school": self.school.name,
		}).insert()

	def _user(self, prefix, roles):
		old = frappe.flags.in_import
		frappe.flags.in_import = True
		try:
			user = frappe.get_doc({
				"doctype": "User", "email": f"{prefix}-{self.key.lower()}@example.invalid",
				"first_name": prefix, "send_welcome_email": 0, "enabled": 1,
				"user_type": "System User", "roles": [{"role": role} for role in roles],
			}).insert(ignore_permissions=True)
		finally:
			frappe.flags.in_import = old
		return user.name

	def _student(self, suffix, group):
		user = self._user(f"student-{suffix}", ["Student"])
		with patch("education.education.doctype.student.student.Student.on_update"):
			student = frappe.get_doc({
				"doctype": "Student", "first_name": suffix,
				"student_email_id": user, "user": user, "enabled": 1,
			}).insert(ignore_permissions=True)
		frappe.get_doc({
			"doctype": "Program Enrollment", "student": student.name,
			"program": self.program.name, "academic_year": self.year.name,
			"enrollment_date": "2020-01-01", "padars_school": self.school.name,
		}).insert().submit()
		group.append("students", {"student": student.name, "active": 1})
		group.save()
		return student.name, user

	def _assignment(self, user, group, **values):
		return frappe.get_doc({
			"doctype": "Academic Assignment", "user": user,
			"assignment_type": "Scoped Staff", "scope_type": "Student Group",
			"scope_name": group.name, **values,
		}).insert()

	def _schedule(self, date, from_time="09:00:00"):
		return frappe.get_doc({
			"doctype": "Course Schedule", "student_group": self.group.name,
			"course": self.course.name, "program": self.program.name,
			"instructor": self.instructor.name, "room": self.room.name,
			"schedule_date": date, "from_time": from_time,
			"to_time": "10:00:00",
		}).insert()

	def test_scoped_bulk_attendance_records_late_minutes_and_rejects_other_groups(self):
		schedule = self._schedule(today())
		frappe.set_user(self.staff)
		with patch("education.education.doctype.student_attendance.student_attendance.is_holiday", return_value=False), \
			patch("padars.daily_operations.is_holiday", return_value=False):
			result = mark_attendance(
				[{"student": self.student_a, "student_name": "a"}],
				[{"student": self.student_b, "student_name": "b"}],
				course_schedule=schedule.name, students_late={self.student_a: 8},
			)
		self.assertEqual(result["marked"], 2)
		att_a = frappe.get_doc("Student Attendance", frappe.db.get_value(
			"Student Attendance", {"student": self.student_a, "course_schedule": schedule.name}, "name"
		))
		att_b = frappe.get_doc("Student Attendance", frappe.db.get_value(
			"Student Attendance", {"student": self.student_b, "course_schedule": schedule.name}, "name"
		))
		self.assertEqual((att_a.docstatus, att_a.status, att_a.padars_late_minutes), (1, "Present", 8))
		self.assertEqual((att_b.docstatus, att_b.status, att_b.padars_late_minutes), (1, "Absent", 0))
		mark_attendance(
			[{"student": self.student_a}, {"student": self.student_b}], [],
			course_schedule=schedule.name, students_late={self.student_a: 11},
		)
		att_a.reload()
		att_b.reload()
		self.assertEqual(att_a.padars_late_minutes, 11)
		self.assertEqual(att_b.status, "Present")
		group_date = add_days(today(), -1)
		with patch("education.education.doctype.student_attendance.student_attendance.is_holiday", return_value=False), \
			patch("padars.daily_operations.is_holiday", return_value=False):
			mark_attendance(
				[{"student": self.student_a}], [{"student": self.student_b}],
				student_group=self.group.name, date=group_date,
			)
		roster = get_student_attendance_records("Student Group", group_date, self.group.name)
		self.assertEqual({row.student: row.status for row in roster}, {
			self.student_a: "Present", self.student_b: "Absent",
		})
		with self.assertRaises(frappe.PermissionError):
			mark_attendance(
				[{"student": self.student_other}], [], student_group=self.other_group.name, date=today(),
			)
		frappe.set_user(self.student_a_user)
		with self.assertRaises(frappe.PermissionError):
			mark_attendance(
				[{"student": self.student_a}, {"student": self.student_b}], [],
				course_schedule=schedule.name,
			)

	def test_approved_leave_creates_only_its_session_records_and_cancels_only_those(self):
		date_a = add_days(today(), -2)
		date_b = add_days(today(), -1)
		schedule_a = self._schedule(date_a)
		schedule_b = self._schedule(date_b)
		frappe.set_user("Administrator")
		with patch("education.education.doctype.student_attendance.student_attendance.is_holiday", return_value=False), \
			patch("padars.daily_operations.is_holiday", return_value=False):
			existing_absent = frappe.get_doc({
				"doctype": "Student Attendance", "student": self.student_a,
				"student_name": "a", "student_group": self.group.name,
				"course_schedule": schedule_a.name, "status": "Absent",
			}).insert()
			existing_absent.submit()
			unrelated = frappe.get_doc({
				"doctype": "Student Attendance", "student": self.student_b,
				"student_name": "b", "student_group": self.group.name,
				"course_schedule": schedule_a.name, "status": "Present",
			}).insert()
			unrelated.submit()
			leave = frappe.get_doc({
				"doctype": "Student Leave Application", "student": self.student_a,
				"attendance_based_on": "Student Group", "student_group": self.group.name,
				"from_date": date_a, "to_date": date_b, "reason": "Approved absence",
			}).insert()
			self.assertEqual(leave.total_leave_days, 2)
			frappe.set_user(self.staff)
			leave.submit()
			leave_attendance = frappe.get_all(
				"Student Attendance", filters={"leave_application": leave.name},
				fields=["name", "course_schedule", "status", "docstatus"],
			)
			self.assertEqual({row.course_schedule for row in leave_attendance}, {schedule_a.name, schedule_b.name})
			self.assertTrue(all(row.status == "Leave" and row.docstatus == 1 for row in leave_attendance))
			leave.cancel()
		self.assertEqual(frappe.db.get_value("Student Attendance", unrelated.name, "docstatus"), 1)
		self.assertEqual(frappe.db.get_value("Student Attendance", existing_absent.name, "docstatus"), 1)
		self.assertEqual(frappe.db.get_value("Student Attendance", existing_absent.name, "status"), "Absent")
		self.assertFalse(frappe.db.get_value("Student Attendance", existing_absent.name, "leave_application"))
		created_for_leave = next(row for row in leave_attendance if row.course_schedule == schedule_b.name)
		self.assertEqual(frappe.db.get_value("Student Attendance", created_for_leave.name, "docstatus"), 2)

	def test_student_care_writes_and_reads_require_an_active_assignment(self):
		reader = self._user("care", ["Padars Academic Staff"])
		self._assignment(reader, self.group, can_manage_student_care=1)
		frappe.set_user("Administrator")
		inside = frappe.get_doc({
			"doctype": "Student Log", "student": self.student_a,
			"type": "Academic", "date": today(),
		}).insert()
		outside = frappe.get_doc({
			"doctype": "Student Log", "student": self.student_other,
			"type": "Academic", "date": today(),
		}).insert()
		frappe.set_user(reader)
		self.assertTrue(frappe.has_permission("Student Log", "read", inside.name))
		self.assertFalse(frappe.has_permission("Student Log", "read", outside.name))
		new_log = frappe.new_doc("Student Log")
		new_log.student = self.student_a
		self.assertTrue(has_school_permission(new_log, "manage_student_care", reader))
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc({
				"doctype": "Student Log", "student": self.student_other,
				"type": "Medical", "date": today(),
			}).insert()

	def test_only_the_reviewed_daily_attendance_report_is_available_to_scoped_staff(self):
		frappe.set_user("Administrator")
		for student, group in ((self.student_a, self.group), (self.student_other, self.other_group)):
			with patch("education.education.doctype.student_attendance.student_attendance.is_holiday", return_value=False):
				attendance = frappe.new_doc("Student Attendance")
				attendance.student = student
				attendance.student_group = group.name
				attendance.date = today()
				attendance.status = "Present"
				attendance.insert()
				attendance.submit()
		frappe.set_user(self.staff)
		self.assertTrue(frappe.has_permission("Student Attendance", "report"))
		_require_reviewed_report_access(DAILY_ATTENDANCE_REPORT)
		_, rows = run_attendance_report({"from_date": today(), "to_date": today()})
		self.assertIn(self.group.name, {row.student_group for row in rows})
		self.assertNotIn(self.other_group.name, {row.student_group for row in rows})
		with self.assertRaises(frappe.PermissionError):
			_require_reviewed_report_access("Student Batch-Wise Attendance")

	def test_student_leave_group_lookup_only_returns_the_students_own_groups(self):
		frappe.set_user(self.student_a_user)
		self.assertEqual(get_student_leave_groups(self.student_a), [self.group.name])
		leave = frappe.new_doc("Student Leave Application")
		leave.student = self.student_a
		leave.student_group = self.group.name
		self.assertTrue(frappe.has_permission("Student Leave Application", "create", doc=leave))
		self.assertFalse(frappe.has_permission("Student Leave Application", "submit", doc=leave))
		with self.assertRaises(frappe.PermissionError):
			get_student_leave_groups(self.student_other)
