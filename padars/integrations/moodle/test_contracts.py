"""Offline contract tests for Moodle 5.2 and MuTMS web-service payloads."""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import frappe

from padars.integrations.moodle.live import LiveMoodleAdapter, _site_fingerprint
from padars.integrations.moodle.rest import (
	MoodleAPIError,
	MoodleRESTClient,
	_form_data,
	validate_moodle_base_url,
)


class FakeResponse:
	status_code = 200

	def __init__(self, body):
		self.body = body

	def json(self):
		return self.body


class FakeHTTPSession:
	def __init__(self, body=None, status=200):
		self.body = body or {"ok": True}
		self.status = status
		self.request = None

	def post(self, url, **kwargs):
		self.request = (url, kwargs)
		response = FakeResponse(self.body)
		response.status_code = self.status
		return response


class FakeMoodleClient:
	base_url = "https://moodle.example.test"

	def __init__(self):
		self.calls = []
		self.tenant = None
		self.users = {}
		self.courses = {}
		self.enrolled_courses = []

	def call(self, function, params=None):
		params = params or {}
		self.calls.append((function, params))
		if function == "tool_mutenancy_get_tenants":
			idnumber = params["fieldvalues"][0]["value"]
			return [self.tenant] if self.tenant and self.tenant["idnumber"] == idnumber else []
		if function == "tool_mutenancy_create_tenant":
			request = params["tenant"]
			self.tenant = {
				"id": 21,
				"name": request["name"],
				"idnumber": request["idnumber"],
				"siteshortname": request["siteshortname"],
				"categoryid": 42,
				"cohortid": 43,
				"assoccohortid": 44,
				"archived": False,
			}
			return self.tenant
		if function == "core_course_get_categories":
			return [{"id": 42}]
		if function == "core_cohort_get_cohorts":
			return [{"id": cohort_id} for cohort_id in params["cohortids"]]
		if function == "core_course_get_courses_by_field":
			field = params["field"]
			return {"courses": [course for course in self.courses.values() if str(course.get(field)) == str(params["value"])]}
		if function == "core_course_create_courses":
			request = params["courses"][0]
			course = {**request, "id": 88}
			self.courses[str(course["id"])] = course
			return [{"id": course["id"]}]
		if function == "core_course_update_courses":
			for update in params["courses"]:
				self.courses[str(update["id"])].update(update)
			return None
		if function == "core_user_get_users_by_field":
			field = params["field"]
			values = {str(value) for value in params["values"]}
			return [user for user in self.users.values() if str(user.get(field)) in values]
		if function == "core_user_create_users":
			request = params["users"][0]
			user = {**request, "id": 77, "tenantid": request["tenantid"]}
			self.users[str(user["idnumber"])] = user
			return [{"id": user["id"]}]
		if function == "enrol_manual_enrol_users":
			self.enrolled_courses = [{"id": params["enrolments"][0]["courseid"]}]
			return None
		if function == "enrol_manual_unenrol_users":
			self.enrolled_courses = []
			return None
		if function == "core_enrol_get_users_courses":
			return self.enrolled_courses
		raise AssertionError(f"Unexpected Moodle function: {function}")


