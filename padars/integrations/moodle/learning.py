"""Teacher-published activities and scoped completion projections, never attendance."""

import hashlib
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_system_timezone, now_datetime, strip_html

from padars.integrations.moodle.grades import _can_read_offering, query_conditions, resolve_course_roster
from padars.school_context import get_primary_school
from padars.permissions_site import get_teacher_instructors


class MoodleLearningSnapshot(Document):
	def validate(self):
		if not self.is_new() or not frappe.flags.get("padars_learning_capture"):
			frappe.throw(_("Learning sources are immutable service records."), frappe.PermissionError)

	def on_trash(self):
		frappe.throw(_("Learning source history cannot be deleted."), frappe.PermissionError)


class CourseActivitySelection(Document):
	def validate(self):
		if not self.is_new() or not frappe.flags.get("padars_learning_publication"):
			frappe.throw(_("Activity selections are versioned through the teacher publication action."), frappe.PermissionError)

	def on_trash(self):
		frappe.throw(_("Activity publication history cannot be deleted."), frappe.PermissionError)


def has_permission(doc, ptype, user=None, **kwargs):
	return ptype in {"read", "select"} and doc.school == get_primary_school() and _can_read_offering(doc.course_offering, user)


def snapshot_query_conditions(user=None):
	return query_conditions(user).replace("`tabMoodle Grade Snapshot`", "`tabMoodle Learning Snapshot`")


def selection_query_conditions(user=None):
	return query_conditions(user).replace("`tabMoodle Grade Snapshot`", "`tabCourse Activity Selection`")


def clean_catalog(sections):
	if not isinstance(sections, list) or len(sections) > 500:
		frappe.throw(_("The course activity response exceeds the supported shape or limit."))
	result, seen = [], set()
	for section in sections:
		for module in section.get("modules", []):
			cmid, tracking = int(module.get("id") or 0), int(module.get("completion") or 0)
			kind = str(module.get("modname") or "")
			if cmid <= 0 or cmid in seen or tracking not in {0, 1, 2} or not re.fullmatch(r"[a-z][a-z0-9_]*", kind):
				frappe.throw(_("Moodle returned invalid or duplicate activity identifiers."))
			seen.add(cmid)
			dates = [{"label": strip_html(str(row.get("label") or ""))[:100], "timestamp": int(row.get("timestamp") or 0)}
				for row in module.get("dates", [])[:20] if 0 < int(row.get("timestamp") or 0) < 20000000000]
			result.append({"cmid": cmid, "name": strip_html(str(module.get("name") or ""))[:255],
				"module": kind, "instance": int(module.get("instance") or 0), "tracking": tracking,
				"visible": bool(module.get("visible", False)) and bool(section.get("visible", False)),
				"restricted": bool(module.get("availability") or module.get("availabilityinfo") or section.get("availabilityinfo")),
				"dates": dates, "attendance_eligible": False})
	if len(result) > 500:
		frappe.throw(_("The supported course activity limit is 500."))
	return sorted(result, key=lambda row: row["cmid"])


def clean_completions(statuses, catalog):
	if not isinstance(statuses, list) or len(statuses) > 500:
		frappe.throw(_("The completion response exceeds the supported shape or limit."))
	known, seen, result = {row["cmid"]: row for row in catalog}, set(), []
	for row in statuses:
		cmid, state, tracking = int(row.get("cmid") or 0), int(row.get("state", -1)), int(row.get("tracking") or 0)
		if cmid not in known or cmid in seen or state not in {0, 1, 2, 3} or tracking not in {1, 2}:
			frappe.throw(_("Moodle completion identifiers, tracking or state could not be verified."))
		item = known[cmid]
		if tracking != item["tracking"] or row.get("modname") != item["module"] or int(row.get("instance") or 0) != item["instance"]:
			frappe.throw(_("An activity changed during completion retrieval. Retry discovery."))
		timestamp = int(row.get("timecompleted") or 0)
		if timestamp < 0 or timestamp >= 20000000000:
			frappe.throw(_("Moodle returned an invalid completion timestamp."))
		seen.add(cmid)
		result.append({"cmid": cmid, "state": state, "tracking": tracking,
			"timecompleted": timestamp, "overridden": bool(row.get("overrideby"))})
	return sorted(result, key=lambda row: row["cmid"])


