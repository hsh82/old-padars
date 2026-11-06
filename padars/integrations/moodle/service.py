import hashlib
import json

import frappe
from frappe import _
from frappe.utils import add_to_date, now_datetime

from padars.integrations.moodle.mock import MockMoodleAdapter
from padars.integrations.moodle.rest import MoodleRESTClient, validate_moodle_base_url
from padars.padars.doctype.lms_sync_operation.lms_sync_operation import MAX_SYNC_ATTEMPTS
from padars.permissions import can_manage_moodle, is_lms_operator


def get_adapter():
	if not frappe.db.exists("LMS Settings", "LMS Settings"):
		frappe.throw(_("Company Moodle connection settings are not configured."))
	settings = frappe.get_single("LMS Settings")
	if not settings.enabled:
		frappe.throw(_("The company Moodle integration is disabled."))
	if settings.adapter == "Mock":
		return MockMoodleAdapter()
	if settings.adapter != "Moodle":
		frappe.throw(_("The configured Moodle adapter is unsupported."))
	try:
		base_url = validate_moodle_base_url(
			settings.base_url, frappe.conf.get("padars_moodle_allowed_hosts")
		)
	except (TypeError, ValueError) as exc:
		frappe.throw(_("Invalid Moodle connection URL: {0}").format(str(exc)))
	token = settings.get_password("api_token", raise_exception=False)
	if not token:
		frappe.throw(_("The Moodle API token is not configured."))
	from padars.integrations.moodle.live import LiveMoodleAdapter

	return LiveMoodleAdapter(
		MoodleRESTClient(base_url, token, timeout=settings.connection_timeout), settings
	)


def request_course_offering_sync(offering):
	if isinstance(offering, str):
		offering = frappe.get_doc("School Course Offering", offering)
	if offering.status == "Archived":
		frappe.throw(_("Archived Course Offerings cannot be synchronized."))
	course_name = frappe.db.get_value("Course", offering.course, "course_name") or offering.course
	fingerprint = hashlib.sha256(
		f"{course_name}\0{offering.student_group}\0{offering.instructor}".encode()
	).hexdigest()[:16]
	return request_sync_operation(
		offering.school,
		"Provision Course",
		"School Course Offering",
		offering.name,
		f"course:{hashlib.sha256((offering.name + fingerprint).encode()).hexdigest()[:32]}",
	)


def request_school_tenant_sync(school):
	if isinstance(school, str):
		school = frappe.get_doc("School", school)
	if not is_lms_operator():
		frappe.throw(_("Only company Moodle operators can request tenant provisioning."), frappe.PermissionError)
	if not school.lms_enabled:
		frappe.throw(_("Enable Moodle for this School before provisioning its tenant."))
	return request_sync_operation(
		school.name,
		"Provision Tenant",
		"School",
		school.name,
		f"tenant:{school.name}:{int(school.lms_provisioning_generation or 1)}",
	)


def request_user_sync(user, school):
	if isinstance(school, str):
		school = frappe.get_doc("School", school)
	user_name = user.name if hasattr(user, "name") else user
	key = hashlib.sha256(f"{school.name}\0{user_name}".encode()).hexdigest()[:32]
	return request_sync_operation(
		school.name,
		"Provision User",
		"User",
		user_name,
		f"user:{key}",
	)


def request_enrollment_sync(enrollment_state):
	if isinstance(enrollment_state, str):
		enrollment_state = frappe.get_doc("LMS Enrollment State", enrollment_state)
	key = hashlib.sha256(
		f"{enrollment_state.name}\0{enrollment_state.desired_state}\0{enrollment_state.desired_revision or 1}".encode()
	).hexdigest()[:32]
	return request_sync_operation(
		enrollment_state.school,
		"Sync Enrollment",
		"LMS Enrollment State",
		enrollment_state.name,
		f"enrollment:{key}",
	)


def request_student_enrollments(course_offering, students):
	if isinstance(course_offering, str):
		course_offering = frappe.get_doc("School Course Offering", course_offering)
	if isinstance(students, str):
		students = frappe.parse_json(students)
	if not isinstance(students, (list, tuple)) or not students:
		frappe.throw(_("Select at least one student to enroll."))
	if len(set(students)) != len(students):
		frappe.throw(_("A student can be selected only once."))
	allowed = set(get_offering_students(course_offering.name))
	invalid = sorted(set(students) - allowed)
	if invalid:
		frappe.throw(_("Every selected student must be activated, have a submitted Program Enrollment, and belong to this offering's active group."))
	return [
		request_enrollment_sync(
			ensure_enrollment_state(course_offering, frappe.db.get_value("Student", student, "user"), "Student")
		)
		for student in students
	]