class TestMoodleRESTContracts(TestCase):
	def test_nested_values_follow_moodle_rest_form_encoding(self):
		self.assertEqual(
			_form_data({"tenant": {"name": "North"}, "fieldvalues": [{"field": "idnumber", "value": "abc"}]}),
			{
				"tenant[name]": "North",
				"fieldvalues[0][field]": "idnumber",
				"fieldvalues[0][value]": "abc",
			},
		)

	def test_token_is_posted_without_redirects(self):
		session = FakeHTTPSession()
		result = MoodleRESTClient("https://moodle.example.test", "secret", session=session).call(
			"core_webservice_get_site_info", {"nested": ["x"]}
		)
		url, request = session.request
		self.assertEqual(result, {"ok": True})
		self.assertEqual(url, "https://moodle.example.test/webservice/rest/server.php")
		self.assertEqual(request["data"]["wstoken"], "secret")
		self.assertEqual(request["data"]["nested[0]"], "x")
		self.assertFalse(request["allow_redirects"])
		self.assertTrue(request["verify"])

	def test_remote_errors_do_not_expose_response_message(self):
		session = FakeHTTPSession({"exception": "moodle_exception", "errorcode": "invalidtoken", "message": "secret"})
		with self.assertRaises(MoodleAPIError) as caught:
			MoodleRESTClient("https://moodle.example.test", "secret", session=session).call("bad")
		self.assertIn("invalidtoken", str(caught.exception))
		self.assertNotIn("secret", str(caught.exception))

	def test_base_url_requires_exact_https_allowlist_host(self):
		self.assertEqual(
			validate_moodle_base_url("https://Moodle.example.test/moodle/", "moodle.example.test"),
			"https://moodle.example.test/moodle",
		)
		for value in (
			"http://moodle.example.test",
			"https://other.example.test",
			"https://moodle.example.test:444",
			"https://user@moodle.example.test",
			"https://moodle.example.test/?token=secret",
			"https://moodle.example.test/#fragment",
			"https://localhost",
		):
			with self.subTest(value=value), self.assertRaises(ValueError):
				validate_moodle_base_url(value, ["moodle.example.test"])


