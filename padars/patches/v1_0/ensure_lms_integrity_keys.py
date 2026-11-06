"""Backfill Padars Moodle identity keys before adding their unique indexes."""

import hashlib
from uuid import uuid4

import frappe


def execute():
	for row in frappe.get_all("School", fields=["name", "lms_installation_uuid", "lms_origin_site"]):
		values = {}
		if not row.lms_installation_uuid:
			values["lms_installation_uuid"] = uuid4().hex
		if not row.lms_origin_site:
			values["lms_origin_site"] = frappe.local.site
		if values:
			frappe.db.set_value("School", row.name, values, update_modified=False)

	for row in frappe.get_all(
		"LMS Enrollment State", fields=["name", "school", "user", "course_offering", "role"]
	):
		key = _digest(row.school, row.user, row.course_offering, row.role)
		frappe.db.set_value("LMS Enrollment State", row.name, "enrollment_key", key, update_modified=False)

	for row in frappe.get_all(
		"LMS Entity Mapping",
		fields=["name", "local_doctype", "local_name", "remote_context", "remote_type", "remote_id"],
	):
		local_key = _digest(row.local_doctype, row.local_name)
		remote_key = _digest(row.remote_context, row.remote_type, row.remote_id)
		frappe.db.set_value(
			"LMS Entity Mapping",
			row.name,
			{"local_mapping_key": local_key, "remote_mapping_key": remote_key},
			update_modified=False,
		)

	_assert_unique("LMS Enrollment State", "enrollment_key")
	_assert_unique("LMS Entity Mapping", "local_mapping_key")
	_assert_unique("LMS Entity Mapping", "remote_mapping_key")
	_assert_unique("School", "lms_installation_uuid")
	frappe.db.add_unique("LMS Enrollment State", "enrollment_key", "unique_lms_enrollment_key")
	frappe.db.add_unique("LMS Entity Mapping", "local_mapping_key", "unique_lms_local_mapping_key")
	frappe.db.add_unique("LMS Entity Mapping", "remote_mapping_key", "unique_lms_remote_mapping_key")
	frappe.db.add_unique("School", "lms_installation_uuid", "unique_school_lms_installation_uuid")


def _digest(*values):
	return hashlib.sha256("\0".join(str(value or "") for value in values).encode()).hexdigest()


def _assert_unique(doctype, field):
	duplicates = frappe.db.sql(
		f"""select `{field}`, count(*) as row_count
			from `tab{doctype}` group by `{field}` having count(*) > 1 limit 1""",
		as_dict=True,
	)
	if duplicates:
		frappe.throw(
			f"Cannot add the Padars LMS uniqueness constraint: {doctype}.{field} has duplicate values. "
			"Review and reconcile the existing records before migrating."
		)