def get_offering_students(course_offering):
	if isinstance(course_offering, str):
		course_offering = frappe.get_doc("School Course Offering", course_offering)
	if not can_manage_moodle(course_offering.school):
		frappe.throw(_("You are not authorized to manage Moodle enrollments for this School."), frappe.PermissionError)
	return _get_offering_students(course_offering)


def _get_offering_students(course_offering):
	offering = course_offering
	if not offering.student_group:
		return []
	rows = frappe.get_all(
		"Student Group Student",
		filters={"parent": offering.student_group, "active": 1},
		fields=["student"],
		ignore_permissions=True,
	)
	students = []
	for row in rows:
		student = row.student
		user = frappe.db.get_value("Student", {"name": student, "enabled": 1}, "user")
		if not user or not frappe.db.exists("User", {"name": user, "enabled": 1, "user_type": "System User"}):
			continue
		if not frappe.db.exists(
			"Program Enrollment",
			{
				"student": student,
				"program": offering.program,
				"academic_year": offering.academic_year,
				"docstatus": 1,
			},
		):
			continue
		students.append(student)
	return sorted(set(students))


def ensure_enrollment_state(offering, user, role):
	if isinstance(offering, str):
		offering = frappe.get_doc("School Course Offering", offering)
	key = hashlib.sha256(f"{offering.school}\0{user}\0{offering.name}\0{role}".encode()).hexdigest()
	existing = frappe.db.get_value("LMS Enrollment State", {"enrollment_key": key}, "name")
	if existing:
		state = frappe.get_doc("LMS Enrollment State", existing)
		if state.desired_state != "Enrolled":
			state.desired_state = "Enrolled"
			state.save(ignore_permissions=True)
		return state
	try:
		return frappe.get_doc({
			"doctype": "LMS Enrollment State",
			"school": offering.school,
			"user": user,
			"course_offering": offering.name,
			"role": role,
			"desired_state": "Enrolled",
		}).insert(ignore_permissions=True)
	except frappe.exceptions.DuplicateEntryError:
		return frappe.get_doc("LMS Enrollment State", frappe.db.get_value("LMS Enrollment State", {"enrollment_key": key}, "name"))


def request_sync_operation(school, operation_type, target_doctype, target_name, idempotency_key):
	"""Persist one idempotent integration request and enqueue it after commit."""
	from padars.integrations.moodle.grades import _can_read_offering
	learning_read = bool(operation_type == "Read Learning" and target_doctype == "School Course Offering"
		and frappe.db.get_value("School Course Offering", target_name, "school") == school and _can_read_offering(target_name))
	auto_sync = bool(
		frappe.flags.get("padars_lms_auto_sync")
		and frappe.db.get_value("School", school, "lms_auto_enrollment")
	)
	withdrawal = bool(
		frappe.flags.get("padars_lms_roster_withdrawal")
		and operation_type == "Sync Enrollment" and target_doctype == "LMS Enrollment State"
		and frappe.db.exists("LMS Enrollment State", {
			"name": target_name, "school": school, "role": "Student", "desired_state": "Not Enrolled",
		})
	)
	if operation_type == "Provision Tenant":
		if not is_lms_operator():
			frappe.throw(_("Only company Moodle operators can provision tenants."), frappe.PermissionError)
	elif not learning_read and not auto_sync and not withdrawal and not can_manage_moodle(school):
		frappe.throw(_("You are not authorized to request this Moodle operation."), frappe.PermissionError)
	if not frappe.db.get_value("School", school, "lms_enabled"):
		frappe.throw(_("Moodle is disabled for this School."))
	if frappe.db.get_value("School", school, "status") != "Active":
		frappe.throw(_("Moodle operations require an active School."))
	existing = frappe.db.exists("LMS Sync Operation", {"idempotency_key": idempotency_key})
	if existing:
		return frappe.get_doc("LMS Sync Operation", existing)

	try:
		operation = frappe.get_doc({
			"doctype": "LMS Sync Operation",
			"school": school,
			"operation_type": operation_type,
			"target_doctype": target_doctype,
			"target_name": target_name,
			"idempotency_key": idempotency_key,
			"state": "Queued",
		}).insert(ignore_permissions=True)
	except frappe.exceptions.DuplicateEntryError:
		return frappe.get_doc(
			"LMS Sync Operation", frappe.db.get_value("LMS Sync Operation", {"idempotency_key": idempotency_key})
		)
	frappe.enqueue(
		"padars.integrations.moodle.service.process_sync_operation",
		operation=operation.name,
		queue="long" if operation_type in {"Read Grades", "Read Learning"} else "short",
			job_id=idempotency_key,
		enqueue_after_commit=True,
	)
	return operation


