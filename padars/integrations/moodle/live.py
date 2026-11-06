"""Moodle 5.2 and MuTMS REST adapter.

All calls here use the public functions declared by the installed Moodle and
MuTMS source. Role IDs are supplied by the trusted, server-side LMS Settings.
"""

import hashlib
import re

import frappe
from frappe import _

from padars.integrations.moodle.rest import MoodleAPIError


class LiveMoodleAdapter:
	name = "Moodle REST / MuTMS"

	def __init__(self, client, settings):
		self.client = client
		self.settings = settings
		self.base_url = client.base_url.rstrip("/")

	def health_check(self):
		return self.client.call("core_webservice_get_site_info")

	def ensure_tenant(self, school):
		if not school.lms_enabled:
			frappe.throw(_("Moodle is disabled for this School."))
		if not school.lms_installation_uuid or not school.lms_origin_site:
			frappe.throw(_("The School LMS installation identity is missing."))
		if school.lms_origin_site != frappe.local.site:
			frappe.throw(_("This site's identity differs from the original installation. Company support must re-identify this clone."))

		identity = re.sub(r"[^a-f0-9]", "", school.lms_installation_uuid.lower())
		if len(identity) != 32:
			frappe.throw(_("The School LMS installation identity is invalid."))
		external_id = f"padars{identity}"
		fingerprint = _site_fingerprint(school, identity)
		tenant = self._find_tenant(external_id)
		if tenant:
			self._validate_tenant_binding(school, tenant, external_id, fingerprint)
		else:
			if school.lms_provisioned:
				frappe.throw(_("The previously mapped Moodle tenant is missing. Automatic replacement is disabled."))
			params = {
				"tenant": {
					"name": _tenant_name(school, identity),
					"idnumber": external_id,
					"loginshow": 1,
					"memberlimit": int(self.settings.default_member_limit or 0),
					"sitefullname": school.school_name,
					"siteshortname": fingerprint,
					"categoryname": f"{school.school_name} Courses",
					"categoryidnumber": f"padarscat{identity}",
					"cohortname": f"{school.school_name} Members",
					"cohortidnumber": f"padarscohort{identity}",
					"assoccohortcreate": 1,
				},
			}
			try:
				self.client.call("tool_mutenancy_create_tenant", params)
			except MoodleAPIError:
				# Create may commit remotely before a timeout or duplicate-ID race.
				# The MuTMS unique idnumber is the reconciliation key.
				tenant = self._find_tenant(external_id)
				if not tenant:
					raise
			tenant = tenant or self._find_tenant(external_id)
			if not tenant:
				frappe.throw(_("MuTMS did not return the newly created tenant."))
			self._validate_tenant_binding(school, tenant, external_id, fingerprint)

		self._verify_tenant_resources(tenant)
		return {
			"remote_type": "Moodle Tenant",
			"remote_id": str(tenant["id"]),
			"remote_context": self._tenant_context(tenant["id"]),
			"remote_url": f"{self.base_url}/login/index.php",
			"tenant_name": tenant["name"],
			"tenant_idnumber": tenant["idnumber"],
			"category_id": int(tenant["categoryid"]),
			"cohort_id": int(tenant["cohortid"]),
			"associated_cohort_id": int(tenant.get("assoccohortid") or 0),
		}

	def _validate_tenant_binding(self, school, tenant, external_id, fingerprint):
		if tenant.get("archived"):
			frappe.throw(_("The mapped Moodle tenant is archived. Company support must repair the connection."))
		if tenant.get("idnumber") != external_id or tenant.get("siteshortname") != fingerprint:
			frappe.throw(_("A Moodle tenant uses this identity but its site fingerprint differs. Company support must re-identify this clone."))
		if school.lms_provisioned and school.lms_tenant_id and int(school.lms_tenant_id) != int(tenant["id"]):
			frappe.throw(_("The Moodle tenant identity changed. Automatic replacement is disabled."))
		if school.lms_tenant_idnumber and school.lms_tenant_idnumber != external_id:
			frappe.throw(_("The saved Moodle tenant ID number changed. Automatic replacement is disabled."))

	def _verify_tenant_resources(self, tenant):
		for key in ("id", "categoryid", "cohortid"):
			if int(tenant.get(key) or 0) <= 0:
				frappe.throw(_("MuTMS tenant verification did not return a valid {0}.").format(key))
		category = int(tenant["categoryid"])
		categories = self.client.call("core_course_get_categories", {
			"criteria": [{"key": "id", "value": str(category)}],
			"addsubcategories": 0,
		}) or []
		if not any(int(row.get("id") or 0) == category for row in categories):
			frappe.throw(_("MuTMS returned a course category that Moodle could not verify."))
		cohort_ids = [int(tenant["cohortid"])]
		if int(tenant.get("assoccohortid") or 0) > 0:
			cohort_ids.append(int(tenant["assoccohortid"]))
		cohorts = self.client.call("core_cohort_get_cohorts", {"cohortids": cohort_ids}) or []
		found = {int(row.get("id") or 0) for row in cohorts}
		if not set(cohort_ids).issubset(found):
			frappe.throw(_("MuTMS returned a cohort that Moodle could not verify."))

	def _find_tenant(self, idnumber):
		rows = self.client.call("tool_mutenancy_get_tenants", {
			"fieldvalues": [{"field": "idnumber", "value": idnumber}],
		}) or []
		if len(rows) > 1:
			frappe.throw(_("MuTMS returned multiple tenants for one unique installation identity."))
		return rows[0] if rows else None

	def _tenant_context(self, tenant_id):
		return f"moodle:{self.base_url}:tenant:{int(tenant_id)}"

	def _local_tenant(self, school):
		if not school.lms_enabled or school.lms_status != "Connected" or not school.lms_tenant_id:
			frappe.throw(_("The School Moodle tenant is not connected."))
		tenant = self._find_tenant(school.lms_tenant_idnumber)
		if (
			not tenant
			or tenant.get("archived")
			or int(tenant["id"]) != int(school.lms_tenant_id)
			or int(tenant["categoryid"]) != int(school.lms_course_category_id)
		):
			frappe.throw(_("The School Moodle tenant cannot be verified. Automatic replacement is disabled."))
		return tenant

	def ensure_user(self, user, school, tenant=None):
		tenant = tenant or self._local_tenant(school)
		if not (user.email or "").strip():
			frappe.throw(_("A valid email address is required before creating a Moodle member account."))
		identity = _installation_identity(school)
		local_key = hashlib.sha256(f"{school.name}\0{user.name}".encode()).hexdigest()[:20]
		idnumber = f"padarsu{identity}{local_key}"
		username = f"p{identity[:8]}_{local_key[:12]}"
		remote_rows = self.client.call("core_user_get_users_by_field", {
			"field": "idnumber", "values": [idnumber],
		}) or []
		if len(remote_rows) > 1:
			frappe.throw(_("Moodle returned duplicate user identities for this School."))
		remote_user = remote_rows[0] if remote_rows else None
		if remote_user:
			if remote_user.get("username") != username:
				frappe.throw(_("The matching Moodle account is not Padars-owned; automatic changes are disabled."))
			remote_tenant_id = int(remote_user.get("tenantid") or 0)
			if remote_tenant_id and remote_tenant_id != int(tenant["id"]):
				frappe.throw(_("The Moodle user belongs to another tenant; automatic reassignment is disabled."))
			if not remote_tenant_id:
				self.client.call("tool_mutenancy_allocate_user", {
					"userid": int(remote_user["id"]), "tenantid": int(tenant["id"]),
				})
				remote_user = self._get_user(idnumber)
				if not remote_user or int(remote_user.get("tenantid") or 0) != int(tenant["id"]):
					frappe.throw(_("Moodle did not verify the user's tenant allocation."))
			self._update_user(remote_user, user)
		else:
			params = {"users": [{
				"username": username,
				"idnumber": idnumber,
				"auth": "manual",
				"createpassword": 1,
				"firstname": (user.first_name or "Learner")[:100],
				"lastname": (user.last_name or "")[:100] or "User",
				"email": user.email,
				"tenantid": int(tenant["id"]),
			}]}
			try:
				created = self.client.call("core_user_create_users", params)
			except MoodleAPIError:
				remote_user = self._get_user(idnumber)
				if not remote_user:
					raise
				created = [remote_user]
			remote_id = int(created[0]["id"])
			remote_user = self._get_user(str(remote_id), field="id")
			if not remote_user or int(remote_user.get("tenantid") or 0) != int(tenant["id"]):
				frappe.throw(_("Moodle did not verify the created tenant member."))
		return {
			"remote_type": "Moodle User",
			"remote_id": str(remote_user["id"]),
			"remote_context": self._tenant_context(tenant["id"]),
			"remote_url": f"{self.base_url}/user/profile.php?id={int(remote_user['id'])}",
			"username": remote_user["username"],
		}

	def _get_user(self, value, field="idnumber"):
		rows = self.client.call("core_user_get_users_by_field", {"field": field, "values": [value]}) or []
		return rows[0] if len(rows) == 1 else None

	def _update_user(self, remote_user, user):
		values = {
			"id": int(remote_user["id"]),
			"firstname": (user.first_name or "Learner")[:100],
			"lastname": (user.last_name or "")[:100] or "User",
			"email": user.email,
		}
		if any(remote_user.get(key) != values[key] for key in ("firstname", "lastname", "email")):
			self.client.call("core_user_update_users", {"users": [values]})

	def create_course(self, offering):
		school = frappe.get_doc("School", offering.school)
		tenant = self._local_tenant(school)
		if int(tenant["categoryid"]) != int(school.lms_course_category_id):
			frappe.throw(_("The verified MuTMS course category differs from the saved tenant binding."))
		identity = _installation_identity(school)
		key = hashlib.sha256(offering.name.encode()).hexdigest()[:20]
		idnumber = f"padarsc{identity}{key}"
		shortname = f"p{identity[:8]}_{key[:14]}"
		course_name = frappe.db.get_value("Course", offering.course, "course_name") or offering.course
		group_name = frappe.db.get_value("Student Group", offering.student_group, "student_group_name") or offering.student_group
		fullname = f"{course_name} — {group_name}"[:254]
		rows = self.client.call("core_course_get_courses_by_field", {"field": "idnumber", "value": idnumber})
		courses = (rows or {}).get("courses", [])
		if len(courses) > 1:
			frappe.throw(_("Moodle returned duplicate courses for one Padars offering."))
		if courses:
			course = courses[0]
			if int(course["categoryid"]) != int(tenant["categoryid"]):
				frappe.throw(_("The mapped Moodle course belongs to another tenant category."))
			if course.get("fullname") != fullname:
				self.client.call("core_course_update_courses", {"courses": [{
					"id": int(course["id"]), "fullname": fullname,
				}]})
				verified = self.client.call("core_course_get_courses_by_field", {
					"field": "id", "value": str(course["id"]),
				})
				courses = (verified or {}).get("courses", [])
				course = courses[0] if len(courses) == 1 else None
				if not course or course.get("fullname") != fullname:
					frappe.throw(_("Moodle did not verify the updated course name."))
		else:
			try:
				created = self.client.call("core_course_create_courses", {"courses": [{
					"fullname": fullname,
					"shortname": shortname,
					"categoryid": int(tenant["categoryid"]),
					"idnumber": idnumber,
					"visible": 1,
				}]})
			except MoodleAPIError:
				rows = self.client.call("core_course_get_courses_by_field", {
					"field": "idnumber", "value": idnumber,
				})
				courses = (rows or {}).get("courses", [])
				if not courses:
					raise
				created = courses
			course_id = int(created[0]["id"])
			verified = self.client.call("core_course_get_courses_by_field", {
				"field": "id", "value": str(course_id),
			})
			courses = (verified or {}).get("courses", [])
			course = courses[0] if len(courses) == 1 else None
			if not course or int(course["categoryid"]) != int(tenant["categoryid"]):
				frappe.throw(_("Moodle did not verify the course in the School tenant category."))
		return {
			"remote_type": "Moodle Course",
			"remote_id": str(course["id"]),
			"remote_context": self._tenant_context(tenant["id"]),
			"remote_url": f"{self.base_url}/course/view.php?id={int(course['id'])}",
		}

	def sync_enrollment(self, enrollment_state, remote_user, remote_course):
		user_id = int(remote_user["remote_id"])
		course_id = int(remote_course["remote_id"])
		role_field = {
			"Teacher": "teacher_role_id",
			"Student": "student_role_id",
			"School Manager": "school_manager_role_id",
		}[enrollment_state.role]
		role_id = int(getattr(self.settings, role_field, 0) or 0)
		if role_id <= 0:
			frappe.throw(_("Company support must configure the Moodle {0} role ID from this server.").format(enrollment_state.role))
		if enrollment_state.desired_state == "Enrolled":
			self.client.call("enrol_manual_enrol_users", {"enrolments": [{
				"roleid": role_id, "userid": user_id, "courseid": course_id,
			}]})
		else:
			self.client.call("enrol_manual_unenrol_users", {"enrolments": [{
				"userid": user_id, "courseid": course_id, "roleid": role_id,
			}]})
		courses = self.client.call("core_enrol_get_users_courses", {
			"userid": user_id, "returnusercount": 0,
		}) or []
		is_enrolled = any(int(course.get("id") or 0) == course_id for course in courses)
		should_be_enrolled = enrollment_state.desired_state == "Enrolled"
		if is_enrolled != should_be_enrolled:
			frappe.throw(_("Moodle did not verify the requested course enrollment state."))
		return {
			"remote_type": "Moodle Enrollment",
			"remote_id": f"{course_id}:{user_id}:{role_id or 'none'}",
			"remote_context": remote_course["remote_context"],
			"remote_url": remote_course.get("remote_url"),
			"remote_state": enrollment_state.desired_state,
		}


def _installation_identity(school):
	identity = re.sub(r"[^a-f0-9]", "", (school.lms_installation_uuid or "").lower())
	if len(identity) != 32:
		frappe.throw(_("The School LMS installation identity is invalid."))
	return identity


def _tenant_name(school, identity):
	return f"{school.school_name} ({identity[:8]})"[:100]


def _site_fingerprint(school, identity):
	host = hashlib.sha256(str(school.lms_origin_site).lower().encode()).hexdigest()[:8]
	return f"pd{identity[:8]}{host}"
