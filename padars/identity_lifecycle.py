"""Keep framework rename/merge from re-keying persisted Padars identities."""

import frappe
from frappe import _


def _exists(doctype, filters):
	return frappe.db.table_exists(doctype) and bool(frappe.db.exists(doctype, filters))


def _lms_bound(doctype, name):
	return _exists("LMS Entity Mapping", {"local_doctype": doctype, "local_name": name}) or _exists(
		"LMS Sync Operation", {"target_doctype": doctype, "target_name": name})


def _bound(doctype, name):
	if _lms_bound(doctype, name):
		return True
	if doctype == "School":
		return any(_exists(child, {"school": name}) for child in (
			"School Curriculum Adoption", "School Course Offering", "Academic Assignment", "School Membership",
			"Student Identity", "Student Registration Application", "LMS Enrollment State",
			"School Assessment Scheme", "Report Card Publication", "Verified Guardian Access",
		))
	if doctype == "School Course Offering":
		return _exists("LMS Enrollment State", {"course_offering": name})
	if doctype == "User":
		return (_exists("Student Identity", {"user": name})
			or _exists("LMS Enrollment State", {"user": name})
			or _exists("Verified Guardian Access", {"user": name}))
	if doctype == "Student":
		if any(_exists(child, {"student": name}) for child in (
			"Student Identity", "Report Card Publication", "Verified Guardian Access", "Moodle Grade Snapshot",
			"Moodle Grade Review", "Attendance Evidence Proposal", "Attendance Evidence Review",
		)):
			return True
		user = frappe.db.get_value("Student", name, "user")
		return bool(user and _lms_bound("User", user))
	return False


def protect_bound_identity(doc, method=None, old=None, new=None, merge=False):
	old = old or doc.name
	if old == new and not merge:
		return
	# A merge into a protected target changes its academic relationships too.
	if _bound(doc.doctype, old) or (merge and new and _bound(doc.doctype, new)):
		frappe.throw(_("This record has persisted Padars identity or integration history. Its key cannot be renamed or merged without a reviewed identity migration. Edit its display name or label instead."), frappe.PermissionError)