def process_sync_operation(operation, adapter=None):
	frappe.db.sql("select name from `tabLMS Sync Operation` where name=%s for update", operation)
	operation = frappe.get_doc("LMS Sync Operation", operation)
	if operation.state in {"Succeeded", "Running"}:
		return operation
	if operation.state not in {"Pending", "Queued", "Failed"}:
		frappe.throw(_("Sync operation {0} is not ready to process.").format(operation.name))
	if (operation.attempt_count or 0) >= MAX_SYNC_ATTEMPTS:
		frappe.throw(_("Sync operation {0} has exhausted its retry limit.").format(operation.name))
	if not frappe.db.get_value("School", operation.school, "lms_enabled"):
		return _fail_operation(operation, _("Moodle is disabled for this School."))
	if frappe.db.get_value("School", operation.school, "status") != "Active":
		return _fail_operation(operation, _("Moodle operations require an active School."))

	operation.state = "Running"
	operation.attempt_count = (operation.attempt_count or 0) + 1
	operation.last_attempt_at = now_datetime()
	operation.save(ignore_permissions=True)
	try:
		adapter = adapter or get_adapter()
		remote, mappings = process_remote_operation(operation, adapter)
		if operation.operation_type == "Provision Course":
			queue_offering_staff_enrollments(operation.target_name)
			school = frappe.get_doc("School", operation.school)
			if school.lms_auto_enrollment:
				queue_offering_student_enrollments(operation.target_name)
		elif operation.operation_type == "Provision Tenant":
			school = frappe.get_doc("School", operation.school)
			queue_school_staff_reconciliation(school.name)
			if school.lms_auto_enrollment:
				queue_school_auto_enrollment(school.name)
			else:
				queue_school_roster_withdrawals(school.name)
		operation.state = "Succeeded"
		operation.last_error = None
		operation.next_retry_at = None
		operation.diagnostics = json.dumps({
			"adapter": getattr(adapter, "name", adapter.__class__.__name__),
			"mappings": [mapping.name for mapping in mappings],
		}, sort_keys=True)
		operation.save(ignore_permissions=True)
		return operation
	except Exception as exc:
		if operation.operation_type == "Provision Tenant":
			_set_school_lms_error(operation.school, _safe_error(exc))
		return _fail_operation(operation, _safe_error(exc))


