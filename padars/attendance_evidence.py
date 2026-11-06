"""Reviewed asynchronous activity evidence; Education owns official attendance."""

import hashlib
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, get_system_timezone, getdate, now_datetime, today

from padars.daily_operations import _require_attendance_action
from padars.integrations.moodle.grades import _can_read_offering
from padars.school_context import get_primary_school


def _hash(value):
	return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def _session(name, student=None, write=False):
	session = frappe.get_doc("Course Schedule", name)
	session.check_permission("read")
	if session.padars_school != get_primary_school() or not session.padars_course_offering:
		frappe.throw(_("Choose a session in this School with a Course Offering."), frappe.PermissionError)
	if not _can_read_offering(session.padars_course_offering):
		frappe.throw(_("This session's evidence is outside your teaching scope."), frappe.PermissionError)
	if student and (not frappe.db.exists("Student", {"name": student, "enabled": 1}) or not frappe.db.exists(
		"Student Group Student", {"parent": session.student_group, "student": student, "active": 1})):
		frappe.throw(_("The student must be active in this session's group."), frappe.PermissionError)
	if write:
		_require_attendance_action(session.student_group, session.schedule_date, session.name, student)
	return session


class SessionAttendancePolicy(Document):
	def validate(self):
		if self.is_new() and self.docstatus != 0:
			frappe.throw(_("New attendance policies must begin as drafts."))
		session = _session(self.course_schedule, write=True)
		if session.padars_session_mode != "Asynchronous":
			frappe.throw(_("Activity completion may count only for an explicitly Asynchronous session."))
		self.school, self.course_offering = session.padars_school, session.padars_course_offering
		source = frappe.get_doc("Moodle Learning Snapshot", self.source_snapshot)
		source.check_permission("read")
		if source.school != self.school or source.course_offering != self.course_offering:
			frappe.throw(_("The evidence catalogue must match this session's School and offering."))
		selected = frappe.parse_json(self.selected_activities)
		if not isinstance(selected, list) or not selected or len(selected) > 100 or any(type(value) is not int for value in selected) or len(set(selected)) != len(selected):
			frappe.throw(_("Select between one and 100 unique automatic-completion activities."))
		known = {row["cmid"]: row for row in json.loads(source.activities)}
		if any(cmid not in known or known[cmid]["tracking"] != 2 or known[cmid]["module"] == "plugnmeet" for cmid in selected):
			frappe.throw(_("Only discovered automatic-completion activities qualify. PlugNmeet requires session analytics."))
		self.selected_activities = json.dumps(sorted(selected))
		start, end, date = get_datetime(self.window_start), get_datetime(self.window_end), getdate(session.schedule_date)
		if start >= end or end - start > timedelta(days=14) or not start.date() <= date <= end.date():
			frappe.throw(_("Use a positive evidence window of at most fourteen days that includes the session date."))
		if not (self.approval_reason or "").strip():
			frappe.throw(_("Explain why these activities may count for this asynchronous session."))
		if self.rule_mode not in {"All selected activities", "Any selected activity"}:
			frappe.throw(_("Choose a supported activity evidence rule."))
		frappe.db.sql("select name from `tabCourse Schedule` where name=%s for update", session.name)
		if self.is_new():
			self.version = 1 + (frappe.db.sql("select max(version) from `tabSession Attendance Policy` where course_schedule=%s", session.name)[0][0] or 0)
			self.timezone = get_system_timezone()
			self.version_key = _hash([session.name, self.version])
		else:
			old = self.get_doc_before_save()
			if any(str(old.get(key)) != str(self.get(key)) for key in ("school", "course_schedule", "course_offering", "version", "timezone", "version_key")):
				frappe.throw(_("Saved policy session bindings and versions cannot change."))

	def before_submit(self):
		self.approved_by, self.approved_at = frappe.session.user, now_datetime()

	def before_cancel(self):
		frappe.throw(_("Approved policy history is retained. Create a new version instead."), frappe.PermissionError)

	def on_trash(self):
		if self.docstatus:
			frappe.throw(_("Approved policy history cannot be deleted."), frappe.PermissionError)


class AttendanceEvidenceProposal(Document):
	def validate(self):
		if not self.is_new() or not frappe.flags.get("padars_evidence_proposal"):
			frappe.throw(_("Evidence proposals are immutable evaluation records."), frappe.PermissionError)

	def on_trash(self):
		frappe.throw(_("Evidence history cannot be deleted."), frappe.PermissionError)


