"""Reviewed, immutable report snapshots over authoritative Education results."""

import hashlib
import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from padars.grading import calculate_scheme
from padars.permissions import get_student_for_user, is_school_manager
from padars.school_context import get_primary_school


def _manager():
	school = get_primary_school(required=True)
	if not is_school_manager(school):
		frappe.throw(_("Only a School Manager can publish report cards."), frappe.PermissionError)
	return school


def _digest(value):
	return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


@frappe.whitelist()
def preview_report_card(enrollment, schemes):
	school = _manager()
	if isinstance(schemes, str):
		schemes = frappe.parse_json(schemes)
	if not isinstance(schemes, list) or not schemes or len(schemes) > 200 or any(not isinstance(name, str) for name in schemes) or len(schemes) != len(set(schemes)):
		frappe.throw(_("Select unique approved schemes covering the enrollment's courses."))
	enrollment = frappe.get_doc("Program Enrollment", enrollment)
	enrollment.check_permission("read")
	if enrollment.docstatus != 1 or enrollment.padars_school != school:
		frappe.throw(_("Choose a submitted enrollment for this School."))
	expected_courses = {row.course for row in enrollment.courses}
	if not expected_courses:
		frappe.throw(_("The enrollment must define its courses before publication."))
	cards, terms, seen = [], set(), set()
	for name in schemes:
		scheme = frappe.get_doc("School Assessment Scheme", name)
		scheme.check_permission("read")
		offering = frappe.get_doc("School Course Offering", scheme.course_offering)
		if (offering.school, offering.program, offering.academic_year) != (school, enrollment.program, enrollment.academic_year):
			frappe.throw(_("Every scheme must match the enrollment's school, program and year."))
		if offering.course in seen:
			frappe.throw(_("Choose exactly one approved scheme per enrolled course."))
		seen.add(offering.course)
		terms.add(scheme.academic_term or "")
		calculated = calculate_scheme(scheme.name, enrollment.student)
		for source in calculated["sources"]:
			result = frappe.get_doc("Assessment Result", source["result"])
			if not frappe.has_permission("Assessment Result", "approve_grade", doc=result):
				frappe.throw(_("Grade approval permission is required for every published result."), frappe.PermissionError)
		cards.append({"course": offering.course, "course_name": frappe.db.get_value("Course", offering.course, "course_name"), **calculated})
	if seen != expected_courses or len(terms) != 1:
		frappe.throw(_("Schemes must cover every enrolled course exactly once and use one term or annual period."))
	term = next(iter(terms))
	if enrollment.academic_term and term != enrollment.academic_term:
		frappe.throw(_("Term enrollment publication must use that enrollment's Academic Term."))
	snapshot = {"schema_version": 1, "school": school,
		"school_name": frappe.db.get_value("School", school, "school_name"),
		"student": enrollment.student, "student_name": enrollment.student_name,
		"enrollment": enrollment.name, "program": enrollment.program,
		"academic_year": enrollment.academic_year, "academic_term": term,
		"courses": sorted(cards, key=lambda card: card["course"])}
	return {"snapshot": snapshot, "digest": _digest(snapshot)}


class ReportCardPublication(Document):
	def validate(self):
		if not self.is_new() or not frappe.flags.get("padars_publishing_report_card"):
			frappe.throw(_("Report publications are immutable and created through the reviewed publication action."), frappe.PermissionError)
		if self.school != _manager():
			frappe.throw(_("The publication must belong to this School."))
		if _digest(json.loads(self.snapshot)) != self.snapshot_digest:
			frappe.throw(_("The report publication snapshot is invalid."))

	def on_trash(self):
		frappe.throw(_("Published report history cannot be deleted."), frappe.PermissionError)


