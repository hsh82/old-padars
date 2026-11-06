from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from padars.integrations.moodle.mock import MockMoodleAdapter
from padars.integrations.moodle.service import (
	process_sync_operation,
	request_course_offering_sync,
	request_school_tenant_sync,
)


class FailingMoodleAdapter:
	name = "Failing Mock"

	def ensure_tenant(self, school):
		raise RuntimeError("mock remote failure")

	def create_course(self, offering):
		raise RuntimeError("mock remote failure")


class TestMoodleService(IntegrationTestCase):
	def setUp(self):
		super().setUp()
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
		self.school = get_or_create_test_school(self.year.name, f"SYNC-{self.key}")
		self.school.db_set("lms_enabled", 1, update_modified=False)
		self.school.reload()
		self.program = frappe.get_doc(
			{"doctype": "Program", "program_name": f"Sync Grade 12 {self.key}"}
		).insert()
		self.course = frappe.get_doc(
			{"doctype": "Course", "course_name": f"Sync Biology {self.key}"}
		).insert()
		self.group = frappe.get_doc(
			{
				"doctype": "Student Group",
				"student_group_name": f"Sync 12-1 {self.key}",
				"academic_year": self.year.name,
				"group_based_on": "Course",
				"program": self.program.name,
				"course": self.course.name,
				"padars_school": self.school.name,
			}
		).insert()
		self.offering = frappe.get_doc(
			{
				"doctype": "School Course Offering",
				"school": self.school.name,
				"academic_year": self.year.name,
				"program": self.program.name,
				"course": self.course.name,
				"student_group": self.group.name,
				"offering_identifier": f"SYNC-BIO-12-1-{self.key}",
			}
		).insert()

	def test_mock_adapter_is_deterministic(self):
		adapter = MockMoodleAdapter()
		self.assertEqual(
			adapter.create_course(self.offering), adapter.create_course(self.offering)
		)

	def test_course_provisioning_is_idempotent(self):
		with patch("frappe.enqueue"):
			first = request_course_offering_sync(self.offering)
			second = request_course_offering_sync(self.offering)
		self.assertEqual(first.name, second.name)
		processed = process_sync_operation(first.name, adapter=MockMoodleAdapter())
		self.assertEqual(processed.state, "Succeeded")
		self.assertEqual(
			frappe.db.count("LMS Entity Mapping", {"local_name": self.offering.name}), 1
		)

	def test_tenant_provisioning_is_idempotent(self):
		with patch("frappe.enqueue"):
			first = request_school_tenant_sync(self.school)
			second = request_school_tenant_sync(self.school)
		self.assertEqual(first.name, second.name)
		processed = process_sync_operation(first.name, adapter=MockMoodleAdapter())
		self.assertEqual(processed.state, "Succeeded")
		self.assertEqual(
			frappe.db.count(
				"LMS Entity Mapping",
				{"local_doctype": "School", "local_name": self.school.name},
			),
			1,
		)

	def test_company_enablement_automatically_queues_tenant_after_commit(self):
		self.school.db_set("lms_enabled", 0, update_modified=False)
		self.school.reload()
		from padars.api import set_school_lms_enabled

		original_user = frappe.session.user
		try:
			frappe.set_user("Administrator")
			with patch("frappe.enqueue") as enqueue:
				result = set_school_lms_enabled(self.school.name, 1)
		finally:
			frappe.set_user(original_user)

		self.assertEqual(result["enabled"], 1)
		self.assertEqual(result["status"], "Provisioning")
		self.assertNotIn("lms_installation_uuid", result)
		self.assertEqual(enqueue.call_count, 1)
		self.assertTrue(enqueue.call_args.kwargs["enqueue_after_commit"])

	def test_school_manager_can_sync_course_but_cannot_manage_tenant(self):
		manager_email = f"moodle-manager-{self.key.lower()}@example.test"
		manager = frappe.get_doc({
			"doctype": "User",
			"email": manager_email,
			"first_name": "Moodle",
			"last_name": "Manager",
			"enabled": 1,
			"user_type": "System User",
			"send_welcome_email": 0,
			"roles": [{"role": "Padars School Manager"}],
		}).insert(ignore_permissions=True)
		original_user = frappe.session.user
		try:
			frappe.set_user(manager.name)
			from padars.permissions import is_lms_operator

			self.assertEqual(frappe.session.user, manager.name)
			self.assertFalse(is_lms_operator(manager.name))
			self.assertFalse(frappe.has_permission("LMS Settings", "write", user=manager.name))
			school = frappe.get_doc("School", self.school.name)
			current_auto_enrollment = int(frappe.db.get_value("School", school.name, "lms_auto_enrollment") or 0)
			school.lms_auto_enrollment = 1 - current_auto_enrollment
			self.assertNotEqual(school.lms_auto_enrollment, current_auto_enrollment)
			school.save()
			self.assertEqual(
				int(frappe.db.get_value("School", school.name, "lms_auto_enrollment") or 0),
				current_auto_enrollment,
			)
			school.reload()
			school.lms_tenant_id = "999"
			with self.assertRaises(frappe.PermissionError):
				school.save()
			with patch("frappe.enqueue"):
				operation = request_course_offering_sync(self.offering)
			self.assertEqual(operation.operation_type, "Provision Course")
			with self.assertRaises(frappe.PermissionError):
				request_school_tenant_sync(self.school)
			from padars.api import set_school_lms_enabled

			with self.assertRaises(frappe.PermissionError):
				set_school_lms_enabled(self.school.name, 0)
		finally:
			frappe.set_user(original_user)

	def test_mocked_school_flow_enrolls_one_teacher_and_three_students(self):
		from padars.api import request_student_enrollments
		from padars.integrations.moodle.teacher_identity import link_instructor_to_user

		teacher_user = frappe.get_doc({
			"doctype": "User",
			"email": f"teacher-{self.key.lower()}@example.test",
			"first_name": "Moodle Teacher",
			"send_welcome_email": 0,
			"enabled": 1,
			"user_type": "System User",
			"roles": [{"role": "Padars Read Only"}, {"role": "Padars Teacher"}],
		}).insert(ignore_permissions=True)
		instructor = frappe.get_doc({
			"doctype": "Instructor",
			"instructor_name": f"Teacher {self.key}",
		}).insert()
		manager = frappe.get_doc({
			"doctype": "User",
			"email": f"course-manager-{self.key.lower()}@example.test",
			"first_name": "Course Manager",
			"send_welcome_email": 0,
			"enabled": 1,
			"user_type": "System User",
			"roles": [{"role": "Padars School Manager"}],
		}).insert(ignore_permissions=True)
		original_user = frappe.session.user
		try:
			frappe.set_user(manager.name)
			link_instructor_to_user(instructor.name, teacher_user.name)
		finally:
			frappe.set_user(original_user)
		previous_flag = frappe.flags.get("padars_teacher_assignment_update")
		frappe.flags.padars_teacher_assignment_update = True
		try:
			self.offering.instructor = instructor.name
			self.offering.save()
		finally:
			frappe.flags.padars_teacher_assignment_update = previous_flag

		students = []
		for index in range(3):
			user = frappe.get_doc({
				"doctype": "User",
				"email": f"learner-{index}-{self.key.lower()}@example.test",
				"first_name": f"Learner {index}",
				"send_welcome_email": 0,
				"enabled": 1,
				"user_type": "System User",
				"roles": [{"role": "Padars Read Only"}, {"role": "Student"}],
			}).insert(ignore_permissions=True)
			with patch("education.education.doctype.student.student.Student.on_update"):
				student = frappe.get_doc({
					"doctype": "Student",
					"first_name": f"Learner {index}",
					"student_email_id": user.name,
					"user": user.name,
					"enabled": 1,
				}).insert()
			enrollment = frappe.get_doc({
				"doctype": "Program Enrollment",
				"student": student.name,
				"program": self.program.name,
				"academic_year": self.year.name,
				"enrollment_date": "2099-01-01",
				"padars_school": self.school.name,
			}).insert()
			enrollment.submit()
			self.group.append("students", {"student": student.name, "active": 1})
			students.append(student.name)
		self.group.save()

		original_user = frappe.session.user
		try:
			frappe.set_user(manager.name)
			with patch("frappe.enqueue"):
				course_operation = request_course_offering_sync(self.offering)
				course_result = process_sync_operation(course_operation.name, adapter=MockMoodleAdapter())
				student_operations = request_student_enrollments(self.offering.name, students)
				states = frappe.get_all(
					"LMS Enrollment State",
					filters={"course_offering": self.offering.name},
					fields=["name", "role", "user"],
					ignore_permissions=True,
				)
				teacher_states = [row for row in states if row.role == "Teacher"]
				self.assertEqual(len(teacher_states), 1)
				self.assertEqual(teacher_states[0].user, teacher_user.name)
				for state in states:
					queued = frappe.get_all(
						"LMS Sync Operation",
						filters={
							"target_doctype": "LMS Enrollment State",
							"target_name": state.name,
						"state": "Queued",
					},
						pluck="name",
						ignore_permissions=True,
					)
					for operation_name in queued:
						process_sync_operation(operation_name, adapter=MockMoodleAdapter())
		finally:
			frappe.set_user(original_user)

		self.assertEqual(course_result.state, "Succeeded")
		self.assertEqual(len([row for row in states if row.role == "Student"]), 3)
		self.assertEqual(len(student_operations), 3)
		self.assertTrue(all(row.remote_state == "Enrolled" for row in frappe.get_all(
			"LMS Enrollment State",
			filters={"course_offering": self.offering.name},
			fields=["remote_state"],
			ignore_permissions=True,
		)))

		# Access can be withdrawn after a student leaves the local roster.
		student_user = frappe.db.get_value("Student", students[0], "user")
		state_name = frappe.db.get_value("LMS Enrollment State", {
			"course_offering": self.offering.name, "user": student_user, "role": "Student",
		}, "name")
		self.group.reload()
		self.school.db_set("lms_auto_enrollment", 1, update_modified=False)
		for row in self.group.students:
			if row.student == students[0]:
				row.active = 0
		with patch("frappe.enqueue") as enqueue:
			self.group.save()
		state = frappe.get_doc("LMS Enrollment State", state_name)
		self.assertEqual(state.desired_state, "Not Enrolled")
		self.assertTrue(any(call.kwargs.get("enqueue_after_commit") for call in enqueue.call_args_list))
		operation_name = frappe.db.get_value("LMS Sync Operation", {
			"target_name": state.name, "target_doctype": "LMS Enrollment State", "state": "Queued",
		}, "name")
		self.assertTrue(operation_name)
		from padars.integrations.moodle.service import process_remote_operation
		with patch("frappe.get_all", return_value=[frappe._dict(desired_state="Enrolled", remote_state="Enrolled")]):
			with self.assertRaises(frappe.ValidationError):
				process_remote_operation(frappe.get_doc("LMS Sync Operation", operation_name), MockMoodleAdapter())
		adapter = MockMoodleAdapter()
		with patch("frappe.enqueue"), patch.object(adapter, "ensure_user", side_effect=AssertionError("unexpected user provisioning")), \
			patch.object(adapter, "create_course", side_effect=AssertionError("unexpected course provisioning")):
			result = process_sync_operation(operation_name, adapter=adapter)
		self.assertEqual(result.state, "Succeeded")
		self.assertEqual(frappe.db.get_value("LMS Enrollment State", state_name, "remote_state"), "Not Enrolled")
		withdrawal_revision = state.desired_revision
		self.group.reload()
		for row in self.group.students:
			if row.student == students[0]:
				row.active = 1
		with patch("frappe.enqueue"):
			self.group.save()
		state.reload()
		self.assertEqual(state.desired_state, "Enrolled")
		self.assertEqual(state.desired_revision, withdrawal_revision + 1)

		# Replacing the instructor queues the new teacher and withdraws the old one.
		from padars.staff import assign_teacher_to_offering
		new_user = frappe.get_doc({
			"doctype": "User", "email": f"replacement-{self.key.lower()}@example.test",
			"first_name": "Replacement", "send_welcome_email": 0,
			"enabled": 1, "user_type": "System User",
			"roles": [{"role": "Padars Read Only"}, {"role": "Padars Teacher"}],
		}).insert(ignore_permissions=True)
		new_instructor = frappe.get_doc({"doctype": "Instructor", "instructor_name": f"Replacement {self.key}"}).insert()
		original_user = frappe.session.user
		try:
			frappe.set_user(manager.name)
			link_instructor_to_user(new_instructor.name, new_user.name)
			with patch("frappe.enqueue"):
				assign_teacher_to_offering(self.offering.name, new_instructor.name)
		finally:
			frappe.set_user(original_user)
		old_state = frappe.get_doc("LMS Enrollment State", teacher_states[0].name)
		self.assertEqual(old_state.desired_state, "Not Enrolled")
		new_state_name = frappe.db.get_value("LMS Enrollment State", {
			"course_offering": self.offering.name, "user": new_user.name,
			"role": "Teacher", "desired_state": "Enrolled",
		}, "name")
		self.assertTrue(new_state_name)
		for target in (old_state.name, new_state_name):
			operation_name = frappe.db.get_value("LMS Sync Operation", {
				"target_doctype": "LMS Enrollment State", "target_name": target, "state": "Queued",
			}, "name")
			self.assertTrue(operation_name)
			with patch("frappe.enqueue"):
				result = process_sync_operation(operation_name, adapter=MockMoodleAdapter())
			self.assertEqual(result.state, "Succeeded")
		self.assertEqual(frappe.db.get_value("LMS Enrollment State", old_state.name, "remote_state"), "Not Enrolled")
		self.assertEqual(frappe.db.get_value("LMS Enrollment State", new_state_name, "remote_state"), "Enrolled")
		self.assertEqual(frappe.db.count("LMS Entity Mapping", {
			"school": self.school.name, "local_doctype": "School Course Offering", "local_name": self.offering.name,
		}), 1)

	def test_failure_is_recorded_and_retry_can_succeed(self):
		with patch("frappe.enqueue"):
			operation = request_course_offering_sync(self.offering)
		failed = process_sync_operation(operation.name, adapter=FailingMoodleAdapter())
		self.assertEqual(failed.state, "Failed")
		self.assertEqual(failed.attempt_count, 1)
		self.assertIn("mock remote failure", failed.last_error)

		with patch("frappe.enqueue"):
			from padars.integrations.moodle.service import retry_sync_operation

			retry_sync_operation(failed.name)
		succeeded = process_sync_operation(failed.name, adapter=MockMoodleAdapter())
		self.assertEqual(succeeded.state, "Succeeded")

	def test_course_follow_up_queue_failure_remains_retryable(self):
		with patch("frappe.enqueue"):
			operation = request_course_offering_sync(self.offering)
		with patch(
			"padars.integrations.moodle.service.queue_offering_staff_enrollments",
			side_effect=RuntimeError("staff enrollment setup failed"),
		):
			failed = process_sync_operation(operation.name, adapter=MockMoodleAdapter())
		self.assertEqual(failed.state, "Failed")
		self.assertIn("staff enrollment setup failed", failed.last_error)

		with patch("frappe.enqueue"):
			from padars.integrations.moodle.service import retry_sync_operation

			retry_sync_operation(failed.name)
		succeeded = process_sync_operation(failed.name, adapter=MockMoodleAdapter())
		self.assertEqual(succeeded.state, "Succeeded")