class AttendanceEvidenceReview(Document):
	def validate(self):
		if not self.is_new() or not frappe.flags.get("padars_evidence_review"):
			frappe.throw(_("Attendance evidence decisions are immutable service records."), frappe.PermissionError)

	def on_trash(self):
		frappe.throw(_("Evidence review history cannot be deleted."), frappe.PermissionError)


class AttendanceEvidenceUse(Document):
	def validate(self):
		if not self.is_new() or not frappe.flags.get("padars_evidence_review"):
			frappe.throw(_("Evidence consumption is immutable and service-created."), frappe.PermissionError)

	def on_trash(self):
		frappe.throw(_("Evidence consumption history cannot be deleted."), frappe.PermissionError)


def has_permission(doc, ptype, user=None, **kwargs):
	user = user or frappe.session.user
	if doc.school and doc.school != get_primary_school():
		return False
	if ptype in {"read", "select"}:
		return bool(doc.course_offering and _can_read_offering(doc.course_offering, user))
	if doc.doctype == "Session Attendance Policy" and ptype in {"create", "write", "submit", "delete"}:
		# Native role permissions plus the service validator's session action scope.
		return bool(frappe.has_permission("Course Schedule", "read", doc.course_schedule, user=user))
	return False


def _conditions(doctype, user=None):
	from padars.integrations.moodle.grades import query_conditions
	return query_conditions(user).replace("`tabMoodle Grade Snapshot`", f"`tab{doctype}`")


def policy_query_conditions(user=None):
	return _conditions("Session Attendance Policy", user)


def proposal_query_conditions(user=None):
	return _conditions("Attendance Evidence Proposal", user)


def review_query_conditions(user=None):
	return _conditions("Attendance Evidence Review", user)