@frappe.whitelist(methods=["POST"])
def request_learning_discovery(course_offering):
	from padars.integrations.moodle.service import request_sync_operation
	if not _can_read_offering(course_offering):
		frappe.throw(_("Only assigned teaching staff can fetch this course's learning data."), frappe.PermissionError)
	offering = frappe.get_doc("School Course Offering", course_offering)
	if offering.status == "Archived":
		frappe.throw(_("Archived offerings cannot fetch current learning data."))
	frappe.db.sql("select name from `tabSchool Course Offering` where name=%s for update", offering.name)
	pending = frappe.db.get_value("LMS Sync Operation", {"operation_type": "Read Learning",
		"target_doctype": "School Course Offering", "target_name": offering.name,
		"state": ["in", ["Pending", "Queued", "Running"]]}, "name")
	if pending:
		return {"operation": pending}
	op = request_sync_operation(offering.school, "Read Learning", "School Course Offering", offering.name,
		f"learning:{frappe.generate_hash(length=32)}")
	return {"operation": op.name}


def capture_learning(operation, adapter):
	offering, school, tenant, course, roster = resolve_course_roster(operation)
	if frappe.db.exists("Moodle Learning Snapshot", {"source_operation": operation.name}):
		return {"captured": 1}
	catalog = clean_catalog(adapter.read_course_activities(school, course))
	completions = {student: clean_completions(adapter.read_activity_completions(school, course, user), catalog)
		for student, user in roster}
	payload = json.dumps({"activities": catalog, "completions": completions}, sort_keys=True)
	old_flag = frappe.flags.get("padars_learning_capture")
	frappe.flags.padars_learning_capture = True
	try:
		frappe.get_doc({"doctype": "Moodle Learning Snapshot", "school": school.name,
			"course_offering": offering.name, "source_operation": operation.name,
			"observed_at": now_datetime(), "remote_context": tenant.remote_context, "remote_course": course.remote_id,
			"activities": json.dumps(catalog, sort_keys=True), "completions": json.dumps(completions, sort_keys=True),
			"payload_digest": hashlib.sha256(payload.encode()).hexdigest()}).insert(ignore_permissions=True)
	finally:
		frappe.flags.padars_learning_capture = old_flag
	return {"captured": len(roster)}


def _publication_allowed(offering):
	assigned_teacher = (offering.instructor in get_teacher_instructors(school=offering.school)
		and frappe.db.get_value("Instructor", offering.instructor, "padars_user") == frappe.session.user)
	return bool(_can_read_offering(offering.name) and (assigned_teacher or frappe.has_permission("School Course Offering", "write", offering)))


@frappe.whitelist()
def get_activity_publication_context(source_snapshot):
	snapshot = frappe.get_doc("Moodle Learning Snapshot", source_snapshot)
	snapshot.check_permission("read")
	offering = frappe.get_doc("School Course Offering", snapshot.course_offering)
	previous = frappe.get_list("Course Activity Selection", filters={"course_offering": offering.name},
		fields=["selected_modules"], order_by="version desc", page_length=1)
	return {"can_publish": offering.status != "Archived" and _publication_allowed(offering),
		"selected": json.loads(previous[0].selected_modules) if previous else []}