def process_remote_operation(operation, adapter):
	if operation.operation_type == "Read Learning":
		from padars.integrations.moodle.learning import capture_learning
		return capture_learning(operation, adapter), []

	if operation.operation_type == "Read Grades":
		from padars.integrations.moodle.grades import capture_grades
		return capture_grades(operation, adapter), []

	if operation.operation_type == "Provision Tenant":
		school = frappe.get_doc("School", operation.target_name)
		remote = adapter.ensure_tenant(school)
		mapping = upsert_entity_mapping("School", school.name, school.name, remote)
		_save_tenant_binding(school, remote)
		return remote, [mapping]

	if operation.operation_type == "Provision User":
		user = frappe.get_doc("User", operation.target_name)
		school = frappe.get_doc("School", operation.school)
		tenant = adapter.ensure_tenant(school)
		_save_tenant_binding(school, tenant)
		remote = adapter.ensure_user(user, school, tenant=tenant)
		return remote, [
			upsert_entity_mapping("School", school.name, school.name, tenant),
			upsert_entity_mapping("User", user.name, school.name, remote),
		]

	if operation.operation_type == "Provision Course":
		offering = frappe.get_doc("School Course Offering", operation.target_name)
		school = frappe.get_doc("School", offering.school)
		tenant = adapter.ensure_tenant(school)
		tenant_mapping = upsert_entity_mapping("School", school.name, school.name, tenant)
		_save_tenant_binding(school, tenant)
		remote = adapter.create_course(offering)
		course_mapping = upsert_entity_mapping(
			"School Course Offering", offering.name, offering.school, remote
		)
		return remote, [tenant_mapping, course_mapping]

	if operation.operation_type == "Sync Enrollment":
		state = frappe.get_doc("LMS Enrollment State", operation.target_name)
		offering = frappe.get_doc("School Course Offering", state.course_offering)
		school = frappe.get_doc("School", state.school)
		if state.desired_state == "Not Enrolled":
			other_states = frappe.get_all("LMS Enrollment State", filters={
				"school": state.school, "course_offering": state.course_offering,
				"user": state.user, "name": ["!=", state.name],
			}, fields=["desired_state", "remote_state"])
			if any(row.desired_state == "Enrolled" or row.remote_state == "Enrolled" for row in other_states):
				frappe.throw(_("Moodle manual unenrollment removes course access for all roles; another enrollment requires operator review."))
			# Never create or modify a remote account or course while removing access.
			mappings = []
			for doctype, name in (("School", school.name), ("School Course Offering", offering.name), ("User", state.user)):
				mapping_name = frappe.db.get_value("LMS Entity Mapping", {
					"school": school.name, "local_doctype": doctype, "local_name": name, "status": "Active",
				}, "name")
				if not mapping_name:
					frappe.throw(_("Cannot withdraw Moodle access without an active {0} mapping; operator reconciliation is required.").format(doctype))
				mappings.append(frappe.get_doc("LMS Entity Mapping", mapping_name))
			tenant_mapping, course_mapping, user_mapping = mappings
			if not school.lms_provisioned or not school.lms_tenant_id:
				frappe.throw(_("Cannot withdraw Moodle access without an existing tenant binding."))
			# A provisioned tenant lookup fails closed if the tenant was removed or
			# this site was cloned; it must never create a tenant during withdrawal.
			tenant = adapter.ensure_tenant(school)
			if (str(tenant["remote_id"]) != str(school.lms_tenant_id)
				or str(tenant_mapping.remote_id) != str(school.lms_tenant_id)
				or any(mapping.remote_context != tenant["remote_context"] for mapping in mappings)):
				frappe.throw(_("Moodle tenant, user and course mappings do not match the verified tenant."))
			course = {"remote_id": course_mapping.remote_id, "remote_context": course_mapping.remote_context, "remote_url": course_mapping.remote_url}
			remote_user = {"remote_id": user_mapping.remote_id, "remote_context": user_mapping.remote_context}
		else:
			tenant = adapter.ensure_tenant(school)
			tenant_mapping = upsert_entity_mapping("School", school.name, school.name, tenant)
			_save_tenant_binding(school, tenant)
			course = adapter.create_course(offering)
			course_mapping = upsert_entity_mapping("School Course Offering", offering.name, offering.school, course)
			user = frappe.get_doc("User", state.user)
			remote_user = adapter.ensure_user(user, school, tenant=tenant)
			user_mapping = upsert_entity_mapping("User", user.name, school.name, remote_user)
		remote = adapter.sync_enrollment(state, remote_user, course)
		state.remote_state = remote["remote_state"]
		state.last_error = None
		state.last_verified_at = now_datetime()
		state.save(ignore_permissions=True)
		enrollment_mapping = upsert_entity_mapping(
			"LMS Enrollment State", state.name, state.school, remote
		)
		return remote, [tenant_mapping, course_mapping, user_mapping, enrollment_mapping]

	frappe.throw(_("Unsupported sync operation {0}.").format(operation.operation_type))