def _evaluate(policy_name, student, snapshot_name):
	policy = frappe.get_doc("Session Attendance Policy", policy_name)
	policy.check_permission("read")
	if policy.docstatus != 1:
		frappe.throw(_("Choose an approved attendance policy."))
	session = _session(policy.course_schedule, student, write=True)
	if policy.school != session.padars_school or policy.course_offering != session.padars_course_offering:
		frappe.throw(_("The session academic binding changed. Approve a matching policy version."))
	if session.padars_session_mode != "Asynchronous":
		frappe.throw(_("This is no longer an asynchronous session; evidence requires manager review."))
	source = frappe.get_doc("Moodle Learning Snapshot", snapshot_name)
	source.check_permission("read")
	if source.school != policy.school or source.course_offering != policy.course_offering:
		frappe.throw(_("Evidence belongs to a different School or course."), frappe.PermissionError)
	latest_policy = frappe.db.get_value("Session Attendance Policy", {"course_schedule": session.name, "docstatus": 1}, "name", order_by="version desc")
	if latest_policy != policy.name:
		frappe.throw(_("Evaluate the latest approved policy version."))
	latest_source = frappe.db.get_value("Moodle Learning Snapshot", {"course_offering": policy.course_offering}, "name", order_by="observed_at desc, creation desc")
	op = frappe.db.get_value("LMS Sync Operation", {"operation_type": "Read Learning", "target_doctype": "School Course Offering",
		"target_name": policy.course_offering}, ["name", "state"], as_dict=True, order_by="creation desc")
	provenance = {"policy": policy.name, "policy_version": policy.version, "student": student,
		"source_snapshot": source.name, "source_digest": source.payload_digest, "session": session.name,
		"window_start": str(policy.window_start), "window_end": str(policy.window_end), "timezone": policy.timezone,
		"rule_mode": policy.rule_mode, "require_pass": bool(policy.require_pass), "evidence": [], "issues": []}
	unavailable = latest_source != source.name or not op or op.name != source.source_operation or op.state != "Succeeded"
	user = frappe.db.get_value("Student", student, "user")
	offering = frappe.db.get_value("School Course Offering", policy.course_offering, ["program", "academic_year"], as_dict=True)
	if not user or not frappe.db.exists("User", {"name": user, "enabled": 1}) or not frappe.db.exists("Program Enrollment", {
		"student": student, "program": offering.program, "academic_year": offering.academic_year,
		"padars_school": policy.school, "docstatus": 1}) or not frappe.db.exists("LMS Enrollment State", {
		"school": policy.school, "course_offering": policy.course_offering, "user": user,
		"role": "Student", "desired_state": "Enrolled", "remote_state": "Enrolled"}):
		unavailable = True
	identity = json.loads(source.identities or "{}").get(student)
	mapping = frappe.db.get_value("LMS Entity Mapping", identity["mapping"], ["status", "remote_id", "remote_context", "local_name"], as_dict=True) if identity else None
	if not mapping or mapping.status != "Active" or mapping.remote_id != identity["remote_user"] or mapping.remote_context != source.remote_context or mapping.local_name != frappe.db.get_value("Student", student, "user"):
		unavailable = True
	provenance["source_operation"] = source.source_operation
	provenance["source_observed_at"] = str(source.observed_at)
	provenance["source_unavailable"] = bool(unavailable)
	configured = {row["cmid"]: row for row in json.loads(frappe.db.get_value("Moodle Learning Snapshot", policy.source_snapshot, "activities"))}
	catalog = {row["cmid"]: row for row in json.loads(source.activities)}
	statuses = {row["cmid"]: row for row in json.loads(source.completions).get(student, [])}
	selected, qualified, incomplete = json.loads(policy.selected_activities), [], False
	for cmid in selected:
		item, status = catalog.get(cmid), statuses.get(cmid)
		if not item or not status or item["tracking"] != 2 or any(item[key] != configured[cmid][key] for key in ("module", "instance")):
			unavailable = True
			continue
		stamp = status["timecompleted"]
		when = datetime.fromtimestamp(stamp, ZoneInfo(policy.timezone)).replace(tzinfo=None) if stamp else None
		complete = status["state"] == 2 if policy.require_pass else status["state"] in {1, 2, 3}
		qualifies = bool(complete and when and get_datetime(policy.window_start) <= when <= get_datetime(policy.window_end))
		key = _hash([student, source.remote_context, cmid])
		consumed = frappe.db.get_value("Attendance Evidence Use", {"consumption_key": key}, "parent")
		used_session = frappe.db.get_value("Attendance Evidence Review", consumed, "course_schedule") if consumed else None
		if consumed and used_session != session.name:
			qualifies = False
			provenance["issues"].append(_("An activity completion has already counted for another session."))
		evidence = {"cmid": cmid, "module": item["module"], "state": status["state"], "completion_timestamp": stamp,
			"overridden": status["overridden"], "remote_context": source.remote_context, "source_mapping": identity,
			"qualifies": qualifies, "consumption_key": key, "already_used": bool(consumed)}
		provenance["evidence"].append(evidence)
		if qualifies:
			qualified.append(evidence)
		else:
			incomplete = True
	present = bool(qualified) and (policy.rule_mode == "Any selected activity" or not incomplete)
	if unavailable:
		state = "Evidence Unavailable"
	elif present:
		state = "Proposed Present"
	else:
		state = "Pending Evidence"
	# Missing/incomplete evidence is never an automatic absence.
	if frappe.db.exists("Student Attendance", {"student": student, "course_schedule": session.name, "docstatus": ["!=", 2]}):
		state = "Already Recorded"
	provenance["evaluation_state"] = state
	provenance["contributing"] = qualified[:1] if policy.rule_mode == "Any selected activity" else qualified
	return policy, session, source, provenance


@frappe.whitelist(methods=["POST"])
def evaluate_attendance_evidence(policy, student, source_snapshot):
	policy_doc, session, source, data = _evaluate(policy, student, source_snapshot)
	key = _hash(data)
	existing = frappe.db.get_value("Attendance Evidence Proposal", {"proposal_key": key}, "name")
	if existing:
		return {"name": existing, "state": data["evaluation_state"]}
	old = frappe.flags.get("padars_evidence_proposal")
	frappe.flags.padars_evidence_proposal = True
	try:
		proposal = frappe.get_doc({"doctype": "Attendance Evidence Proposal", "school": policy_doc.school,
			"course_schedule": session.name, "course_offering": policy_doc.course_offering, "student": student,
			"policy": policy_doc.name, "source_snapshot": source.name, "evaluation_state": data["evaluation_state"],
			"evaluated_at": now_datetime(), "provenance": json.dumps(data, sort_keys=True), "proposal_key": key}).insert(ignore_permissions=True)
	finally:
		frappe.flags.padars_evidence_proposal = old
	return {"name": proposal.name, "state": proposal.evaluation_state}


