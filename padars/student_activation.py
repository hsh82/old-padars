"""First-login activation: no session exists until the temporary password is changed."""

import base64
import hashlib
import hmac
import re
import secrets
import unicodedata

import frappe
import pyotp
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils.password import check_password, update_password

from padars.registration import _identity_key, _phone, normalize_national_id
from padars.school_context import get_primary_school


def _credentials(national_id, temporary_password):
	try:
		identity_key = _identity_key(national_id)
	except frappe.ValidationError:
		frappe.clear_messages()
		frappe.throw(_("Invalid activation details."), frappe.AuthenticationError)
	# In addition to the per-IP endpoint limit, limit guesses per identity.
	key = "padars:activation-attempts:" + identity_key
	count = frappe.cache.incr(key)
	if count == 1:
		frappe.cache.expire(key, 3600)
	if count > 10:
		frappe.throw(_("Too many activation attempts. Try again later."), frappe.AuthenticationError)
	identity = frappe.db.get_value("Student Identity", {"identity_key": identity_key, "pending_activation": 1},
		["name", "user", "student"], as_dict=True)
	if not identity or not identity.user or frappe.db.get_value("User", identity.user, "enabled"):
		frappe.throw(_("Invalid activation details."), frappe.AuthenticationError)
	try:
		check_password(identity.user, str(temporary_password or ""), delete_tracker_cache=False)
	except frappe.AuthenticationError:
		frappe.throw(_("Invalid activation details."), frappe.AuthenticationError)
	return identity_key, identity


def _sms_required():
	return bool(frappe.db.get_value("School", get_primary_school(required=True), "require_sms_verification"))


def _otp_digest(identity_key, otp):
	return hmac.new(frappe.local.conf.encryption_key.encode(),
		("padars-activation:" + identity_key + ":" + str(otp)).encode(), hashlib.sha256).hexdigest()


def _sms_configured():
	return bool(frappe.get_hooks("send_token_via_sms") or frappe.db.get_single_value("SMS Settings", "sms_gateway_url"))


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=3600)
def send_activation_code(national_id, temporary_password):
	identity_key, identity = _credentials(national_id, temporary_password)
	if not _sms_required():
		frappe.throw(_("SMS verification is not enabled."))
	if not _sms_configured():
		frappe.throw(_("SMS delivery is not configured. Contact the school."))
	from frappe.twofactor import send_token_via_sms
	phone = frappe.db.get_value("Student", identity.student, "student_mobile_number")
	secret = base64.b32encode(secrets.token_bytes(20)).decode("ascii")
	counter = secrets.randbelow(2**31)
	otp = pyotp.HOTP(secret).at(counter)
	cache_key = "padars:activation-otp:" + identity_key
	frappe.cache.set_value(cache_key, _otp_digest(identity_key, otp), expires_in_sec=300)
	frappe.db.after_commit.add(lambda: send_token_via_sms(secret, token=counter, phone_no=phone))
	return {"queued": True}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=3600)
def activate(national_id, temporary_password, new_password, otp=None):
	identity_key, identity = _credentials(national_id, temporary_password)
	frappe.db.sql("select name from `tabStudent Identity` where name=%s for update", identity.name)
	if not frappe.db.get_value("Student Identity", identity.name, "pending_activation"):
		frappe.throw(_("Invalid activation details."), frappe.AuthenticationError)
	if _sms_required():
		cache_key = "padars:activation-otp:" + identity_key
		stored = frappe.cache.get_value(cache_key)
		if not stored or not hmac.compare_digest(str(stored), _otp_digest(identity_key, otp or "")):
			frappe.throw(_("Invalid or expired verification code."), frappe.AuthenticationError)
	if not isinstance(new_password, str) or len(new_password) < 10 or len(new_password) > 128:
		frappe.throw(_("Choose a password of 10 to 128 characters."))
	if new_password in {temporary_password, normalize_national_id(national_id), _phone(temporary_password)}:
		frappe.throw(_("Choose a password different from your ID and phone number."))
	from frappe.core.doctype.user.user import handle_password_test_fail, test_password_strength
	feedback = test_password_strength(new_password).get("feedback")
	if feedback and not feedback.get("password_policy_validation_passed", False):
		handle_password_test_fail(feedback)
	update_password(identity.user, new_password, logout_all_sessions=True)
	frappe.db.set_value("User", identity.user, "enabled", 1)
	frappe.db.set_value("Student Identity", identity.name, "pending_activation", 0)
	frappe.clear_cache(user=identity.user)
	if _sms_required():
		frappe.cache.delete_value("padars:activation-otp:" + identity_key)
	return {"activated": True}


def resolve_student_login(login_manager):
	"""Map a national ID to Frappe's real email-based User identity."""
	identifier = frappe.form_dict.get("usr")
	if not identifier:
		return
	canonical = unicodedata.normalize("NFKC", str(identifier)).strip()
	canonical = "".join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in canonical)
	if not re.fullmatch(r"[0-9]{10}", canonical):
		return
	try:
		key = _identity_key(canonical)
	except frappe.ValidationError:
		frappe.clear_messages()
		frappe.form_dict.usr = "padars-unknown-student"
		return
	user = frappe.db.get_value("Student Identity", {"identity_key": key, "pending_activation": 0}, "user")
	frappe.form_dict.usr = user or "padars-unknown-student"