def queue_offering_staff_enrollments(course_offering):
	offering = frappe.get_doc("School Course Offering", course_offering)
	teacher_user = None
	if offering.instructor:
		if not frappe.get_meta("Instructor").has_field("padars_user"):
			frappe.throw(_("Add a Moodle User mapping to the assigned Instructor before syncing this course."))
		teacher_user = frappe.db.get_value("Instructor", offering.instructor, "padars_user")
		if not teacher_user or not frappe.db.exists("User", {"name": teacher_user, "enabled": 1, "user_type": "System User"}):
			frappe.throw(_("The assigned Instructor must map to an enabled Frappe System User."))
		state = ensure_enrollment_state(offering, teacher_user, "Teacher")
		request_enrollment_sync(state)

	for row in frappe.get_all("LMS Enrollment State", filters={
		"school": offering.school, "course_offering": offering.name,
		"role": "Teacher", "desired_state": "Enrolled",
	}, fields=["name", "user"]):
		if row.user == teacher_user:
			continue
		frappe.db.sql("select name from `tabLMS Enrollment State` where name=%s for update", row.name)
		state = frappe.get_doc("LMS Enrollment State", row.name)
		if state.desired_state == "Enrolled":
			state.desired_state = "Not Enrolled"
			state.save(ignore_permissions=True)
			request_enrollment_sync(state)

	manager = frappe.db.get_value("School", offering.school, "primary_school_manager")
	if manager and frappe.db.exists("User", {"name": manager, "enabled": 1, "user_type": "System User"}):
		state = ensure_enrollment_state(offering, manager, "School Manager")
		request_enrollment_sync(state)


def queue_offering_student_enrollments(course_offering, students=None, reconcile=False, withdraw_only=False):
	offering = frappe.get_doc("School Course Offering", course_offering) if isinstance(course_offering, str) else course_offering
	if reconcile and students is not None:
		frappe.throw(_("Roster reconciliation requires the complete group, not a selected subset."))
	students = students if students is not None else _get_offering_students(offering)
	operations = []
	eligible_users = set()
	for student in students:
		user = frappe.db.get_value("Student", student, "user")
		eligible_users.add(user)
		if not withdraw_only:
			state = ensure_enrollment_state(offering, user, "Student")
			operations.append(request_enrollment_sync(state))
	if reconcile:
		states = frappe.get_all("LMS Enrollment State", filters={
			"school": offering.school, "course_offering": offering.name,
			"role": "Student", "desired_state": "Enrolled",
		}, fields=["name", "user"])
		for row in states:
			if row.user in eligible_users:
				continue
			frappe.db.sql("select name from `tabLMS Enrollment State` where name=%s for update", row.name)
			state = frappe.get_doc("LMS Enrollment State", row.name)
			if state.desired_state == "Enrolled":
				state.desired_state = "Not Enrolled"
				state.save(ignore_permissions=True)
			operations.append(request_enrollment_sync(state))
	return operations


def sync_group_roster_after_update(doc, method=None):
	"""Queue currently enrolled LMS students after a Group roster edit commits."""
	school = doc.get("padars_school")
	if not school or not frappe.db.get_value("School", school, "lms_enabled"):
		return []
	auto_enrollment = bool(frappe.db.get_value("School", school, "lms_auto_enrollment"))
	offerings = frappe.get_all(
		"School Course Offering",
		filters={"school": school, "student_group": doc.name, "status": ["!=", "Archived"]},
		pluck="name",
		ignore_permissions=True,
	)
	old_flag = frappe.flags.get("padars_lms_auto_sync")
	old_withdrawal_flag = frappe.flags.get("padars_lms_roster_withdrawal")
	frappe.flags.padars_lms_auto_sync = True
	frappe.flags.padars_lms_roster_withdrawal = True
	try:
		return [queue_offering_student_enrollments(name, reconcile=True, withdraw_only=not auto_enrollment) for name in offerings]
	finally:
		frappe.flags.padars_lms_auto_sync = old_flag
		frappe.flags.padars_lms_roster_withdrawal = old_withdrawal_flag


def sync_student_eligibility_change(doc, method=None):
	old = doc.get_doc_before_save()
	if not old or (old.enabled == doc.enabled and old.user == doc.user):
		return []
	return _sync_student_groups(doc.name)


def sync_user_eligibility_change(doc, method=None):
	old = doc.get_doc_before_save()
	if not old or (old.enabled == doc.enabled and old.user_type == doc.user_type):
		return []
	students = frappe.get_all("Student", filters={"user": doc.name}, pluck="name")
	return [_sync_student_groups(student) for student in students]


def _sync_student_groups(student):
	groups = frappe.get_all("Student Group Student", filters={"student": student, "active": 1}, pluck="parent")
	return [sync_group_roster_after_update(frappe.get_doc("Student Group", group)) for group in set(groups)]


