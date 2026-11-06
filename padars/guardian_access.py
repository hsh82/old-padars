"""Verified school decisions over native Education guardian relationships."""

import hashlib

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from padars.permissions import is_school_manager
from padars.school_context import get_primary_school


def _manager():
	school = get_primary_school(required=True)
	if not is_school_manager(school):
		frappe.throw(_("Only a School Manager can verify guardian access."), frappe.PermissionError)
	return school


def _key(student, guardian, user, row):
	return hashlib.sha256(f"{student}\0{guardian}\0{user}\0{row}".encode()).hexdigest()


class VerifiedGuardianAccess(Document):
	def validate(self):
		if not frappe.flags.get("padars_guardian_access_service"):
			frappe.throw(_("Guardian access is managed through school verification actions."), frappe.PermissionError)
		old = self.get_doc_before_save()
		if not old:
			if self.school != _manager() or self.status != "Active" or not self.verification_reason:
				frappe.throw(_("A new guardian grant requires school verification."))
			self.active_key = _key(self.student, self.guardian, self.user, self.relationship_row)
		else:
			fixed = ("school", "student", "guardian", "user", "relationship_row", "verified_by", "verified_at", "verification_reason")
			if any(str(old.get(field) or "") != str(self.get(field) or "") for field in fixed):
				frappe.throw(_("Verified guardian bindings and history cannot be changed."))
			if old.status != "Active" or self.status != "Revoked" or not self.revocation_reason:
				frappe.throw(_("Guardian grants may only transition from Active to Revoked."))
			self.active_key = None

	def on_trash(self):
		frappe.throw(_("Guardian verification history cannot be deleted."), frappe.PermissionError)


def _valid(grant):
	if grant.status != "Active" or grant.school != get_primary_school():
		return False
	if not frappe.db.exists("User", {"name": grant.user, "enabled": 1}) or "Padars Guardian" not in frappe.get_roles(grant.user):
		return False
	if not frappe.db.exists("Student", {"name": grant.student, "enabled": 1}):
		return False
	guardian = frappe.db.get_value("Guardian", grant.guardian, ["user", "email_address"], as_dict=True)
	if not guardian or guardian.user != grant.user or (guardian.email_address or "").strip().lower() != grant.user.lower():
		return False
	return bool(frappe.db.exists("Student Guardian", {"name": grant.relationship_row,
		"parent": grant.student, "parenttype": "Student", "guardian": grant.guardian}))


def linked_students(user=None):
	user = user or frappe.session.user
	if user == "Guest" or "Padars Guardian" not in frappe.get_roles(user):
		return []
	if not frappe.db.table_exists("Verified Guardian Access"):
		return []
	grants = frappe.get_all("Verified Guardian Access", filters={"user": user, "status": "Active"},
		fields=["school", "student", "guardian", "user", "relationship_row", "status"])
	return sorted({grant.student for grant in grants if _valid(grant)})


@frappe.whitelist()
def list_linked_students():
	return [{"student": name, "student_name": frappe.db.get_value("Student", name, "student_name")} for name in linked_students()]


@frappe.whitelist(methods=["POST"])
def verify_guardian_access(student, guardian, user=None, reason=None):
	school = _manager()
	if not isinstance(reason, str) or not reason.strip():
		frappe.throw(_("Record why the school has verified this guardian relationship."))
	student_doc = frappe.get_doc("Student", student)
	student_doc.check_permission("write")
	frappe.db.sql("select name from `tabStudent` where name=%s for update", student)
	rows = frappe.get_all("Student Guardian", filters={"parent": student, "parenttype": "Student", "guardian": guardian}, pluck="name")
	if len(rows) != 1 or not student_doc.enabled:
		frappe.throw(_("Select a unique native guardian relationship on an enabled Student."))
	guardian_doc = frappe.get_doc("Guardian", guardian)
	guardian_doc.check_permission("write")
	user = user or guardian_doc.user or (guardian_doc.email_address or "").strip().lower()
	if not user:
		frappe.throw(_("The Guardian needs an email address for their account."))
	if not frappe.db.exists("User", user):
		if user != (guardian_doc.email_address or "").strip().lower():
			frappe.throw(_("A new guardian account must match the Guardian email address."))
		account = frappe.get_doc({"doctype": "User", "email": user, "first_name": guardian_doc.guardian_name,
			"user_type": "Website User", "enabled": 1, "send_welcome_email": 0,
			"roles": [{"role": "Padars Guardian"}]}).insert(ignore_permissions=True)
	else:
		account = frappe.get_doc("User", user)
	if not account.enabled or user == "Guest" or (guardian_doc.email_address or "").strip().lower() != account.name.lower():
		frappe.throw(_("The enabled User must match the Guardian email address."))
	if guardian_doc.user and guardian_doc.user != account.name:
		frappe.throw(_("Review the Guardian's existing User binding before replacing it."))
	if guardian_doc.user != account.name:
		guardian_doc.user = account.name
		guardian_doc.save()
	# This service grants only the fixed portal-only guardian role after manager verification.
	from padars.role_profiles import grant_fixed_role
	grant_fixed_role(account, "Padars Guardian")
	key = _key(student, guardian, user, rows[0])
	existing = frappe.db.get_value("Verified Guardian Access", {"active_key": key}, "name")
	if existing:
		return {"name": existing, "status": "Active", "user": account.name}
	old_flag = frappe.flags.get("padars_guardian_access_service")
	frappe.flags.padars_guardian_access_service = True
	try:
		doc = frappe.get_doc({"doctype": "Verified Guardian Access", "school": school,
			"student": student, "guardian": guardian, "user": user, "relationship_row": rows[0],
			"status": "Active", "verification_reason": reason.strip(), "verified_by": frappe.session.user,
			"verified_at": now_datetime()}).insert(ignore_permissions=True)
	finally:
		frappe.flags.padars_guardian_access_service = old_flag
	return {"name": doc.name, "status": doc.status, "user": account.name}


def _revoke(grant, reason):
	old_flag = frappe.flags.get("padars_guardian_access_service")
	frappe.flags.padars_guardian_access_service = True
	try:
		grant.status = "Revoked"
		grant.revoked_by = frappe.session.user
		grant.revoked_at = now_datetime()
		grant.revocation_reason = reason
		grant.save(ignore_permissions=True)
	finally:
		frappe.flags.padars_guardian_access_service = old_flag


@frappe.whitelist(methods=["POST"])
def revoke_guardian_access(access, reason):
	school = _manager()
	if not isinstance(reason, str) or not reason.strip():
		frappe.throw(_("A revocation reason is required."))
	grant = frappe.get_doc("Verified Guardian Access", access, for_update=True)
	if grant.school != school:
		frappe.throw(_("This grant belongs to another School."), frappe.PermissionError)
	if grant.status == "Active":
		_revoke(grant, reason.strip())
	return {"name": grant.name, "status": grant.status}


def revoke_changed_relationships(doc, method=None):
	if not frappe.db.table_exists("Verified Guardian Access"):
		return
	filters = {"status": "Active", "student" if doc.doctype == "Student" else "guardian": doc.name}
	for name in frappe.get_all("Verified Guardian Access", filters=filters, pluck="name"):
		grant = frappe.get_doc("Verified Guardian Access", name, for_update=True)
		if grant.status == "Active" and not _valid(grant):
			_revoke(grant, _("The native guardian relationship or account binding changed."))
