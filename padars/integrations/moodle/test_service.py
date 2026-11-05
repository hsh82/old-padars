from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

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


class TestMoodleService(FrappeTestCase):
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
		self.school = get_or_create_test_school(self.year.name, f"SYNC-{self.key}")
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