@frappe.whitelist(methods=["POST"])
def publish_report_card(enrollment, schemes, expected_digest, correction_reason=None):
	_manager()
	enrollment_doc = frappe.get_doc("Program Enrollment", enrollment)
	enrollment_doc.check_permission("read")
	# Student-level locking also covers publication through distinct annual/term
	# enrollment records that resolve to the same report period.
	frappe.db.sql("select name from `tabStudent` where name=%s for update", enrollment_doc.student)
	if not frappe.db.sql("select name from `tabProgram Enrollment` where name=%s for update", enrollment):
		frappe.throw(_("Choose an existing Program Enrollment."))
	preview = preview_report_card(enrollment, schemes)
	if preview["digest"] != expected_digest:
		frappe.throw(_("Report sources changed after review. Preview again before publishing."), frappe.TimestampMismatchError)
	data = preview["snapshot"]
	scope = _digest({key: data[key] for key in ("school", "student", "program", "academic_year", "academic_term")})
	previous = frappe.db.sql("""select name, version, snapshot_digest from `tabReport Card Publication`
		where scope_key=%s order by version desc limit 1 for update""", scope, as_dict=True)
	if previous and previous[0].snapshot_digest == preview["digest"]:
		return {"name": previous[0].name, "version": previous[0].version}
	if previous and not (correction_reason or "").strip():
		frappe.throw(_("A correction reason is required for a new publication version."))
	version = int(previous[0].version) + 1 if previous else 1
	old_flag = frappe.flags.get("padars_publishing_report_card")
	frappe.flags.padars_publishing_report_card = True
	try:
		doc = frappe.get_doc({"doctype": "Report Card Publication", "school": data["school"],
			"student": data["student"], "program": data["program"], "academic_year": data["academic_year"],
			"academic_term": data["academic_term"], "enrollment": enrollment, "scope_key": scope,
			"version": version, "version_key": _digest({"scope": scope, "version": version}),
			"supersedes": previous[0].name if previous else None, "correction_reason": correction_reason,
			"snapshot": json.dumps(data, ensure_ascii=False, sort_keys=True), "snapshot_digest": preview["digest"],
			"published_by": frappe.session.user, "published_at": now_datetime()}).insert(ignore_permissions=True)
	finally:
		frappe.flags.padars_publishing_report_card = old_flag
	return {"name": doc.name, "version": version}


def _can_read(doc, user=None):
	user = user or frappe.session.user
	return doc.school == get_primary_school() and (is_school_manager(doc.school, user) or get_student_for_user(user) == doc.student)


def has_permission(doc, ptype, user=None, **kwargs):
	return ptype in {"read", "select", "print"} and _can_read(doc, user)


def query_conditions(user=None):
	user = user or frappe.session.user
	school = get_primary_school()
	base = f"`tabReport Card Publication`.school={frappe.db.escape(school or '')}"
	if is_school_manager(school, user):
		return base
	student = get_student_for_user(user)
	return f"({base}) and `tabReport Card Publication`.student={frappe.db.escape(student)}" if student else "1=0"


@frappe.whitelist()
def read_report_card(publication):
	doc = frappe.get_doc("Report Card Publication", publication)
	if not _can_read(doc):
		frappe.throw(_("This report card is not available to your account."), frappe.PermissionError)
	return {"name": doc.name, "version": doc.version, "published_at": str(doc.published_at),
		"supersedes": doc.supersedes, "snapshot": json.loads(doc.snapshot)}


@frappe.whitelist()
def list_report_cards(student=None, start=0, limit=20):
	school = get_primary_school(required=True)
	if not is_school_manager(school):
		own = get_student_for_user()
		if not own or (student and student != own):
			frappe.throw(_("Report cards are restricted to your own student account."), frappe.PermissionError)
		student = own
	if not student:
		frappe.throw(_("Select a student to view published report cards."))
	start, limit = int(start), int(limit)
	if start < 0 or limit < 1 or limit > 50:
		frappe.throw(_("Invalid report-card pagination."))
	return frappe.get_list("Report Card Publication", filters={"school": school, "student": student},
		fields=["name", "version", "program", "academic_year", "academic_term", "published_at"],
		order_by="published_at desc, version desc", start=start, page_length=limit)


def report_card_pdf(publication):
	doc = frappe.get_doc("Report Card Publication", publication)
	if not _can_read(doc):
		frappe.throw(_("This report card is not available to your account."), frappe.PermissionError)
	from frappe.utils.pdf import get_pdf
	template = frappe.get_doc("Print Format", "Padars Report Card").html
	body = frappe.render_template(template, {"doc": doc})
	html = '<!doctype html><html><head><meta charset="utf-8"><style>body{font-family:sans-serif;padding:24px}table{border-collapse:collapse;width:100%}th,td{border:1px solid #777;padding:8px;text-align:start}</style></head><body>' + body + '</body></html>'
	return get_pdf(html, options={"disable-javascript": None})


@frappe.whitelist()
def download_report_card(publication):
	frappe.response.filename = "report-card.pdf"
	frappe.response.filecontent = report_card_pdf(publication)
	frappe.response.type = "pdf"
