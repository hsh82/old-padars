"""Add Stage 1 database constraints only after proving existing data is safe."""

import frappe
from frappe import _


UNIQUE_CONSTRAINTS = (
	("School Membership", ("school", "user", "school_role")),
	("School Course Offering", ("school", "academic_year", "course", "student_group")),
	("LMS Entity Mapping", ("local_doctype", "local_name", "remote_context")),
	("LMS Entity Mapping", ("remote_type", "remote_id", "remote_context")),
	("LMS Enrollment State", ("user", "course_offering", "role")),
)
INDEXES = (
	("LMS Sync Operation", ("school", "state"), "padars_school_state"),
	("LMS Sync Operation", ("state", "next_retry_at"), "padars_state_retry"),
	("LMS Entity Mapping", ("school", "local_doctype", "local_name"), "padars_mapping_lookup"),
)


def _duplicates(doctype, fields):
	field_sql = ", ".join(f"`{field}`" for field in fields)
	return frappe.db.sql(
		f"select {field_sql}, count(*) as duplicate_count from `tab{doctype}` "
		f"group by {field_sql} having count(*) > 1 limit 5",
		as_dict=True,
	)


def _assert_safe_to_constrain():
	for doctype, fields in UNIQUE_CONSTRAINTS:
		duplicates = _duplicates(doctype, fields)
		if duplicates:
			frappe.throw(
				_("Cannot add the Padars uniqueness constraint for {0} ({1}); duplicate records exist: {2}").format(
					doctype, ", ".join(fields), duplicates
				)
			)


def execute():
	_assert_safe_to_constrain()
	for doctype, fields in UNIQUE_CONSTRAINTS:
		frappe.db.add_unique(doctype, fields)
	for doctype, fields, index_name in INDEXES:
		frappe.db.add_index(doctype, fields, index_name)