class TestLiveMoodleContracts(TestCase):
	def setUp(self):
		self.client = FakeMoodleClient()
		self.settings = SimpleNamespace(
			default_member_limit=500,
			teacher_role_id=3,
			student_role_id=5,
			school_manager_role_id=9,
		)
		self.adapter = LiveMoodleAdapter(self.client, self.settings)
		self.school = SimpleNamespace(
			name="SCH-01",
			school_name="North School",
			lms_enabled=1,
			lms_installation_uuid="0123456789abcdef0123456789abcdef",
			lms_origin_site=frappe.local.site,
			lms_provisioned=0,
			lms_tenant_id="",
			lms_tenant_idnumber="",
		)

	def test_grade_report_checks_tenant_course_and_user_before_returning_items(self):
		from unittest.mock import Mock
		identity = self.school.lms_installation_uuid
		self.school.lms_tenant_idnumber = "padars" + identity
		tenant = {"id": 7, "categoryid": 30, "idnumber": self.school.lms_tenant_idnumber,
			"siteshortname": _site_fingerprint(self.school, identity)}
		course = SimpleNamespace(remote_id="14", remote_context=self.adapter._tenant_context(7))
		user = SimpleNamespace(remote_id="9", remote_context=course.remote_context)
		item = {"id": 25, "graderaw": 16, "grademax": 20}
		with patch.object(self.adapter, "_local_tenant", return_value=tenant):
			self.client.call = Mock(side_effect=[{"courses": [{"id": 14, "categoryid": 30}]},
				[{"id": 9, "tenantid": 7}], {"usergrades": [{"courseid": 14, "userid": 9, "gradeitems": [item]}]}])
			self.assertEqual(self.adapter.read_grade_items(self.school, course, user), [item])
			self.client.call.assert_called_with("gradereport_user_get_grade_items", {"courseid": 14, "userid": 9})
			self.client.call = Mock(side_effect=[{"courses": [{"id": 14, "categoryid": 99}]}])
			with self.assertRaises(frappe.ValidationError):
				self.adapter.read_grade_items(self.school, course, user)
			self.assertEqual(self.client.call.call_count, 1)
			self.client.call = Mock(side_effect=[{"courses": [{"id": 14, "categoryid": 30}]},
				[{"id": 9, "tenantid": 99}]])
			with self.assertRaises(frappe.ValidationError):
				self.adapter.read_grade_items(self.school, course, user)
			self.client.call = Mock(side_effect=[{"courses": [{"id": 14, "categoryid": 30}]},
				[{"id": 9, "tenantid": 7}], {"usergrades": [{"courseid": 14, "userid": 999, "gradeitems": [item]}]}])
			with self.assertRaises(frappe.ValidationError):
				self.adapter.read_grade_items(self.school, course, user)

	def test_learning_calls_exclude_content_and_target_the_requested_user(self):
		from unittest.mock import Mock
		course = SimpleNamespace(remote_id="14")
		user = SimpleNamespace(remote_id="9")
		with patch.object(self.adapter, "_verified_read_scope", return_value=(14, 9)) as verify:
			self.client.call = Mock(return_value=[])
			self.assertEqual(self.adapter.read_course_activities(self.school, course), [])
			self.client.call.assert_called_with("core_course_get_contents", {"courseid": 14, "options": [{"name": "excludecontents", "value": "1"}]})
			self.client.call = Mock(return_value={"statuses": [{"cmid": 101, "state": 2}], "warnings": []})
			self.assertEqual(self.adapter.read_activity_completions(self.school, course, user), [{"cmid": 101, "state": 2}])
			verify.assert_called_with(self.school, course, user)
			self.client.call.assert_called_with("core_completion_get_activities_completion_status", {"courseid": 14, "userid": 9})
			self.client.call = Mock(return_value={"statuses": [], "warnings": [{"warningcode": "denied"}]})
			with self.assertRaises(frappe.ValidationError):
				self.adapter.read_activity_completions(self.school, course, user)

	def test_tenant_create_and_resource_verification_contract(self):
		result = self.adapter.ensure_tenant(self.school)
		create = next(params for function, params in self.client.calls if function == "tool_mutenancy_create_tenant")
		tenant = create["tenant"]
		self.assertEqual(tenant["idnumber"], "padars0123456789abcdef0123456789abcdef")
		self.assertEqual(tenant["siteshortname"], _site_fingerprint(self.school, self.school.lms_installation_uuid))
		self.assertEqual(tenant["memberlimit"], 500)
		self.assertEqual(tenant["assoccohortcreate"], 1)
		functions = [function for function, _ in self.client.calls]
		self.assertIn("core_course_get_categories", functions)
		self.assertIn("core_cohort_get_cohorts", functions)
		self.assertEqual(result["remote_id"], "21")
		self.assertEqual(result["category_id"], 42)
		self.assertEqual(result["cohort_id"], 43)
		self.assertEqual(result["associated_cohort_id"], 44)

	def test_tenant_retry_reuses_stable_remote_identity(self):
		first = self.adapter.ensure_tenant(self.school)
		self.school.lms_provisioned = 1
		self.school.lms_tenant_id = first["remote_id"]
		self.school.lms_tenant_idnumber = first["tenant_idnumber"]
		second = self.adapter.ensure_tenant(self.school)
		self.assertEqual(first["remote_id"], second["remote_id"])
		self.assertEqual(
			sum(function == "tool_mutenancy_create_tenant" for function, _ in self.client.calls),
			1,
		)

	def test_cloned_site_is_rejected_before_remote_calls(self):
		self.school.lms_origin_site = "a-different-site.example.test"
		with self.assertRaises(Exception):
			self.adapter.ensure_tenant(self.school)
		self.assertEqual(self.client.calls, [])

	def test_member_is_created_with_tenant_allocation_and_stable_id(self):
		tenant = {
			"id": 21,
			"categoryid": 42,
			"cohortid": 43,
		}
		user = SimpleNamespace(name="student@example.test", email="student@example.test", first_name="Ada", last_name="Lovelace")
		result = self.adapter.ensure_user(user, self.school, tenant=tenant)
		request = next(params["users"][0] for function, params in self.client.calls if function == "core_user_create_users")
		self.assertEqual(request["tenantid"], 21)
		self.assertEqual(request["createpassword"], 1)
		self.assertEqual(request["auth"], "manual")
		self.assertEqual(result["remote_id"], "77")
		self.assertIn("idnumber", request)

	def test_unowned_remote_user_is_not_reused(self):
		import hashlib

		identity = self.school.lms_installation_uuid
		local_key = hashlib.sha256(f"{self.school.name}\0student@example.test".encode()).hexdigest()[:20]
		idnumber = f"padarsu{identity}{local_key}"
		self.client.users[idnumber] = {
			"id": 77,
			"idnumber": idnumber,
			"username": "somebody-else",
			"tenantid": 21,
		}
		user = SimpleNamespace(name="student@example.test", email="student@example.test", first_name="Ada", last_name="Lovelace")
		with self.assertRaises(Exception):
			self.adapter.ensure_user(user, self.school, tenant={"id": 21})
		self.assertEqual(self.client.calls[0][0], "core_user_get_users_by_field")
		self.assertEqual(len(self.client.calls), 1)

	def test_course_is_created_in_verified_tenant_category_and_reused(self):
		self.client.tenant = {
			"id": 21,
			"name": "North School",
			"idnumber": "padars0123456789abcdef0123456789abcdef",
			"siteshortname": _site_fingerprint(self.school, self.school.lms_installation_uuid),
			"categoryid": 42,
			"cohortid": 43,
			"assoccohortid": 44,
			"archived": False,
		}
		school = SimpleNamespace(**{
			**vars(self.school),
			"lms_status": "Connected",
			"lms_tenant_id": "21",
			"lms_tenant_idnumber": self.client.tenant["idnumber"],
			"lms_course_category_id": "42",
		})
		offering = SimpleNamespace(name="OFFER-1", school=school.name, course="BIO", student_group="GROUP-1")
		with (
			patch("padars.integrations.moodle.live.frappe.get_doc", return_value=school),
			patch(
				"padars.integrations.moodle.live.frappe.db.get_value",
				side_effect=["Biology", "Grade 10A", "Biology", "Grade 10A"],
			),
		):
			first = self.adapter.create_course(offering)
			second = self.adapter.create_course(offering)
		create = next(params["courses"][0] for function, params in self.client.calls if function == "core_course_create_courses")
		self.assertEqual(create["categoryid"], 42)
		self.assertTrue(create["idnumber"].startswith("padarsc0123456789abcdef0123456789abcdef"))
		self.assertEqual(first, second)
		self.assertEqual(sum(function == "core_course_create_courses" for function, _ in self.client.calls), 1)

	def test_enrollment_uses_configured_role_and_verifies_state(self):
		state = SimpleNamespace(role="Teacher", desired_state="Enrolled")
		user = {"remote_id": "77"}
		course = {"remote_id": "88", "remote_context": "tenant:21", "remote_url": "https://moodle.example.test/course/view.php?id=88"}
		result = self.adapter.sync_enrollment(state, user, course)
		function, params = next(call for call in self.client.calls if call[0] == "enrol_manual_enrol_users")
		self.assertEqual(function, "enrol_manual_enrol_users")
		self.assertEqual(params["enrolments"], [{"roleid": 3, "userid": 77, "courseid": 88}])
		self.assertEqual(result["remote_state"], "Enrolled")
		self.assertIn("core_enrol_get_users_courses", [function for function, _ in self.client.calls])

	def test_unenrollment_uses_moodle_user_and_course_contract(self):
		state = SimpleNamespace(role="Student", desired_state="Not Enrolled")
		course = {"remote_id": "88", "remote_context": "tenant:21", "remote_url": ""}
		result = self.adapter.sync_enrollment(state, {"remote_id": "77"}, course)
		_, params = next(call for call in self.client.calls if call[0] == "enrol_manual_unenrol_users")
		self.assertEqual(params["enrolments"], [{"userid": 77, "courseid": 88}])
		self.assertEqual(result["remote_state"], "Not Enrolled")

	def test_missing_role_id_fails_closed_before_remote_write(self):
		self.settings.student_role_id = 0
		state = SimpleNamespace(role="Student", desired_state="Enrolled")
		with self.assertRaises(Exception):
			self.adapter.sync_enrollment(state, {"remote_id": "77"}, {"remote_id": "88", "remote_context": "x"})
		self.assertFalse(any(function == "enrol_manual_enrol_users" for function, _ in self.client.calls))
