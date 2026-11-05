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
from padars.sensitive_requests import protect_registration_request


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
		["name", "user", "student", "phone", "first_name", "last_name"], as_dict=True)
	if not identity or (identity.user and frappe.db.get_value("User", identity.user, "enabled")):
		frappe.throw(_("Invalid activation details."), frappe.AuthenticationError)
	try:
		if identity.user:
			check_password(identity.user, str(temporary_password or ""), delete_tracker_cache=False)
		else:
			from padars.student_identity import check_provisional_password
			check_provisional_password(identity, temporary_password)
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


def _queue_otp_sms(secret, counter, phone, cache_key):
	"""Queue after commit; invalidate the code if the provider rejects queuing."""
	from frappe.twofactor import send_token_via_sms
	def send():
		try:
			if send_token_via_sms(secret, token=counter, phone_no=phone):
				return
		except Exception:
			pass
		frappe.cache.delete_value(cache_key)
		frappe.log_error(title="Student SMS queue failed", message="Student verification SMS could not be queued.")
	frappe.db.after_commit.add(send)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@protect_registration_request
@rate_limit(limit=5, seconds=3600)
def send_activation_code(national_id, temporary_password):
	identity_key, identity = _credentials(national_id, temporary_password)
	if not _sms_required():
		frappe.throw(_("SMS verification is not enabled."))
	if not _sms_configured():
		frappe.throw(_("SMS delivery is not configured. Contact the school."))
	phone = identity.phone or frappe.db.get_value("Student", identity.student, "student_mobile_number")
	secret = base64.b32encode(secrets.token_bytes(20)).decode("ascii")
	counter = secrets.randbelow(2**31)
	otp = pyotp.HOTP(secret).at(counter)
	cache_key = "padars:activation-otp:" + identity_key
	frappe.cache.set_value(cache_key, _otp_digest(identity_key, otp), expires_in_sec=300)
	_queue_otp_sms(secret, counter, phone, cache_key)
	return {"queued": True}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@protect_registration_request
@rate_limit(limit=10, seconds=3600)
def verify_first_login(national_id, temporary_password):
	_, identity = _credentials(national_id, temporary_password)
	return {"needs_details": not bool(identity.user)}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@protect_registration_request
@rate_limit(limit=10, seconds=3600)
def activate(national_id, temporary_password, new_password, otp=None, email=None, first_name=None, last_name=None, confirm_password=None):
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
	if not identity.user:
		if new_password != confirm_password:
			frappe.throw(_("The passwords do not match."))
		user = _complete_provisional(identity, email, first_name, last_name, new_password)
	else:
		user = identity.user
		update_password(user, new_password, logout_all_sessions=True)
		frappe.db.set_value("User", user, "enabled", 1)
		frappe.db.set_value("Student Identity", identity.name, "pending_activation", 0)
	frappe.clear_cache(user=user)
	if _sms_required():
		frappe.cache.delete_value("padars:activation-otp:" + identity_key)
	return {"activated": True}


def _complete_provisional(identity, email, first_name, last_name, new_password):
	from frappe.utils import validate_email_address
	from frappe.utils.password import remove_encrypted_password
	from padars.student_extension import _ONBOARDING

	email = str(email or "").strip().lower()
	first_name = str(first_name or identity.first_name or "").strip()
	last_name = str(last_name or identity.last_name or "").strip()
	if not validate_email_address(email) or not email.endswith("@gmail.com"):
		frappe.throw(_("Enter a valid Gmail address."))
	if not first_name or len(first_name) > 140 or len(last_name) > 140:
		frappe.throw(_("Enter the student's first name."))
	if frappe.db.exists("User", email) or frappe.db.exists("Student", {"student_email_id": email}):
		frappe.throw(_("These details require school review."))
	# Only these fixed records are created with elevated document permissions;
	# the request remains Guest and never assumes the Administrator session.
	user = frappe.get_doc({"doctype": "User", "email": email, "first_name": first_name,
		"last_name": last_name, "phone": identity.phone, "enabled": 1,
		"user_type": "Website User", "send_welcome_email": 0})
	user.append_roles("Student")
	user.insert(ignore_permissions=True)
	update_password(user.name, new_password)
	student = frappe.get_doc({"doctype": "Student", "first_name": first_name, "last_name": last_name,
		"student_email_id": email, "student_mobile_number": identity.phone, "user": user.name})
	previous_flag = getattr(frappe.flags, "padars_onboarding_student", None)
	try:
		frappe.flags.padars_onboarding_student = _ONBOARDING
		student.insert(ignore_permissions=True)
	finally:
		frappe.flags.padars_onboarding_student = previous_flag
	frappe.db.set_value("Student Identity", identity.name,
		{"user": user.name, "student": student.name, "pending_activation": 0})
	remove_encrypted_password("Student Identity", identity.name, "provisional_password")
	return user.name


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