@frappe.whitelist(methods=["POST"])
def publish_activity_selection(source_snapshot, selected_modules, reason):
	snapshot = frappe.get_doc("Moodle Learning Snapshot", source_snapshot)
	snapshot.check_permission("read")
	# Read access includes grade-entry staff. Publishing requires course editing authority.
	offering = frappe.get_doc("School Course Offering", snapshot.course_offering)
	if not _publication_allowed(offering):
		frappe.throw(_("Only the assigned teacher or authorized academic editor may publish activities."), frappe.PermissionError)
	if offering.status == "Archived":
		frappe.throw(_("Archived offerings cannot publish current activities."))
	if not isinstance(reason, str) or not reason.strip():
		frappe.throw(_("Record why these activity titles and dates may be shared with students and verified guardians."))
	selected = frappe.parse_json(selected_modules) if isinstance(selected_modules, str) else selected_modules
	if not isinstance(selected, list) or len(selected) > 500 or any(type(value) is not int for value in selected) or len(set(selected)) != len(selected):
		frappe.throw(_("Choose unique discovered activity identifiers."))
	known = {row["cmid"] for row in json.loads(snapshot.activities)}
	if not set(selected).issubset(known):
		frappe.throw(_("Only activities in this course's source snapshot can be selected."))
	frappe.db.sql("select name from `tabSchool Course Offering` where name=%s for update", offering.name)
	latest = frappe.db.get_value("Moodle Learning Snapshot", {"course_offering": offering.name}, "name", order_by="observed_at desc, creation desc")
	operation = frappe.db.get_value("LMS Sync Operation", {"operation_type": "Read Learning",
		"target_doctype": "School Course Offering", "target_name": offering.name}, ["name", "state"], as_dict=True, order_by="creation desc")
	if selected and (latest != snapshot.name or not operation or operation.name != snapshot.source_operation or operation.state != "Succeeded"):
		frappe.throw(_("Fetch current successful learning data before publishing activities."))
	previous = frappe.db.get_value("Course Activity Selection", {"course_offering": offering.name},
		["name", "version", "source_snapshot", "selected_modules"], as_dict=True, order_by="version desc")
	encoded = json.dumps(sorted(selected))
	if previous and previous.source_snapshot == snapshot.name and previous.selected_modules == encoded:
		return {"name": previous.name, "version": previous.version}
	version = previous.version + 1 if previous else 1
	old_flag = frappe.flags.get("padars_learning_publication")
	frappe.flags.padars_learning_publication = True
	try:
		selection = frappe.get_doc({"doctype": "Course Activity Selection", "school": snapshot.school,
			"course_offering": offering.name, "source_snapshot": snapshot.name, "version": version,
			"selected_modules": encoded, "published_by": frappe.session.user, "published_at": now_datetime(),
			"publication_reason": reason.strip(), "selection_key": hashlib.sha256(f"{offering.name}\0{version}".encode()).hexdigest()}).insert(ignore_permissions=True)
	finally:
		frappe.flags.padars_learning_publication = old_flag
	return {"name": selection.name, "version": selection.version}


def _learning_for_student(student, offerings):
	"""Called only after the portal has authorized the student and active courses."""
	result = []
	for offering in offerings[:100]:
		selection = frappe.db.get_value("Course Activity Selection", {"course_offering": offering, "school": get_primary_school()},
			["source_snapshot", "selected_modules", "version"], as_dict=True, order_by="version desc")
		if not selection:
			continue
		selected = json.loads(selection.selected_modules)
		if not selected:
			continue
		published = frappe.get_doc("Moodle Learning Snapshot", selection.source_snapshot)
		latest = frappe.db.get_value("Moodle Learning Snapshot", {"course_offering": offering}, "name", order_by="observed_at desc, creation desc")
		snapshot = frappe.get_doc("Moodle Learning Snapshot", latest)
		operation = frappe.db.get_value("LMS Sync Operation", {"operation_type": "Read Learning", "target_doctype": "School Course Offering",
			"target_name": offering}, ["name", "state"], as_dict=True, order_by="creation desc")
		stale = not operation or operation.name != snapshot.source_operation or operation.state != "Succeeded"
		current = {row["cmid"]: row for row in json.loads(snapshot.activities)}
		completion = {row["cmid"]: row for row in json.loads(snapshot.completions).get(student, [])}
		for item in json.loads(published.activities):
			if item["cmid"] not in selected:
				continue
			active = current.get(item["cmid"])
			status = completion.get(item["cmid"])
			matches = active and all(active[key] == item[key] for key in ("module", "instance")) and published.remote_context == snapshot.remote_context and published.remote_course == snapshot.remote_course
			metadata_changed = not matches or any(active[key] != item[key] for key in ("name", "dates"))
			state = status["state"] if matches and status and not stale else None
			result.append({"course_offering": offering, "cmid": item["cmid"], "name": item["name"], "module": item["module"],
				"dates": [{"label": row["label"], "date": str(datetime.fromtimestamp(row["timestamp"], ZoneInfo(get_system_timezone())))} for row in item["dates"]] if not metadata_changed else [],
				"state": state, "observed_at": str(snapshot.observed_at), "unavailable": state is None,
				"purpose": "Engagement only", "metadata_changed": metadata_changed, "selection_version": selection.version})
	return result