@frappe.whitelist(methods=["POST"])
def confirm_attendance_evidence(proposal, reason):
	if not isinstance(reason, str) or not reason.strip():
		frappe.throw(_("Record the teacher's evidence review reason."))
	doc = frappe.get_doc("Attendance Evidence Proposal", proposal)
	doc.check_permission("read")
	session = _session(doc.course_schedule, doc.student, write=True)
	# Same order as source capture; Student lock also serializes evidence use across sessions.
	frappe.db.sql("select name from `tabSchool Course Offering` where name=%s for update", doc.course_offering)
	frappe.db.sql("select name from `tabStudent` where name=%s for update", doc.student)
	frappe.db.sql("select name from `tabCourse Schedule` where name=%s for update", session.name)
	previous = frappe.db.get_value("Attendance Evidence Review", {"review_key": f"proposal:{doc.name}"}, ["name", "attendance"], as_dict=True)
	if previous:
		if frappe.db.get_value("Student Attendance", previous.attendance, ["status", "docstatus"]) != ("Present", 1):
			frappe.throw(_("This evidence attendance was subsequently overridden. Review the official record."))
		return {"review": previous.name, "attendance": previous.attendance}
	data = _evaluate(doc.policy, doc.student, doc.source_snapshot)[3]
	if _hash(data) != doc.proposal_key:
		frappe.throw(_("Evidence, policy or consumption changed. Evaluate again."), frappe.TimestampMismatchError)
	if data["evaluation_state"] != "Proposed Present":
		frappe.throw(_("Only a reviewed Proposed Present can confirm attendance."))
	if getdate(session.schedule_date) > getdate(today()):
		frappe.throw(_("Future attendance cannot be confirmed."))
	existing = frappe.get_all("Student Attendance", filters={"student": doc.student, "course_schedule": session.name, "docstatus": ["!=", 2]}, pluck="name")
	if existing:
		frappe.throw(_("Attendance already exists. Use the official record's manual correction action."))
	frappe.db.savepoint("padars_confirm_evidence")
	old = frappe.flags.get("padars_evidence_review")
	try:
		attendance = frappe.get_doc({"doctype": "Student Attendance", "student": doc.student,
			"student_group": session.student_group, "course_schedule": session.name, "date": session.schedule_date, "status": "Present"}).insert()
		attendance.submit()
		frappe.flags.padars_evidence_review = True
		review = frappe.get_doc({"doctype": "Attendance Evidence Review", "school": doc.school,
			"course_schedule": session.name, "course_offering": doc.course_offering, "student": doc.student,
			"proposal": doc.name, "attendance": attendance.name, "decision": "Evidence Confirmed", "confirmed_status": "Present",
			"reviewed_by": frappe.session.user, "reviewed_at": now_datetime(), "reason": reason.strip(),
			"review_key": f"proposal:{doc.name}", "evidence": [{"consumption_key": row["consumption_key"],
				"cmid": row["cmid"], "completion_timestamp": row["completion_timestamp"], "remote_context": row["remote_context"]}
				for row in data["contributing"] if not row["already_used"]]}).insert(ignore_permissions=True)
	except Exception:
		frappe.db.rollback(save_point="padars_confirm_evidence")
		raise
	finally:
		frappe.flags.padars_evidence_review = old
	return {"review": review.name, "attendance": attendance.name}


def protect_evidence_attendance(doc, method=None):
	if not frappe.db.table_exists("Attendance Evidence Review"):
		return
	old = doc.get_doc_before_save()
	changed = old and (old.status != doc.status or old.padars_late_minutes != doc.padars_late_minutes)
	leave_update = frappe.flags.get("padars_leave_attendance_update") or frappe.flags.get("padars_leave_attendance_cancel")
	if leave_update and old and leave_update in {old.leave_application, doc.leave_application}:
		return  # Existing validated leave workflow retains its own status/approval history.
	if changed and frappe.db.exists("Attendance Evidence Review", {"attendance": doc.name}) and frappe.flags.get("padars_evidence_override") != doc.name:
		frappe.throw(_("Use Override Evidence Attendance and record a reason."), frappe.PermissionError)


