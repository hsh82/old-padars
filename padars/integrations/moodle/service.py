import json

import frappe
from frappe import _
from frappe.utils import add_to_date, now_datetime

from padars.integrations.moodle.mock import MockMoodleAdapter


def get_adapter():
	if not frappe.db.exists("LMS Settings", "LMS Settings"):
		return MockMoodleAdapter()

	settings = frappe.get_single("LMS Settings")
	if settings.adapter == "Mock":
		return MockMoodleAdapter()

	frappe.throw(_("The live Moodle adapter is not configured in this release."))


def request_course_offering_sync(offering):
	"""Persist one idempotent provisioning request and enqueue it after commit."""
	idempotency_key = f"course-offering:{offering.name}:provision"
	existing = frappe.db.exists("LMS Sync Operation", {"idempotency_key": idempotency_key})
	if existing:
		return frappe.get_doc("LMS Sync Operation", existing)

	operation = frappe.get_doc(
		{
			"doctype": "LMS Sync Operation",
			"school": offering.school,
			"operation_type": "Provision Course",
			"target_doctype": "School Course Offering",
			"target_name": offering.name,
			"idempotency_key": idempotency_key,
			"state": "Queued",
		}
	).insert()
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

	operation.state = "Running"
	operation.attempt_count = (operation.attempt_count or 0) + 1
	operation.last_attempt_at = now_datetime()
	operation.save(ignore_permissions=True)

	try:
		if operation.target_doctype != "School Course Offering":
			frappe.throw(_("Unsupported sync target {0}.").format(operation.target_doctype))

		offering = frappe.get_doc(operation.target_doctype, operation.target_name)
		adapter = adapter or get_adapter()
		remote = adapter.create_course(offering)
		mapping = upsert_entity_mapping(offering, remote)
		operation.state = "Succeeded"
		operation.last_error = None
		operation.next_retry_at = None
		operation.diagnostics = json.dumps(
			{"adapter": getattr(adapter, "name", adapter.__class__.__name__), "mapping": mapping.name},
			sort_keys=True,
		)
		operation.save(ignore_permissions=True)
		return operation
	except Exception as exc:
		operation.state = "Failed"
		operation.last_error = str(exc)
		operation.next_retry_at = add_to_date(now_datetime(), minutes=5)
		operation.save(ignore_permissions=True)
		return operation


def upsert_entity_mapping(offering, remote):
	filters = {
		"local_doctype": "School Course Offering",
		"local_name": offering.name,
		"remote_context": remote["remote_context"],
	}
	existing = frappe.db.exists("LMS Entity Mapping", filters)
	if existing:
		mapping = frappe.get_doc("LMS Entity Mapping", existing)
		mapping.remote_id = remote["remote_id"]
		mapping.remote_type = remote["remote_type"]
		mapping.status = "Active"
		mapping.save(ignore_permissions=True)
		return mapping

	return frappe.get_doc(
		{
			"doctype": "LMS Entity Mapping",
			"school": offering.school,
			"local_doctype": "School Course Offering",
			"local_name": offering.name,
			"remote_type": remote["remote_type"],
			"remote_id": remote["remote_id"],
			"remote_context": remote["remote_context"],
			"status": "Active",
		}
	).insert(ignore_permissions=True)


def retry_sync_operation(operation):
	operation = frappe.get_doc("LMS Sync Operation", operation)
	if operation.state != "Failed":
		frappe.throw(_("Only failed sync operations can be retried."))

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