def sync_program_enrollment_change(doc, method=None):
	"""Reconcile affected offerings after an annual enrollment is submitted or cancelled."""
	school = doc.get("padars_school")
	if not school or not frappe.db.get_value("School", school, "lms_enabled"):
		return []
	auto_enrollment = bool(frappe.db.get_value("School", school, "lms_auto_enrollment"))
	groups = frappe.get_all("Student Group Student", filters={"student": doc.student, "active": 1}, pluck="parent")
	if not groups:
		return []
	offerings = frappe.get_all("School Course Offering", filters={
		"school": school, "academic_year": doc.academic_year, "program": doc.program,
		"student_group": ["in", groups], "status": ["!=", "Archived"],
	}, pluck="name")
	old_flag = frappe.flags.get("padars_lms_auto_sync")
	old_withdrawal_flag = frappe.flags.get("padars_lms_roster_withdrawal")
	frappe.flags.padars_lms_auto_sync = True
	frappe.flags.padars_lms_roster_withdrawal = True
	try:
		return [queue_offering_student_enrollments(name, reconcile=True, withdraw_only=not auto_enrollment) for name in offerings]
	finally:
		frappe.flags.padars_lms_auto_sync = old_flag
		frappe.flags.padars_lms_roster_withdrawal = old_withdrawal_flag


def queue_school_auto_enrollment(school_name):
	if not frappe.db.get_value("School", school_name, "lms_enabled"):
		return []
	offerings = frappe.get_all(
		"School Course Offering",
		filters={"school": school_name, "status": ["!=", "Archived"]},
		pluck="name",
		ignore_permissions=True,
	)
	queued = []
	for offering_name in offerings:
		offering = frappe.get_doc("School Course Offering", offering_name)
		request_course_offering_sync(offering)
		if offering.student_group:
			sync_group_roster_after_update(frappe.get_doc("Student Group", offering.student_group))
		queued.append(offering_name)
	return queued


def queue_school_roster_withdrawals(school_name):
	"""Recheck mapped rosters after reconnect without creating course enrollments."""
	offerings = frappe.get_all("School Course Offering", filters={
		"school": school_name, "status": ["!=", "Archived"], "student_group": ["is", "set"],
	}, fields=["name", "student_group"])
	groups = {row.student_group for row in offerings if frappe.db.exists("LMS Entity Mapping", {
		"school": school_name, "local_doctype": "School Course Offering", "local_name": row.name,
		"status": "Active",
	})}
	return [sync_group_roster_after_update(frappe.get_doc("Student Group", group)) for group in groups]


def queue_school_staff_reconciliation(school_name):
	"""Reconcile teachers on already mapped courses after a tenant reconnect."""
	offerings = frappe.get_all("School Course Offering", filters={
		"school": school_name, "status": ["!=", "Archived"],
	}, pluck="name")
	queued = []
	for offering in offerings:
		if frappe.db.exists("LMS Entity Mapping", {
			"school": school_name, "local_doctype": "School Course Offering", "local_name": offering,
			"status": "Active",
		}):
			queue_offering_staff_enrollments(offering)
			queued.append(offering)
	return queued


def _save_tenant_binding(school, remote):
	current_id = str(school.lms_tenant_id or "")
	current_idnumber = str(school.lms_tenant_idnumber or "")
	if current_id and current_id != str(remote["remote_id"]):
		frappe.throw(_("The saved Moodle tenant ID cannot be replaced automatically."))
	if current_idnumber and current_idnumber != str(remote["tenant_idnumber"]):
		frappe.throw(_("The saved Moodle tenant ID number cannot be replaced automatically."))
	old_flag = frappe.flags.get("padars_lms_service_update")
	frappe.flags.padars_lms_service_update = True
	try:
		school.lms_tenant_name = remote["tenant_name"]
		school.lms_tenant_id = str(remote["remote_id"])
		school.lms_tenant_idnumber = str(remote["tenant_idnumber"])
		school.lms_course_category_id = str(remote["category_id"])
		school.lms_tenant_cohort_id = str(remote["cohort_id"])
		school.lms_associated_cohort_id = str(remote.get("associated_cohort_id") or "")
		school.lms_moodle_url = remote.get("remote_url") or ""
		school.lms_provisioned = 1
		school.lms_status = "Connected"
		school.lms_last_sync = now_datetime()
		school.lms_last_error = None
		school.save(ignore_permissions=True)
	finally:
		frappe.flags.padars_lms_service_update = old_flag