@frappe.whitelist(methods=["POST"])
def override_evidence_attendance(attendance, status, reason, late_minutes=0):
	if status not in {"Present", "Absent"} or not isinstance(reason, str) or not reason.strip():
		frappe.throw(_("Choose Present or Absent and record the correction reason."))
	late_minutes = int(late_minutes)
	if not 0 <= late_minutes <= 1440 or (status != "Present" and late_minutes):
		frappe.throw(_("Late minutes must be 0–1440 and require Present status."))
	doc = frappe.get_doc("Student Attendance", attendance)
	session = _session(doc.course_schedule, doc.student, write=True)
	frappe.db.sql("select name from `tabStudent` where name=%s for update", doc.student)
	doc = frappe.get_doc("Student Attendance", attendance, for_update=True)
	doc.check_permission("write")
	if doc.docstatus != 1 or doc.leave_application or not frappe.db.exists("Attendance Evidence Review", {"attendance": doc.name}):
		frappe.throw(_("Select a submitted evidence attendance record without approved leave."))
	previous, previous_late = doc.status, int(doc.padars_late_minutes or 0)
	if previous == status and previous_late == late_minutes:
		return {"attendance": doc.name, "status": status}
	frappe.db.savepoint("padars_override_evidence")
	old_review, old_override = frappe.flags.get("padars_evidence_review"), frappe.flags.get("padars_evidence_override")
	try:
		frappe.flags.padars_evidence_override = doc.name
		doc.status = status
		doc.padars_late_minutes = late_minutes
		doc.save()
		frappe.flags.padars_evidence_review = True
		frappe.get_doc({"doctype": "Attendance Evidence Review", "school": session.padars_school,
			"course_schedule": session.name, "course_offering": session.padars_course_offering, "student": doc.student,
			"attendance": doc.name, "decision": "Manual Override", "previous_status": previous, "confirmed_status": status,
			"previous_late_minutes": previous_late, "confirmed_late_minutes": late_minutes,
			"reviewed_by": frappe.session.user, "reviewed_at": now_datetime(), "reason": reason.strip(),
			"review_key": f"override:{frappe.generate_hash(length=32)}"}).insert(ignore_permissions=True)
	except Exception:
		frappe.db.rollback(save_point="padars_override_evidence")
		raise
	finally:
		frappe.flags.padars_evidence_review, frappe.flags.padars_evidence_override = old_review, old_override
	return {"attendance": doc.name, "status": doc.status}


@frappe.whitelist()
def get_session_evidence_context(course_schedule, source_snapshot=None):
	from padars.daily_operations import _attendance_doc
	session = _session(course_schedule)
	students = frappe.get_all("Student Group Student", filters={"parent": session.student_group, "active": 1},
		fields=["student", "student_name"], order_by="group_roll_number asc", page_length=201)
	can_manage = bool(students and frappe.has_permission("Student Attendance", "manage_attendance",
		doc=_attendance_doc(session.student_group, session.schedule_date, session.name, students[0].student)))
	if not can_manage:
		return {"can_manage": False}
	if len(students) > 200:
		frappe.throw(_("This evidence review supports up to 200 active students per session."))
	latest = frappe.db.get_value("Moodle Learning Snapshot", {"course_offering": session.padars_course_offering}, "name", order_by="observed_at desc, creation desc")
	name = source_snapshot or latest
	activities = []
	if name:
		source = frappe.get_doc("Moodle Learning Snapshot", name)
		source.check_permission("read")
		if source.school != session.padars_school or source.course_offering != session.padars_course_offering:
			frappe.throw(_("The source must belong to the session's School and offering."), frappe.PermissionError)
		activities = [item for item in json.loads(source.activities) if item["tracking"] == 2 and item["module"] != "plugnmeet"]
	return {"can_manage": True, "school": session.padars_school, "course_offering": session.padars_course_offering,
		"source_snapshot": name, "latest_source": latest, "activities": activities, "students": students,
		"policy": frappe.db.get_value("Session Attendance Policy", {"course_schedule": session.name, "docstatus": 1}, "name", order_by="version desc"),
		"window_start": f"{session.schedule_date} 00:00:00", "window_end": f"{session.schedule_date} 23:59:59"}


@frappe.whitelist()
def get_attendance_evidence_context(attendance):
	from padars.daily_operations import _attendance_doc
	doc = frappe.get_doc("Student Attendance", attendance)
	doc.check_permission("read")
	session = _session(doc.course_schedule)
	is_evidence = bool(frappe.db.exists("Attendance Evidence Review", {"attendance": doc.name}))
	return {"is_evidence": is_evidence, "can_override": bool(is_evidence and doc.docstatus == 1 and not doc.leave_application
		and frappe.has_permission("Student Attendance", "write", doc)
		and frappe.has_permission("Student Attendance", "manage_attendance", _attendance_doc(session.student_group, session.schedule_date, session.name, doc.student)))}
