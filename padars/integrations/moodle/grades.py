"""Durable, read-only discovery of Moodle grades for reviewed academic imports."""

import hashlib
import json
from decimal import Decimal, InvalidOperation

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, strip_html

from padars.permissions_site import is_school_manager, school_permission_query_conditions
from padars.school_context import get_primary_school

GRADE_READ_ROLES = {"Padars Teacher", "Padars Academic Staff", "Padars Grade Entry Staff"}


def _can_read_offering(offering, user=None):
	user = user or frappe.session.user
	school = frappe.db.get_value("School Course Offering", offering, "school")
	return bool(school == get_primary_school() and
		(is_school_manager(school, user) or (GRADE_READ_ROLES.intersection(frappe.get_roles(user))
		and frappe.has_permission("School Course Offering", "read", offering, user=user))))


class MoodleGradeSnapshot(Document):
	def validate(self):
		if not self.is_new() or not frappe.flags.get("padars_grade_capture"):
			frappe.throw(_("Moodle grade snapshots are immutable service records."), frappe.PermissionError)

	def on_trash(self):
		frappe.throw(_("Moodle grade source history cannot be deleted."), frappe.PermissionError)


def has_permission(doc, ptype, user=None, **kwargs):
	return ptype in {"read", "select"} and doc.school == get_primary_school() and _can_read_offering(doc.course_offering, user)


def query_conditions(user=None):
	user = user or frappe.session.user
	if not is_school_manager(get_primary_school(), user) and not GRADE_READ_ROLES.intersection(frappe.get_roles(user)):
		return "1=0"
	condition = school_permission_query_conditions(user, "School Course Offering")
	return f"`tabMoodle Grade Snapshot`.school={frappe.db.escape(get_primary_school() or '')} and exists (select name from `tabSchool Course Offering` where name=`tabMoodle Grade Snapshot`.course_offering and ({condition or '1=1'}))"


def clean_items(items):
	if not isinstance(items, list) or len(items) > 2000:
		frappe.throw(_("The Moodle grade item response exceeds the supported shape or limit."))
	clean, seen = [], set()
	for item in items:
		item_id = int(item.get("id") or 0)
		if item_id <= 0 or item_id in seen:
			frappe.throw(_("Moodle returned duplicate or invalid grade item identifiers."))
		seen.add(item_id)
		row = {"id": item_id, "name": strip_html(str(item.get("itemname") or ""))[:255],
			"itemtype": str(item.get("itemtype") or "")[:30], "module": str(item.get("itemmodule") or "")[:50],
			"scaleid": int(item.get("scaleid") or 0), "outcomeid": int(item.get("outcomeid") or 0),
			"cmid": int(item.get("cmid") or 0), "graded_at": int(item.get("gradedategraded") or 0)}
		for field in ("graderaw", "grademin", "grademax"):
			value = item.get(field)
			try:
				number = Decimal(str(value)) if value is not None else None
			except InvalidOperation:
				frappe.throw(_("Moodle returned an invalid numeric grade."))
			if number is not None and not number.is_finite():
				frappe.throw(_("Moodle returned a non-finite grade."))
			row[field] = str(number) if number is not None else None
		for field in ("gradeishidden", "gradehiddenbydate", "gradeneedsupdate", "gradeisoverridden", "gradeislocked"):
			row[field] = bool(item.get(field))
		row["status"] = "Ready"
		if row["graderaw"] is None:
			row["status"] = "Missing"
		elif row["gradeishidden"] or row["gradehiddenbydate"] or row["gradeneedsupdate"]:
			row["status"] = "Unavailable"
		elif row["scaleid"] or row["outcomeid"] or row["grademin"] is None or row["grademax"] is None:
			row["status"] = "Unsupported"
		elif Decimal(row["grademax"]) <= Decimal(row["grademin"]) or not Decimal(row["grademin"]) <= Decimal(row["graderaw"]) <= Decimal(row["grademax"]):
			row["status"] = "Conflict"
		elif row["gradeisoverridden"]:
			row["status"] = "Review Required"
		clean.append(row)
	return sorted(clean, key=lambda row: row["id"])


@frappe.whitelist(methods=["POST"])
def request_grade_discovery(course_offering):
	from padars.integrations.moodle.service import request_sync_operation
	offering = frappe.get_doc("School Course Offering", course_offering)
	offering.check_permission("read")
	if not is_school_manager(offering.school) or offering.school != get_primary_school():
		frappe.throw(_("Only this School's Manager can request grade discovery."), frappe.PermissionError)
	if offering.status == "Archived":
		frappe.throw(_("Archived offerings cannot fetch current grades."))
	frappe.db.sql("select name from `tabSchool Course Offering` where name=%s for update", offering.name)
	pending = frappe.db.get_value("LMS Sync Operation", {"target_doctype": "School Course Offering",
		"target_name": offering.name, "operation_type": "Read Grades", "state": ["in", ["Pending", "Queued", "Running"]]}, "name")
	if pending:
		return {"operation": pending}
	operation = request_sync_operation(offering.school, "Read Grades", "School Course Offering", offering.name,
		f"grade:{frappe.generate_hash(length=32)}")
	return {"operation": operation.name}


