from calendar import day_name
from datetime import timedelta
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, today

from padars.curriculum import create_curriculum_adoption_from_program, generate_course_offerings
from padars.scheduling import validate_assessment_result_relationships, validate_course_schedule_deletion
from padars.staff import assign_teacher_to_offering, link_instructor_to_user
from padars.tests.utils import get_or_create_test_school


class TestScheduling(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		frappe.db.savepoint("padars_scheduling_test")
		self.key = frappe.generate_hash(length=8).upper()
		self.year = frappe.get_doc({
			"doctype": "Academic Year", "academic_year_name": f"T-{self.key}",
			"year_start_date": "2020-01-01", "year_end_date": "2100-12-31",
		}).insert()
		self.school = get_or_create_test_school(self.year.name, f"T-{self.key}")
		self.course = frappe.get_doc({"doctype": "Course", "course_name": f"Course-{self.key}"}).insert()
		self.program = frappe.get_doc({
			"doctype": "Program", "program_name": f"Program-{self.key}",
			"padars_grade_level": "11", "padars_stream": f"Stream-{self.key}",
			"courses": [{"course": self.course.name, "required": 1}],
		}).insert()
		adoption = frappe.get_doc("School Curriculum Adoption",
			create_curriculum_adoption_from_program(self.program.name, self.year.name)["name"])
		adoption.courses[0].weekly_hours = 2
		adoption.status = "Active"
		adoption.save()
		self.group = frappe.get_doc({
			"doctype": "Student Group", "student_group_name": f"Section-{self.key}",
			"academic_year": self.year.name, "group_based_on": "Batch", "program": self.program.name,
			"padars_school": self.school.name, "padars_is_class_section": 1,
			"padars_section_code": f"A-{self.key}", "padars_curriculum_adoption": adoption.name,
		}).insert()
		offering_name = generate_course_offerings(self.group.name)["offerings"][0]
		self.offering = frappe.get_doc("School Course Offering", offering_name)
		self.instructor = frappe.get_doc({
			"doctype": "Instructor", "instructor_name": f"Instructor-{self.key}",
		}).insert()
		user = self._user("teacher")
		link_instructor_to_user(self.instructor.name, user)
		assign_teacher_to_offering(self.offering.name, self.instructor.name)
		self.offering.reload()
		self.room = frappe.get_doc({"doctype": "Room", "room_name": f"Room-{self.key}"}).insert()

	def tearDown(self):
		frappe.set_user("Administrator")
		try:
			frappe.db.rollback(save_point="padars_scheduling_test")
		finally:
			super().tearDown()

	def _user(self, prefix):
		old = frappe.flags.in_import
		frappe.flags.in_import = True
		try:
			user = frappe.get_doc({
				"doctype": "User", "email": f"{prefix}-{self.key.lower()}@example.invalid",
				"first_name": prefix, "send_welcome_email": 0, "enabled": 1,
				"user_type": "System User", "roles": [{"role": "Padars Read Only"}],
			}).insert(ignore_permissions=True)
		finally:
			frappe.flags.in_import = old
		return user.name

	def _monday(self, year="2099"):
		start = getdate(f"{year}-01-01")
		return start + timedelta(days=(0 - start.weekday()) % 7)

	def _schedule(self, group, date, from_time, to_time, room=None, offering=None, instructor=None):
		return frappe.get_doc({
			"doctype": "Course Schedule", "student_group": group.name,
			"course": group.course or self.course.name, "program": group.program,
			"instructor": instructor or self.instructor.name,
			"room": (room or self.room).name, "schedule_date": date,
			"from_time": from_time, "to_time": to_time,
			"padars_course_offering": offering,
		}).insert()

	def _other_group(self):
		return frappe.get_doc({
			"doctype": "Student Group", "student_group_name": f"Other-{self.key}",
			"academic_year": self.year.name, "group_based_on": "Course",
			"program": self.program.name, "course": self.course.name,
			"padars_school": self.school.name,
		}).insert()

	def _assessment_plan(self, group, date, examiner=None, from_time="13:00:00", to_time="14:00:00", room=None):
		root = frappe.get_doc("Assessment Group", "All Assessment Groups")
		assessment_group = frappe.get_doc({
			"doctype": "Assessment Group", "assessment_group_name": f"AG-{self.key}",
			"parent_assessment_group": root.name, "is_group": 0,
		}).insert()
		criteria = frappe.get_doc({
			"doctype": "Assessment Criteria", "assessment_criteria": f"Criteria-{self.key}",
		}).insert()
		scale = frappe.get_doc({
			"doctype": "Grading Scale", "grading_scale_name": f"Scale-{self.key}",
			"intervals": [
				{"grade_code": "F", "threshold": 0},
				{"grade_code": "P", "threshold": 50},
			],
		}).insert()
		scale.submit()
		return frappe.get_doc({
			"doctype": "Assessment Plan", "student_group": group.name,
			"program": group.program, "course": group.course or self.course.name,
			"academic_year": group.academic_year, "assessment_group": assessment_group.name,
			"grading_scale": scale.name, "schedule_date": date, "room": (room or self.room).name,
			"examiner": examiner, "from_time": from_time, "to_time": to_time,
			"maximum_assessment_score": 100,
			"assessment_criteria": [{"assessment_criteria": criteria.name, "maximum_score": 100}],
		}).insert()

	def test_native_weekly_tool_creates_course_offering_linked_sessions(self):
		start = self._monday()
		end = start + timedelta(days=7)
		tool = frappe.get_doc({
			"doctype": "Course Scheduling Tool", "student_group": self.group.name,
			"course": self.course.name, "instructor": self.instructor.name,
			"room": self.room.name, "from_time": "09:00:00", "to_time": "10:00:00",
			"course_start_date": start, "course_end_date": end,
		})
		result = tool.schedule_course([day_name[start.weekday()]])
		self.assertEqual(len(result["course_schedules"]), 1)
		schedule = frappe.get_doc("Course Schedule", result["course_schedules"][0].name)
		self.assertEqual(schedule.padars_course_offering, self.offering.name)
		self.assertEqual(schedule.padars_school, self.school.name)

		other_group = self._other_group()
		other_instructor = frappe.get_doc({
			"doctype": "Instructor", "instructor_name": f"Other-{self.key}",
		}).insert()
		other_room = frappe.get_doc({"doctype": "Room", "room_name": f"Other-{self.key}"}).insert()
		with self.assertRaises(frappe.ValidationError):
			self._schedule(other_group, start, "09:30:00", "10:30:00", instructor=other_instructor.name)
		with self.assertRaises(frappe.ValidationError):
			self._schedule(other_group, start, "09:30:00", "10:30:00", room=other_room)
		with self.assertRaises(frappe.ValidationError):
			self._schedule(self.group, start, "09:30:00", "10:30:00",
				room=other_room, instructor=other_instructor.name, offering=self.offering.name)

	def test_examiner_cannot_overlap_a_course_schedule(self):
		date = self._monday()
		self._schedule(self.group, date, "09:00:00", "10:00:00", offering=self.offering.name)
		other_group = self._other_group()
		other_room = frappe.get_doc({"doctype": "Room", "room_name": f"Exam-{self.key}"}).insert()
		with self.assertRaises(frappe.ValidationError):
			self._assessment_plan(other_group, date, examiner=self.instructor.name,
				from_time="09:30:00", to_time="10:30:00", room=other_room)

	def test_assessment_plan_and_result_keep_authoritative_relationships(self):
		plan = self._assessment_plan(self.group, self._monday(), examiner=self.instructor.name)
		self.assertEqual(plan.padars_course_offering, self.offering.name)
		result = frappe.new_doc("Assessment Result")
		result.assessment_plan = plan.name
		validate_assessment_result_relationships(result)
		self.assertEqual(result.student_group, self.group.name)
		self.assertEqual(result.course, self.course.name)
		self.assertEqual(result.padars_course_offering, self.offering.name)

		result.course = "Another Course"
		with self.assertRaises(frappe.ValidationError):
			validate_assessment_result_relationships(result)

	def test_assessment_scores_use_complete_plan_criteria_and_server_maxima(self):
		from padars.assessment import validate_result_ready_for_approval
		plan = self._assessment_plan(self.group, self._monday(), examiner=self.instructor.name)
		criterion = plan.assessment_criteria[0].assessment_criteria
		result = frappe.new_doc("Assessment Result")
		result.assessment_plan = plan.name
		with self.assertRaises(frappe.ValidationError):
			validate_result_ready_for_approval(result)
		result.maximum_score = 999
		result.append("details", {"assessment_criteria": criterion, "score": 60})
		result.run_method("before_validate")
		self.assertEqual(result.maximum_score, 100)
		for invalid in (-1, 101, float("nan")):
			result.details[0].score = invalid
			with self.assertRaises(frappe.ValidationError):
				result.run_method("before_validate")
		result.details[0].score = 60
		result.append("details", {"assessment_criteria": criterion, "score": 10})
		with self.assertRaises(frappe.ValidationError):
			result.run_method("before_validate")
		result.details = []
		with self.assertRaises(frappe.ValidationError):
			result.run_method("before_validate")

	def test_assessment_form_criteria_are_limited_to_readable_plans(self):
		from padars.assessment import get_assessment_details
		plan = self._assessment_plan(self.group, self._monday(), examiner=self.instructor.name)
		teacher = frappe.db.get_value("Instructor", self.instructor.name, "padars_user")
		outsider = self._user("outside")
		try:
			frappe.set_user(teacher)
			criteria = get_assessment_details(plan.name)
			self.assertEqual(criteria[0]["assessment_criteria"], plan.assessment_criteria[0].assessment_criteria)
			self.assertEqual(criteria[0]["maximum_score"], 100)
			frappe.set_user(outsider)
			with self.assertRaises(frappe.PermissionError):
				get_assessment_details(plan.name)
		finally:
			frappe.set_user("Administrator")

	def test_assigned_teacher_can_create_and_update_only_scoped_draft_results(self):
		from padars.assessment import get_assessment_students, mark_assessment_result, preview_approved_results
		student_user = self._user("learner")
		frappe.get_doc("User", student_user).add_roles("Student")
		with patch("education.education.doctype.student.student.Student.on_update"):
			student = frappe.get_doc({"doctype": "Student", "first_name": "Learner",
				"student_email_id": student_user, "user": student_user, "enabled": 1}).insert()
		frappe.get_doc({"doctype": "Program Enrollment", "student": student.name,
			"program": self.program.name, "academic_year": self.year.name,
			"enrollment_date": "2020-01-01", "padars_school": self.school.name}).insert().submit()
		self.group.append("students", {"student": student.name, "active": 1})
		self.group.save()
		plan = self._assessment_plan(self.group, self._monday(), examiner=self.instructor.name)
		plan.submit()
		criterion = plan.assessment_criteria[0].assessment_criteria
		teacher = frappe.db.get_value("Instructor", self.instructor.name, "padars_user")
		outsider = self._user("outsider")
		manager = self._user("approver")
		frappe.get_doc("User", manager).add_roles("Padars School Manager")
		try:
			frappe.set_user(teacher)
			self.assertTrue(frappe.has_permission("Assessment Result Tool", "read"))
			first = mark_assessment_result(plan.name, {"student": student.name, "assessment_details": {criterion: 70}})
			second = mark_assessment_result(plan.name, {"student": student.name, "assessment_details": {criterion: 80}, "expected_modified": first["modified"]})
			with self.assertRaises(frappe.TimestampMismatchError):
				mark_assessment_result(plan.name, {"student": student.name, "assessment_details": {criterion: 90}, "expected_modified": first["modified"]})
			self.assertEqual(first["name"], second["name"])
			self.assertEqual(second["total_score"], 80)
			from padars.scheduling import validate_assessment_plan
			frappe.set_user("Administrator")
			original_plan = frappe.get_doc("Assessment Plan", plan.name)
			changed_plan = frappe.get_doc("Assessment Plan", plan.name)
			changed_plan.assessment_criteria[0].maximum_score = 90
			changed_plan.maximum_assessment_score = 90
			with patch.object(changed_plan, "get_doc_before_save", return_value=original_plan):
				with self.assertRaises(frappe.ValidationError):
					validate_assessment_plan(changed_plan)
			frappe.set_user(manager)
			preview = preview_approved_results(student.name, self.program.name, self.year.name)
			self.assertEqual(preview["results"], [])
			self.assertEqual(preview["draft_count"], 1)
			self.assertIn(self.course.name, preview["courses_without_approved_results"])
			frappe.set_user(teacher)
			duplicate = frappe.copy_doc(frappe.get_doc("Assessment Result", first["name"]))
			with self.assertRaises(frappe.ValidationError):
				duplicate.insert(ignore_permissions=True)
			roster = get_assessment_students(plan.name, self.group.name)
			self.assertEqual(roster[0].student, student.name)
			self.assertEqual(float(roster[0].assessment_details[criterion][0]), 80)
			with self.assertRaises(frappe.PermissionError):
				get_assessment_students(plan.name, "unrelated-group")
			with self.assertRaises(frappe.ValidationError):
				mark_assessment_result(plan.name, {"student": student.name, "assessment_details": {criterion: -1}, "expected_modified": second["modified"]})
			frappe.set_user(outsider)
			self.assertFalse(frappe.has_permission("Assessment Result Tool", "read"))
			with self.assertRaises(frappe.PermissionError):
				mark_assessment_result(plan.name, {"student": student.name, "assessment_details": {criterion: 90}})
			with self.assertRaises(frappe.PermissionError):
				get_assessment_students(plan.name, self.group.name)
			frappe.set_user(teacher)
			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc("Assessment Result", first["name"]).submit()
			frappe.set_user("Administrator")
			permission = frappe.db.get_value("Custom DocPerm", {
				"parent": "Assessment Result", "role": "Padars School Manager", "permlevel": 0,
			}, "name")
			frappe.db.set_value("Custom DocPerm", permission, "approve_grade", 0)
			frappe.clear_cache(doctype="Assessment Result")
			frappe.set_user(manager)
			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc("Assessment Result", first["name"]).submit()
			frappe.set_user("Administrator")
			frappe.db.set_value("Custom DocPerm", permission, "approve_grade", 1)
			frappe.clear_cache(doctype="Assessment Result")
			frappe.set_user(manager)
			frappe.get_doc("Assessment Result", first["name"]).submit()
			preview = preview_approved_results(student.name, self.program.name, self.year.name)
			self.assertEqual([row["result"] for row in preview["results"]], [first["name"]])
			self.assertEqual(preview["results"][0]["total_score"], 80)
			self.assertEqual(preview["draft_count"], 0)
			self.assertNotIn(self.course.name, preview["courses_without_approved_results"])
			self.assertNotIn("comment", preview["results"][0])
			from padars.grading import calculate_scheme
			scheme = frappe.get_doc({"doctype": "School Assessment Scheme", "scheme_title": "Test scheme",
				"course_offering": self.offering.name, "grading_scale": plan.grading_scale,
				"output_maximum": 20, "decimal_places": 2,
				"components": [{"assessment_plan": plan.name, "assessment_criteria": criterion, "weight": 100}]}).insert()
			scheme.submit()
			calculated = calculate_scheme(scheme.name, student.name)
			self.assertEqual(calculated["score"], "16.00")
			self.assertEqual(calculated["grade"], "P")
			self.assertEqual(calculated["sources"][0]["result"], first["name"])
			self.assertEqual(scheme.approved_by, manager)
			from padars.publication import preview_report_card, publish_report_card, read_report_card, list_report_cards
			enrollment = frappe.db.get_value("Program Enrollment", {"student": student.name, "docstatus": 1}, "name")
			card = preview_report_card(enrollment, [scheme.name])
			with self.assertRaises(frappe.TimestampMismatchError):
				publish_report_card(enrollment, [scheme.name], "stale-digest")
			publication = publish_report_card(enrollment, [scheme.name], card["digest"])
			self.assertEqual(publication, publish_report_card(enrollment, [scheme.name], card["digest"]))
			self.assertEqual(read_report_card(publication["name"])["snapshot"]["courses"][0]["score"], "16.00")
			printed = frappe.get_print("Report Card Publication", publication["name"], print_format="Padars Report Card")
			self.assertIn("16.00", printed)
			import json
			probe = frappe._dict(frappe.get_doc("Report Card Publication", publication["name"]).as_dict())
			probe_snapshot = json.loads(probe.snapshot)
			probe_snapshot["student_name"] = "<script>alert(1)</script>"
			probe.snapshot = json.dumps(probe_snapshot)
			escaped = frappe.render_template(frappe.get_doc("Print Format", "Padars Report Card").html, {"doc": probe})
			self.assertNotIn("<script>alert(1)</script>", escaped)
			self.assertIn("&lt;script&gt;", escaped)
			from padars.publication import report_card_pdf
			pdf = report_card_pdf(publication["name"])
			self.assertTrue(pdf.startswith(b"%PDF"))
			published = frappe.get_doc("Report Card Publication", publication["name"])
			published.snapshot = "{}"
			with self.assertRaises(frappe.PermissionError):
				published.save(ignore_permissions=True)
			with self.assertRaises(frappe.PermissionError):
				frappe.delete_doc("Report Card Publication", publication["name"], ignore_permissions=True)
			scheme.output_maximum = 100
			with self.assertRaises(frappe.ValidationError):
				scheme.save()
			revised = frappe.copy_doc(scheme)
			revised.docstatus = 0
			revised.insert()
			revised.submit()
			correction = preview_report_card(enrollment, [revised.name])
			with self.assertRaises(frappe.ValidationError):
				publish_report_card(enrollment, [revised.name], correction["digest"])
			updated = publish_report_card(enrollment, [revised.name], correction["digest"], "School approved revised scale")
			self.assertEqual(updated["version"], 2)
			self.assertEqual(read_report_card(publication["name"])["snapshot"]["courses"][0]["score"], "16.00")
			self.assertEqual(read_report_card(updated["name"])["snapshot"]["courses"][0]["score"], "80.00")
			from padars.assessment import correct_assessment_result
			current = str(frappe.get_doc("Assessment Result", first["name"]).modified)
			with self.assertRaises(frappe.ValidationError):
				correct_assessment_result(first["name"], current, "")
			with patch("education.education.doctype.assessment_result.assessment_result.AssessmentResult.insert", side_effect=frappe.ValidationError("test correction failure")):
				with self.assertRaises(frappe.ValidationError):
					correct_assessment_result(first["name"], current, "Review score")
			self.assertEqual(frappe.db.get_value("Assessment Result", first["name"], "docstatus"), 1)
			amended = correct_assessment_result(first["name"], current, "School verified revised mark")
			self.assertEqual(frappe.db.get_value("Assessment Result", first["name"], "docstatus"), 2)
			self.assertEqual(frappe.db.get_value("Assessment Result", amended["name"], "amended_from"), first["name"])
			self.assertEqual(frappe.db.get_value("Assessment Result", amended["name"], "padars_corrected_by"), manager)
			correction_doc = frappe.get_doc("Assessment Result", amended["name"])
			correction_doc.padars_correction_reason = "Changed audit reason"
			with self.assertRaises(frappe.ValidationError):
				correction_doc.save(ignore_permissions=True)
			frappe.set_user(teacher)
			with self.assertRaises(frappe.PermissionError):
				mark_assessment_result(plan.name, {"student": student.name, "assessment_details": {criterion: 90}, "expected_modified": amended["modified"]})
			with self.assertRaises(frappe.PermissionError):
				correct_assessment_result(amended["name"], amended["modified"], "Teacher attempt")
			frappe.set_user(manager)
			mark_assessment_result(plan.name, {"student": student.name, "assessment_details": {criterion: 90}, "expected_modified": amended["modified"]})
			frappe.get_doc("Assessment Result", amended["name"]).submit()
			self.assertEqual(calculate_scheme(revised.name, student.name)["score"], "90.00")
			self.assertEqual(read_report_card(updated["name"])["snapshot"]["courses"][0]["score"], "80.00")
			with self.assertRaises(frappe.TimestampMismatchError):
				publish_report_card(enrollment, [revised.name], correction["digest"], "Stale review")
			frappe.set_user(student_user)
			from frappe.model import get_permitted_fields
			self.assertNotIn("correction_reason", get_permitted_fields("Report Card Publication"))
			self.assertEqual(len(list_report_cards()), 2)
			self.assertEqual(read_report_card(publication["name"])["snapshot"]["student"], student.name)
			with self.assertRaises(frappe.PermissionError):
				publish_report_card(enrollment, [scheme.name], card["digest"])
			frappe.set_user(outsider)
			with self.assertRaises(frappe.PermissionError):
				read_report_card(publication["name"])
			with self.assertRaises(frappe.PermissionError):
				report_card_pdf(publication["name"])
			# A native relationship alone grants no report access.
			from padars.guardian_access import verify_guardian_access, revoke_guardian_access, linked_students
			frappe.set_user("Administrator")
			parent_user = self._user("parent")
			frappe.get_doc("User", parent_user).add_roles("Guardian")
			guardian = frappe.get_doc({"doctype": "Guardian", "guardian_name": "Verified parent",
				"email_address": parent_user, "user": parent_user}).insert()
			student.reload()
			student.append("guardians", {"guardian": guardian.name, "relation": "Mother"})
			student.save()
			frappe.set_user(parent_user)
			self.assertEqual(linked_students(), [])
			with self.assertRaises(frappe.PermissionError):
				read_report_card(publication["name"])
			with self.assertRaises(frappe.PermissionError):
				verify_guardian_access(student.name, guardian.name, reason="Self verified")
			frappe.set_user(manager)
			with self.assertRaises(frappe.ValidationError):
				verify_guardian_access(student.name, guardian.name, reason="")
			grant = verify_guardian_access(student.name, guardian.name, reason="School checked guardian records")
			self.assertEqual(grant, verify_guardian_access(student.name, guardian.name, reason="Repeated request"))
			frappe.set_user(parent_user)
			self.assertEqual(linked_students(), [student.name])
			self.assertEqual(len(list_report_cards(student.name)), 2)
			self.assertEqual(read_report_card(publication["name"])["snapshot"]["student"], student.name)
			self.assertNotIn("correction_reason", get_permitted_fields("Report Card Publication"))
			self.assertFalse(frappe.has_permission("Assessment Result", "read", doc=frappe.get_doc("Assessment Result", amended["name"])))
			with self.assertRaises(frappe.PermissionError):
				list_report_cards("unrelated-student")
			frappe.set_user(manager)
			revoke_guardian_access(grant["name"], "School access review")
			frappe.set_user(parent_user)
			with self.assertRaises(frappe.PermissionError):
				report_card_pdf(publication["name"])
			frappe.set_user(manager)
			second_grant = verify_guardian_access(student.name, guardian.name, reason="Reverified")
			self.assertNotEqual(second_grant["name"], grant["name"])
			student.reload()
			student.set("guardians", [])
			student.save()
			self.assertEqual(frappe.db.get_value("Verified Guardian Access", second_grant["name"], "status"), "Revoked")
			frappe.set_user(parent_user)
			self.assertEqual(linked_students(), [])
			frappe.set_user(teacher)
			with self.assertRaises(frappe.PermissionError):
				calculate_scheme(scheme.name, student.name)
			with self.assertRaises(frappe.PermissionError):
				preview_approved_results(student.name, self.program.name, self.year.name)
			with self.assertRaises((frappe.ValidationError, frappe.PermissionError)):
				mark_assessment_result(plan.name, {"student": student.name, "assessment_details": {criterion: 90}})
		finally:
			frappe.set_user("Administrator")

	def test_guardian_verification_creates_only_scoped_website_account(self):
		from padars.guardian_access import verify_guardian_access, linked_students
		child_user = self._user("guardian-child")
		with patch("education.education.doctype.student.student.Student.on_update"):
			student = frappe.get_doc({"doctype": "Student", "first_name": "Child", "enabled": 1, "student_email_id": child_user, "user": child_user}).insert()
		email = f"family-{self.key.lower()}@example.invalid"
		guardian = frappe.get_doc({"doctype": "Guardian", "guardian_name": "Family",
			"email_address": email}).insert()
		student.append("guardians", {"guardian": guardian.name, "relation": "Father"})
		with patch("education.education.doctype.student.student.Student.on_update"):
			student.save()
		manager = self._user("family-manager")
		frappe.get_doc("User", manager).add_roles("Padars School Manager")
		frappe.set_user(manager)
		self.assertFalse(frappe.has_permission("User", "write", doc=frappe.get_doc("User", child_user)))
		grant = verify_guardian_access(student.name, guardian.name, reason="School verified relationship")
		account = frappe.get_doc("User", grant["user"])
		self.assertEqual(account.user_type, "Website User")
		self.assertEqual({row.role for row in account.roles}, {"Padars Guardian"})
		self.assertEqual(frappe.db.get_value("Guardian", guardian.name, "user"), email)
		frappe.set_user(email)
		self.assertEqual(linked_students(), [student.name])
		from padars.www.report_cards import get_context
		with patch.dict(frappe.form_dict, {}, clear=True):
			context = get_context(frappe._dict())
		self.assertEqual(context.linked_children[0]["student"], student.name)
		self.assertEqual(context.reports, [])
		frappe.set_user(manager)
		guardian.reload()
		guardian.email_address = f"changed-{email}"
		guardian.save()
		self.assertEqual(frappe.db.get_value("Verified Guardian Access", grant["name"], "status"), "Revoked")
		frappe.set_user(email)
		self.assertEqual(linked_students(), [])

	def test_academic_portal_projects_only_authorized_native_records(self):
		from padars.portal import get_academic_overview
		from padars.guardian_access import verify_guardian_access
		learner = self._user("portal-student")
		frappe.get_doc("User", learner).add_roles("Student")
		with patch("education.education.doctype.student.student.Student.on_update"):
			student = frappe.get_doc({"doctype": "Student", "first_name": "Portal learner",
				"enabled": 1, "student_email_id": learner, "user": learner}).insert()
		frappe.get_doc({"doctype": "Program Enrollment", "student": student.name,
			"program": self.program.name, "academic_year": self.year.name,
			"enrollment_date": "2020-01-01", "padars_school": self.school.name}).insert().submit()
		self.group.append("students", {"student": student.name, "active": 1})
		self.group.save()
		date = getdate(today()) - timedelta(days=getdate(today()).weekday())
		lesson = self._schedule(self.group, date, "11:00:00", "12:00:00", offering=self.offering.name)
		other = self._other_group()
		hidden = self._schedule(other, date, "13:00:00", "14:00:00")
		frappe.get_doc({"doctype": "Student Attendance", "student": student.name,
			"course_schedule": lesson.name, "student_group": self.group.name,
			"date": date, "status": "Present"}).insert().submit()
		frappe.set_user(learner)
		result = get_academic_overview(week=str(date))
		self.assertEqual([row.name for row in result["sessions"]], [lesson.name])
		self.assertNotIn(hidden.name, str(result))
		self.assertEqual(result["attendance"][0].status, "Present")
		self.assertEqual(result["courses"][0].course_name, self.course.course_name)
		self.assertIsNone(result["courses"][0].moodle_url)
		self.assertFalse(result["sso_verified"])
		self.assertNotIn("student_mobile_number", str(result))
		from pathlib import Path
		template = Path(frappe.get_app_path("padars", "www", "school.html")).read_text()
		body = template.split("{% block page_content %}", 1)[1].split("{% endblock %}", 1)[0]
		probe = frappe._dict(result.copy())
		probe.student_name = "<script>alert(1)</script>"
		html = frappe.render_template(body, {"overview": probe, "children": []})
		self.assertNotIn("<script>", html)
		self.assertIn("&lt;script&gt;", html)
		with self.assertRaises(frappe.PermissionError):
			get_academic_overview("unrelated-student", week=str(date))
		frappe.set_user("Administrator")
		parent = self._user("portal-parent")
		guardian = frappe.get_doc({"doctype": "Guardian", "guardian_name": "Portal family",
			"email_address": parent, "user": parent}).insert()
		student.reload()
		student.append("guardians", {"guardian": guardian.name, "relation": "Mother"})
		with patch("education.education.doctype.student.student.Student.on_update"):
			student.save()
		verify_guardian_access(student.name, guardian.name, reason="Verified for portal")
		frappe.set_user(parent)
		self.assertEqual(get_academic_overview(student.name, str(date))["sessions"][0].name, lesson.name)
		frappe.set_user("Administrator")
		self.group.reload()
		self.group.students[0].active = 0
		self.group.save()
		frappe.set_user(learner)
		withdrawn = get_academic_overview(week=str(date))
		self.assertEqual(withdrawn["sessions"], [])
		self.assertEqual(withdrawn["courses"], [])
		self.assertEqual(withdrawn["attendance"][0].status, "Present")
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			get_academic_overview(student.name, str(date))

	def test_portal_moodle_links_require_verified_tenant_and_observed_roster(self):
		from padars.portal import _course_links
		school = frappe._dict(lms_enabled=1, lms_status="Connected", lms_tenant_id=42)
		settings = frappe._dict(enabled=1, adapter="Moodle", base_url="https://lms.example.invalid")
		with patch("padars.portal.get_student_for_user", return_value="STUDENT"), \
			patch("padars.portal.frappe.get_doc", return_value=school), \
			patch("padars.portal.frappe.get_single", return_value=settings), \
			patch.dict(frappe.conf, {"padars_moodle_allowed_hosts": ["lms.example.invalid"]}), \
			patch("padars.portal.frappe.db.exists", return_value=True) as exists, \
			patch("padars.portal.frappe.get_all", side_effect=[["OFFERING"],
				[frappe._dict(local_name="OFFERING", remote_id="57", remote_url="javascript:bad")]]) as query:
			self.assertEqual(_course_links(self.school.name, "STUDENT", ["OFFERING"]),
				{"OFFERING": "https://lms.example.invalid/course/view.php?id=57"})
			self.assertEqual(exists.call_args.args[1]["remote_context"], "moodle:https://lms.example.invalid:tenant:42")
			self.assertEqual(query.call_args_list[0].kwargs["filters"]["remote_state"], "Enrolled")
			self.assertEqual(query.call_args_list[1].kwargs["filters"]["remote_context"], "moodle:https://lms.example.invalid:tenant:42")
		with patch("padars.portal.get_student_for_user", return_value="OTHER"):
			self.assertEqual(_course_links(self.school.name, "STUDENT", ["OFFERING"]), {})
		with patch("padars.portal.get_student_for_user", return_value="STUDENT"), \
			patch("padars.portal.frappe.get_doc", return_value=school), \
			patch("padars.portal.frappe.get_single", return_value=settings), \
			patch.dict(frappe.conf, {"padars_moodle_allowed_hosts": ["lms.example.invalid"]}), \
			patch("padars.portal.frappe.db.exists", return_value=False):
			self.assertEqual(_course_links(self.school.name, "STUDENT", ["OFFERING"]), {})

	def test_scheme_rejects_invalid_weights_and_allocates_versions(self):
		plan = self._assessment_plan(self.group, self._monday(), examiner=self.instructor.name)
		plan.submit()
		def make(weight):
			return frappe.get_doc({"doctype": "School Assessment Scheme", "scheme_title": "Versioned test",
				"course_offering": self.offering.name, "grading_scale": plan.grading_scale,
				"output_maximum": 100, "decimal_places": 2,
				"components": [{"assessment_plan": plan.name, "assessment_criteria": plan.assessment_criteria[0].assessment_criteria, "weight": weight}]})
		with self.assertRaises(frappe.ValidationError):
			make(50).insert()
		first = make(100).insert()
		first.submit()
		second = make(100).insert()
		self.assertEqual(second.version, first.version + 1)
		self.assertNotEqual(second.version_key, first.version_key)
		with self.assertRaises(frappe.ValidationError):
			first.cancel()

	def test_weighted_scheme_uses_normalized_approved_scores_and_requires_all_sources(self):
		from padars.assessment import mark_assessment_result
		from padars.grading import calculate_scheme
		user = self._user("weighted-student")
		with patch("education.education.doctype.student.student.Student.on_update"):
			student = frappe.get_doc({"doctype": "Student", "first_name": "Weighted",
				"student_email_id": user, "user": user, "enabled": 1}).insert()
		frappe.get_doc({"doctype": "Program Enrollment", "student": student.name, "program": self.program.name,
			"academic_year": self.year.name, "enrollment_date": "2020-01-01", "padars_school": self.school.name}).insert().submit()
		self.group.append("students", {"student": student.name, "active": 1})
		self.group.save()
		plan = self._assessment_plan(self.group, self._monday(), examiner=self.instructor.name)
		criterion = plan.assessment_criteria[0].assessment_criteria
		second = frappe.get_doc({"doctype": "Assessment Criteria", "assessment_criteria": f"Second-{self.key}"}).insert()
		plan.append("assessment_criteria", {"assessment_criteria": second.name, "maximum_score": 50})
		plan.maximum_assessment_score = 150
		plan.save()
		plan.submit()
		scheme = frappe.get_doc({"doctype": "School Assessment Scheme", "scheme_title": "Weighted scheme",
			"course_offering": self.offering.name, "grading_scale": plan.grading_scale,
			"output_maximum": 20, "decimal_places": 2, "rounding_mode": "Half Even",
			"components": [{"assessment_plan": plan.name, "assessment_criteria": criterion, "weight": 60},
				{"assessment_plan": plan.name, "assessment_criteria": second.name, "weight": 40}]}).insert()
		scheme.submit()
		with self.assertRaises(frappe.ValidationError):
			calculate_scheme(scheme.name, student.name)
		result = mark_assessment_result(plan.name, {"student": student.name, "assessment_details": {criterion: 80, second.name: 25}})
		with self.assertRaises(frappe.ValidationError):
			calculate_scheme(scheme.name, student.name)
		frappe.get_doc("Assessment Result", result["name"]).submit()
		calculated = calculate_scheme(scheme.name, student.name)
		self.assertEqual(calculated["score"], "13.60")
		self.assertEqual(calculated["percentage"], "68.00")
		self.assertEqual(calculated["rounding_mode"], "Half Even")

	def test_past_exam_plans_cannot_be_deleted_or_rescheduled(self):
		past_date = add_days(today(), -1)
		plan = self._assessment_plan(self.group, past_date, examiner=self.instructor.name)
		plan.schedule_date = add_days(past_date, -1)
		with self.assertRaises(frappe.ValidationError):
			plan.save()
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("Assessment Plan", plan.name)
		self.assertTrue(frappe.db.exists("Assessment Plan", plan.name))

	def test_rescheduling_is_atomic_and_preserves_past_sessions(self):
		date = self._monday()
		original = self._schedule(self.group, date, "11:00:00", "12:00:00", offering=self.offering.name)
		other_group = self._other_group()
		blocker = self._schedule(other_group, date, "09:00:00", "10:00:00")
		tool = frappe.get_doc({
			"doctype": "Course Scheduling Tool", "student_group": self.group.name,
			"course": self.course.name, "instructor": self.instructor.name,
			"room": self.room.name, "from_time": "09:00:00", "to_time": "10:00:00",
			"course_start_date": date, "course_end_date": add_days(date, 1), "reschedule": 1,
		})
		with self.assertRaises(frappe.ValidationError):
			tool.schedule_course([day_name[date.weekday()]])
		self.assertTrue(frappe.db.exists("Course Schedule", original.name))
		self.assertTrue(frappe.db.exists("Course Schedule", blocker.name))

		boundary_start = add_days(date, -1)
		boundary_tool = frappe.get_doc({
			"doctype": "Course Scheduling Tool", "student_group": self.group.name,
			"course": self.course.name, "instructor": self.instructor.name,
			"room": self.room.name, "from_time": "09:00:00", "to_time": "10:00:00",
			"course_start_date": boundary_start, "course_end_date": date, "reschedule": 1,
		})
		with self.assertRaises(frappe.ValidationError):
			boundary_tool.schedule_course([
				day_name[boundary_start.weekday()], day_name[date.weekday()],
			])
		self.assertTrue(frappe.db.exists("Course Schedule", original.name))

		past_date = add_days(today(), -1)
		past = self._schedule(self.group, past_date, "15:00:00", "16:00:00", offering=self.offering.name)
		past_tool = frappe.get_doc({
			"doctype": "Course Scheduling Tool", "student_group": self.group.name,
			"course": self.course.name, "instructor": self.instructor.name,
			"room": self.room.name, "from_time": "15:00:00", "to_time": "16:00:00",
			"course_start_date": past_date, "course_end_date": add_days(past_date, 1), "reschedule": 1,
		})
		with self.assertRaises(frappe.ValidationError):
			past_tool.schedule_course([day_name[getdate(past_date).weekday()]])
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("Course Schedule", past.name)
		self.assertTrue(frappe.db.exists("Course Schedule", past.name))

		future = self._schedule(self.group, date, "15:00:00", "16:00:00", offering=self.offering.name)
		with patch("padars.scheduling.frappe.db.exists", return_value="ATT-TEST"):
			with self.assertRaises(frappe.ValidationError):
				validate_course_schedule_deletion(future)

	def test_only_school_manager_can_run_weekly_scheduler(self):
		tool = frappe.get_doc({"doctype": "Course Scheduling Tool"})
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				tool.schedule_course(["Monday"])
		finally:
			frappe.set_user("Administrator")
