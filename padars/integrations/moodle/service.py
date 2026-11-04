import json

import frappe
from frappe import _
from frappe.utils import add_to_date, now_datetime

from padars.integrations.moodle.mock import MockMoodleAdapter
from padars.padars.doctype.lms_sync_operation.lms_sync_operation import MAX_SYNC_ATTEMPTS


def get_adapter():
	if not frappe.db.exists("LMS Settings", "LMS Settings"):
		return MockMoodleAdapter()

	settings = frappe.get_single("LMS Settings")
	if not settings.enabled:
		frappe.throw(_("The LMS integration is disabled."))
	if settings.adapter == "Mock":
		return MockMoodleAdapter()

	frappe.throw(_("The live Moodle adapter is not configured in this release."))


def request_course_offering_sync(offering):
	return request_sync_operation(
		offering.school,
		"Provision Course",
		"School Course Offering",
		offering.name,
		f"course-offering:{offering.name}:provision",
	)


def request_school_tenant_sync(school):
	return request_sync_operation(
		school.name, "Provision Tenant", "School", school.name, f"school:{school.name}:tenant"
	)


def request_user_sync(user, school):
	return request_sync_operation(
		school.name, "Provision User", "User", user.name, f"user:{school.name}:{user.name}:provision"
	)


def request_enrollment_sync(enrollment_state):
	return request_sync_operation(
		enrollment_state.school,
		"Sync Enrollment",
		"LMS Enrollment State",
		enrollment_state.name,
		f"enrollment:{enrollment_state.name}:sync",
	)


def request_sync_operation(school, operation_type, target_doctype, target_name, idempotency_key):
	"""Persist one idempotent integration request and enqueue it after commit."""
	existing = frappe.db.exists("LMS Sync Operation", {"idempotency_key": idempotency_key})
	if existing:
		return frappe.get_doc("LMS Sync Operation", existing)

	try:
		operation = frappe.get_doc(
			{
				"doctype": "LMS Sync Operation",
				"school": school,
				"operation_type": operation_type,
				"target_doctype": target_doctype,
				"target_name": target_name,
				"idempotency_key": idempotency_key,
				"state": "Queued",
			}
		).insert()
	except frappe.exceptions.DuplicateEntryError:
		return frappe.get_doc(
			"LMS Sync Operation", frappe.db.get_value("LMS Sync Operation", {"idempotency_key": idempotency_key})
		)
	frappe.enqueue(
		"padars.integrations.moodle.service.process_sync_operation",
		operation=operation.name,
		queue="short",
		job_name=idempotency_key,
		enqueue_after_commit=True,
	)
	return operation


def process_sync_operation(operation, adapter=None):
	operation = frappe.get_doc("LMS Sync Operation", operation)
	if operation.state == "Succeeded":
		return operation

	if operation.state not in {"Pending", "Queued", "Failed"}:
		frappe.throw(_("Sync operation {0} is not ready to process.").format(operation.name))
	if (operation.attempt_count or 0) >= MAX_SYNC_ATTEMPTS:
		frappe.throw(_("Sync operation {0} has exhausted its retry limit.").format(operation.name))

	operation.state = "Running"
	operation.attempt_count = (operation.attempt_count or 0) + 1
	operation.last_attempt_at = now_datetime()
	operation.save(ignore_permissions=True)

	try:
		adapter = adapter or get_adapter()
		remote, mappings = process_remote_operation(operation, adapter)
		operation.state = "Succeeded"
		operation.last_error = None
		operation.next_retry_at = None
		operation.diagnostics = json.dumps(
			{
				"adapter": getattr(adapter, "name", adapter.__class__.__name__),
				"mappings": [mapping.name for mapping in mappings],
			},
			sort_keys=True,
		)
		operation.save(ignore_permissions=True)
		return operation
	except Exception as exc:
		operation.state = "Failed"
		operation.last_error = _safe_error(exc)
		operation.next_retry_at = add_to_date(now_datetime(), minutes=5)
		operation.save(ignore_permissions=True)
		return operation


def process_remote_operation(operation, adapter):
	if operation.operation_type == "Provision Tenant":
		school = frappe.get_doc("School", operation.target_name)
		remote = adapter.ensure_tenant(school)
		return remote, [upsert_entity_mapping("School", school.name, school.name, remote)]

	if operation.operation_type == "Provision User":
		user = frappe.get_doc("User", operation.target_name)
		school = frappe.get_doc("School", operation.school)
		remote = adapter.ensure_user(user, school)
		return remote, [upsert_entity_mapping("User", user.name, school.name, remote)]

	if operation.operation_type == "Provision Course":
		offering = frappe.get_doc("School Course Offering", operation.target_name)
		tenant = adapter.ensure_tenant(frappe.get_doc("School", offering.school))
		remote = adapter.create_course(offering)
		tenant_mapping = upsert_entity_mapping("School", offering.school, offering.school, tenant)
		course_mapping = upsert_entity_mapping(
			"School Course Offering", offering.name, offering.school, remote
		)
		return remote, [tenant_mapping, course_mapping]

	if operation.operation_type == "Sync Enrollment":
		enrollment_state = frappe.get_doc("LMS Enrollment State", operation.target_name)
		remote = adapter.sync_enrollment(enrollment_state)
		enrollment_state.remote_state = remote["remote_state"]
		enrollment_state.last_error = None
		enrollment_state.last_verified_at = now_datetime()
		enrollment_state.save(ignore_permissions=True)
		mapping = upsert_entity_mapping(
			"LMS Enrollment State", enrollment_state.name, enrollment_state.school, remote
		)
		return remote, [mapping]

	frappe.throw(_("Unsupported sync operation {0}.").format(operation.operation_type))


def _safe_error(error):
	message = str(error).splitlines()[0].strip()
	if any(secret in message.lower() for secret in ("password", "api_token", "authorization", "bearer ")):
		return _("The remote LMS request failed. See server logs for the classified error.")
	return message[:500] or _("The remote LMS request failed.")


def upsert_entity_mapping(local_doctype, local_name, school, remote):
	filters = {
		"local_doctype": local_doctype,
		"local_name": local_name,
		"remote_context": remote["remote_context"],
	}
	existing = frappe.db.exists("LMS Entity Mapping", filters)
	if existing:
		mapping = frappe.get_doc("LMS Entity Mapping", existing)
		mapping.remote_id = remote["remote_id"]
		mapping.remote_type = remote["remote_type"]
		mapping.status = "Active"
		mapping.last_verified_at = now_datetime()
		mapping.save(ignore_permissions=True)
		return mapping

	return frappe.get_doc(
		{
			"doctype": "LMS Entity Mapping",
			"school": school,
			"local_doctype": local_doctype,
			"local_name": local_name,
			"remote_type": remote["remote_type"],
			"remote_id": remote["remote_id"],
			"remote_context": remote["remote_context"],
			"status": "Active",
			"last_verified_at": now_datetime(),
		}
	).insert(ignore_permissions=True)


def retry_sync_operation(operation):
	operation = frappe.get_doc("LMS Sync Operation", operation)
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
		queue="short",
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

