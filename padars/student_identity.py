"""Identity reservations and temporary credentials for imported students."""

import frappe
from frappe import _
from frappe.utils.password import check_password, update_password

from padars.registration import _identity_key, _phone
from padars.sensitive_requests import protect_registration_request


def reserve_provisional(national_id, phone, first_name=None, last_name=None):
	identity_key = _identity_key(national_id)
	phone = _phone(phone)
	existing = frappe.db.get_value("Student Identity", {"identity_key": identity_key},
		["name", "phone", "pending_activation", "user"], as_dict=True)
	if existing:
		if existing.phone != phone or not existing.pending_activation or existing.user:
			frappe.throw(_("This identity requires school review."))
		return frappe.get_doc("Student Identity", existing.name), False
	first_name = str(first_name or "").strip()
	last_name = str(last_name or "").strip()
	if len(first_name) > 140 or len(last_name) > 140:
		frappe.throw(_("Student names are too long."))
	identity = frappe.get_doc({"doctype": "Student Identity", "identity_key": identity_key,
		"phone": phone, "first_name": first_name, "last_name": last_name, "pending_activation": 1})
	identity.insert(ignore_permissions=True)
	update_password(identity.name, "0" + phone[3:], doctype="Student Identity", fieldname="provisional_password")
	return identity, True


def check_provisional_password(identity, password):
	return check_password(identity.name, str(password or ""), doctype="Student Identity",
		fieldname="provisional_password", delete_tracker_cache=False)


@frappe.whitelist(methods=["POST"])
@protect_registration_request
def reset_provisional_credentials(national_id, phone):
	"""After manual review, replace a pending identity's phone credential."""
	from padars.registration import _require_manager
	_require_manager()
	identity_key = _identity_key(national_id)
	phone = _phone(phone)
	name = frappe.db.get_value("Student Identity", {"identity_key": identity_key}, "name")
	if not name:
		frappe.throw(_("The identity requires school review."))
	frappe.db.sql("select name from `tabStudent Identity` where name=%s for update", name)
	identity = frappe.db.get_value("Student Identity", name, ["user", "student", "pending_activation"], as_dict=True)
	if not identity or identity.user or identity.student or not identity.pending_activation:
		frappe.throw(_("This account cannot be reset through provisional recovery."))
	frappe.db.set_value("Student Identity", name, "phone", phone)
	update_password(name, "0" + phone[3:], doctype="Student Identity", fieldname="provisional_password")
	frappe.cache.delete_value("padars:activation-otp:" + identity_key)
	return {"reset": True}


@frappe.whitelist(methods=["POST"])
@protect_registration_request
def reconcile_existing_student(student, national_id):
	"""Manually bind a known existing Student without changing its account."""
	from padars.registration import _require_manager
	_require_manager()
	doc = frappe.get_doc("Student", student)
	doc.check_permission("write")
	if not doc.user or not frappe.db.exists("User", doc.user) or doc.student_email_id.lower() != doc.user.lower():
		frappe.throw(_("The existing Student needs account review before identity reconciliation."))
	key = _identity_key(national_id)
	frappe.db.sql("select name from `tabStudent` where name=%s for update", student)
	existing = frappe.db.get_value("Student Identity", {"identity_key": key}, ["name", "student", "user"], as_dict=True)
	if existing:
		if existing.student == doc.name and existing.user == doc.user:
			return {"student": doc.name, "created": False}
		frappe.throw(_("This identity requires manual conflict review."))
	if frappe.db.exists("Student Identity", {"student": doc.name}) or frappe.db.exists("Student Identity", {"user": doc.user}):
		frappe.throw(_("This Student or User already has an identity reservation."))
	frappe.get_doc({"doctype": "Student Identity", "identity_key": key, "student": doc.name,
		"user": doc.user, "pending_activation": 0}).insert(ignore_permissions=True)
	return {"student": doc.name, "created": True}


def attach_matching_user(doc, method=None):
	"""Associate an existing reservation only when the explicit User matches."""
	if not doc.user:
		return
	identity = frappe.db.get_value("Student Identity", {"user": doc.user}, ["name", "student"], as_dict=True)
	if identity and not identity.student:
		frappe.db.set_value("Student Identity", identity.name, "student", doc.name)
