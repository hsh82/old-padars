"""Public application and staff approval without granting applicant access."""

import base64
import hashlib
import hmac
import secrets

import frappe
import pyotp
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import validate_email_address
from frappe.utils.password import get_decrypted_password

from padars.registration import _identity_key, _phone, _prepare, _register, _require_manager, normalize_national_id
from padars.student_activation import _sms_configured, _sms_required


def _digest(value):
	return hmac.new(frappe.local.conf.encryption_key.encode(), value.encode(), hashlib.sha256).hexdigest()


def _attempt(identity_key):
	key = "padars:application-attempts:" + identity_key
	count = frappe.cache.incr(key)
	if count == 1:
		frappe.cache.expire(key, 3600)
	if count > 10:
		frappe.throw(_("Too many requests. Try again later."), frappe.AuthenticationError)


def _otp_key(identity_key, phone):
	return "padars:application-otp:" + _digest(identity_key + ":" + phone)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=3600)
def send_code(national_id, phone):
	identity_key = _identity_key(national_id)
	phone = _phone(phone)
	_attempt(identity_key)
	if not _sms_required() or not _sms_configured():
		frappe.throw(_("SMS verification is unavailable. Contact the school."))
	from frappe.twofactor import send_token_via_sms
	secret = base64.b32encode(secrets.token_bytes(20)).decode("ascii")
	counter = secrets.randbelow(2**31)
	otp = pyotp.HOTP(secret).at(counter)
	frappe.cache.set_value(_otp_key(identity_key, phone), _digest("application:" + identity_key + ":" + otp), expires_in_sec=300)
	frappe.db.after_commit.add(lambda: send_token_via_sms(secret, token=counter, phone_no=phone))
	return {"queued": True}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=3600)
def submit(first_name, national_id, phone, email, guardian_consent, last_name=None, otp=None):
	data = _prepare({"first_name": first_name, "last_name": last_name, "national_id": national_id, "phone": phone, "email": email})
	_attempt(data["identity_key"])
	if frappe.utils.cint(guardian_consent) != 1:
		frappe.throw(_("An adult or guardian must consent to the application."))
	verified = _sms_required()
	if verified:
		stored = frappe.cache.get_value(_otp_key(data["identity_key"], data["phone"]))
		current = _digest("application:" + data["identity_key"] + ":" + str(otp or ""))
		if not stored or not hmac.compare_digest(str(stored), current):
			frappe.throw(_("Invalid or expired verification code."), frappe.AuthenticationError)
	if frappe.db.exists("Student Registration Application", {"identity_key": data["identity_key"]}):
		frappe.throw(_("This application requires school review."))
	token = secrets.token_urlsafe(32)
	doc = frappe.get_doc({"doctype": "Student Registration Application", "first_name": data["first_name"],
		"last_name": data["last_name"], "phone": data["phone"], "email": data["email"],
		"national_id": normalize_national_id(national_id), "identity_key": data["identity_key"],
		"status_token_hash": _digest("application-status:" + token), "guardian_consent": 1,
		"phone_verified": verified, "status": "Submitted"}).insert(ignore_permissions=True)
	if verified:
		frappe.cache.delete_value(_otp_key(data["identity_key"], data["phone"]))
	return {"status_token": token, "status": doc.status}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=60, seconds=3600)
def status(status_token):
	if not isinstance(status_token, str) or len(status_token) > 128:
		frappe.throw(_("Invalid application reference."), frappe.AuthenticationError)
	state = frappe.db.get_value("Student Registration Application", {"status_token_hash": _digest("application-status:" + status_token)}, "status")
	if not state:
		frappe.throw(_("Invalid application reference."), frappe.AuthenticationError)
	return {"status": state}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=3600)
def update_details(status_token, first_name, email, last_name=None):
	if not isinstance(status_token, str) or len(status_token) > 128:
		frappe.throw(_("Invalid application reference."), frappe.AuthenticationError)
	name = frappe.db.get_value("Student Registration Application", {"status_token_hash": _digest("application-status:" + status_token)}, "name")
	if not name:
		frappe.throw(_("Invalid application reference."), frappe.AuthenticationError)
	frappe.db.sql("select name from `tabStudent Registration Application` where name=%s for update", name)
	if frappe.db.get_value("Student Registration Application", name, "status") != "Submitted":
		frappe.throw(_("This application can no longer be edited."))
	first_name = str(first_name or "").strip()
	email = str(email or "").strip().lower()
	if not first_name or len(first_name) > 140 or not validate_email_address(email):
		frappe.throw(_("Enter a valid name and email address."))
	frappe.db.set_value("Student Registration Application", name,
		{"first_name": first_name, "last_name": str(last_name or "").strip(), "email": email})
	return {"status": "Submitted"}


@frappe.whitelist(methods=["POST"])
def approve(application):
	_require_manager()
	frappe.get_doc("Student Registration Application", application).check_permission("read")
	frappe.db.sql("select name from `tabStudent Registration Application` where name=%s for update", application)
	doc = frappe.get_doc("Student Registration Application", application)
	if doc.status == "Approved":
		return {"student": doc.student, "created": False}
	if doc.status != "Submitted":
		frappe.throw(_("Only a submitted application can be approved."))
	national_id = get_decrypted_password(doc.doctype, doc.name, "national_id")
	result = _register({"first_name": doc.first_name, "last_name": doc.last_name, "national_id": national_id,
		"phone": doc.phone, "email": doc.email})
	frappe.db.set_value(doc.doctype, doc.name, {"status": "Approved", "student": result["student"]})
	return result


@frappe.whitelist(methods=["POST"])
def reject(application):
	_require_manager()
	frappe.get_doc("Student Registration Application", application).check_permission("read")
	frappe.db.sql("select name from `tabStudent Registration Application` where name=%s for update", application)
	if frappe.db.get_value("Student Registration Application", application, "status") != "Submitted":
		frappe.throw(_("Only a submitted application can be rejected."))
	frappe.db.set_value("Student Registration Application", application, "status", "Rejected")
	return {"status": "Rejected"}