def upsert_entity_mapping(local_doctype, local_name, school, remote):
	local_key = hashlib.sha256(f"{local_doctype}\0{local_name}".encode()).hexdigest()
	existing = frappe.db.get_value("LMS Entity Mapping", {"local_mapping_key": local_key}, "name")
	if existing:
		mapping = frappe.get_doc("LMS Entity Mapping", existing)
		if (
			mapping.remote_id != str(remote["remote_id"])
			or mapping.remote_type != remote["remote_type"]
			or mapping.remote_context != remote["remote_context"]
		):
			frappe.throw(_("An existing LMS entity mapping cannot be silently replaced."))
		mapping.status = "Active"
		mapping.last_verified_at = now_datetime()
		mapping.save(ignore_permissions=True)
		return mapping

	return frappe.get_doc({
		"doctype": "LMS Entity Mapping",
		"school": school,
		"local_doctype": local_doctype,
		"local_name": local_name,
		"remote_type": remote["remote_type"],
		"remote_id": str(remote["remote_id"]),
		"remote_context": remote["remote_context"],
		"remote_url": remote.get("remote_url") or "",
		"status": "Active",
		"last_verified_at": now_datetime(),
	}).insert(ignore_permissions=True)


def _safe_error(error):
	message = str(error).splitlines()[0].strip()
	try:
		settings = frappe.get_single("LMS Settings")
		token = settings.get_password("api_token", raise_exception=False)
		if token:
			message = message.replace(token, "[redacted]")
	except Exception:
		pass
	if any(secret in message.lower() for secret in ("password", "api_token", "authorization", "bearer ", "wstoken")):
		return _("The remote LMS request failed; sensitive details were removed.")
	return message[:500] or _("The remote LMS request failed.")


def _fail_operation(operation, error):
	operation.state = "Failed"
	operation.last_error = _safe_error(error)
	operation.next_retry_at = add_to_date(now_datetime(), minutes=5)
	operation.save(ignore_permissions=True)
	return operation


def _set_school_lms_error(school_name, error):
	school = frappe.get_doc("School", school_name)
	if not school.lms_enabled:
		return
	old_flag = frappe.flags.get("padars_lms_service_update")
	frappe.flags.padars_lms_service_update = True
	try:
		school.lms_status = "Error"
		school.lms_last_error = _safe_error(error)
		school.save(ignore_permissions=True)
	finally:
		frappe.flags.padars_lms_service_update = old_flag


def retry_sync_operation(operation):
	operation = frappe.get_doc("LMS Sync Operation", operation)
	if operation.operation_type == "Provision Tenant":
		if not is_lms_operator():
			frappe.throw(_("Only company Moodle operators can retry tenant provisioning."), frappe.PermissionError)
	elif not can_manage_moodle(operation.school):
		frappe.throw(_("You are not authorized to retry this Moodle operation."), frappe.PermissionError)
	if not frappe.db.get_value("School", operation.school, "lms_enabled"):
		frappe.throw(_("Moodle is disabled for this School."))
	if operation.state != "Failed":
		frappe.throw(_("Only failed sync operations can be retried."))
	if (operation.attempt_count or 0) >= MAX_SYNC_ATTEMPTS:
		frappe.throw(_("This synchronization has exhausted its retry limit."))
	operation.state = "Queued"
	operation.last_error = None
	operation.next_retry_at = None
	operation.save(ignore_permissions=True)
	frappe.enqueue(
		"padars.integrations.moodle.service.process_sync_operation",
		operation=operation.name,
		queue="long" if operation.operation_type in {"Read Grades", "Read Learning"} else "short",
		job_name=f"retry:{operation.name}:{operation.attempt_count or 0}",
		enqueue_after_commit=True,
	)
	return operation


def recover_stale_sync_operations():
	"""Mark worker-interrupted operations failed so an operator can retry safely."""
	stale_before = add_to_date(now_datetime(), minutes=-30)
	names = frappe.get_all(
		"LMS Sync Operation",
		filters={"state": "Running", "last_attempt_at": ["<", stale_before]},
		pluck="name",
		ignore_permissions=True,
	)
	for name in names:
		operation = frappe.get_doc("LMS Sync Operation", name)
		if operation.state != "Running":
			continue
		operation.state = "Failed"
		operation.last_error = _("The worker stopped during this attempt; retry is available.")
		operation.next_retry_at = add_to_date(now_datetime(), minutes=5)
		operation.save(ignore_permissions=True)
	return names