def resolve_course_roster(operation):
	"""Collect a bounded complete local roster before persisting any sources."""
	frappe.db.sql("select name from `tabSchool Course Offering` where name=%s for update", operation.target_name)
	offering = frappe.get_doc("School Course Offering", operation.target_name)
	if offering.school != operation.school or offering.school != get_primary_school() or offering.status == "Archived":
		frappe.throw(_("The grade operation's School or offering is no longer eligible."))
	school = frappe.get_doc("School", offering.school)
	def mapping(doctype, name):
		names = frappe.get_all("LMS Entity Mapping", filters={"school": school.name, "local_doctype": doctype,
			"local_name": name, "status": "Active"}, pluck="name")
		if len(names) != 1:
			frappe.throw(_("Grade discovery requires unique active tenant, course and user mappings."))
		return frappe.get_doc("LMS Entity Mapping", names[0])
	tenant, course = mapping("School", school.name), mapping("School Course Offering", offering.name)
	if tenant.remote_context != course.remote_context:
		frappe.throw(_("The grade course mapping differs from the School tenant."))
	students = frappe.get_all("Student Group Student", filters={"parent": offering.student_group,
		"parenttype": "Student Group", "active": 1}, pluck="student")
	if not students or len(students) > 200:
		frappe.throw(_("Grade discovery requires between one and 200 active students per offering."))
	roster = []
	for student in sorted(set(students)):
		user = frappe.db.get_value("Student", {"name": student, "enabled": 1}, "user")
		if not user or not frappe.db.exists("User", {"name": user, "enabled": 1}) or not frappe.db.exists("Program Enrollment", {
			"student": student, "program": offering.program, "academic_year": offering.academic_year,
			"padars_school": school.name, "docstatus": 1}):
			frappe.throw(_("Complete active student accounts and submitted academic enrollment before fetching grades."))
		if not frappe.db.exists("LMS Enrollment State", {"school": school.name, "course_offering": offering.name,
			"user": user, "role": "Student", "desired_state": "Enrolled", "remote_state": "Enrolled"}):
			frappe.throw(_("Complete Moodle roster synchronization before fetching grades."))
		remote_user = mapping("User", user)
		if remote_user.remote_context != tenant.remote_context:
			frappe.throw(_("A grade user mapping differs from the School tenant."))
		roster.append((student, remote_user))
	return offering, school, tenant, course, roster


def capture_grades(operation, adapter):
	offering, school, tenant, course, roster = resolve_course_roster(operation)
	captured = [(student, user, clean_items(adapter.read_grade_items(school, course, user))) for student, user in roster]
	observed = now_datetime()
	frappe.db.savepoint("padars_grade_sources")
	old_flag = frappe.flags.get("padars_grade_capture")
	frappe.flags.padars_grade_capture = True
	try:
		for student, remote_user, items in captured:
			key = hashlib.sha256(f"{operation.name}\0{student}".encode()).hexdigest()
			if frappe.db.exists("Moodle Grade Snapshot", {"snapshot_key": key}):
				continue
			payload = json.dumps(items, sort_keys=True, separators=(",", ":"))
			frappe.get_doc({"doctype": "Moodle Grade Snapshot", "school": school.name, "course_offering": offering.name,
				"student": student, "source_operation": operation.name, "remote_context": tenant.remote_context,
				"remote_course": course.remote_id, "remote_user": remote_user.remote_id, "observed_at": observed,
				"snapshot_key": key, "payload_digest": hashlib.sha256(payload.encode()).hexdigest(), "items": payload}).insert(ignore_permissions=True)
	except Exception:
		frappe.db.rollback(save_point="padars_grade_sources")
		raise
	finally:
		frappe.flags.padars_grade_capture = old_flag
	return {"captured": len(captured)}


@frappe.whitelist()
def list_grade_snapshots(course_offering, start=0):
	if not _can_read_offering(course_offering):
		frappe.throw(_("These instructional grades are not available to your account."), frappe.PermissionError)
	start = int(start)
	if start < 0:
		frappe.throw(_("Invalid grade pagination."))
	return frappe.get_list("Moodle Grade Snapshot", filters={"course_offering": course_offering},
		fields=["name", "student", "observed_at", "source_operation"], start=start, page_length=50,
		order_by="observed_at desc, name asc")
