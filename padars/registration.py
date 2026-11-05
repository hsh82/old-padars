"""Staff registration using Education records and private identity reservations."""

import hashlib
import hmac
import re
import unicodedata

import frappe
from frappe import _
from frappe.utils import today, validate_email_address

from padars.permissions import can_manage_school
from padars.school_context import get_primary_school

def _require_manager():
	school = get_primary_school(required=True)
	if not can_manage_school(school):
		frappe.throw(_("Only a school manager can register students."), frappe.PermissionError)
	return school


def normalize_national_id(value):
	value = unicodedata.normalize("NFKC", str(value or "")).strip()
	value = "".join(str(unicodedata.decimal(c)) if c.isdecimal() else c.upper() for c in value)
	if not re.fullmatch(r"[0-9]{10}", value) or len(set(value)) == 1:
		frappe.throw(_("Enter a valid 10-digit Iranian national ID."))
	remainder = sum(int(value[i]) * (10 - i) for i in range(9)) % 11
	if int(value[9]) != (remainder if remainder < 2 else 11 - remainder):
		frappe.throw(_("Enter a valid 10-digit Iranian national ID."))
	return value


def _identity_key(value):
	value = normalize_national_id(value)
	key = frappe.local.conf.get("encryption_key")
	if not key:
		frappe.throw(_("The site encryption key must be configured before registration."))
	return hmac.new(key.encode(), ("padars-student-id-v1:" + value).encode(), hashlib.sha256).hexdigest()


def _phone(value):
	value = unicodedata.normalize("NFKC", str(value or "")).strip()
	value = "".join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in value)
	value = re.sub(r"[ ()-]", "", value)
	if re.fullmatch(r"09[0-9]{9}", value):
		value = "+98" + value[1:]
	if not re.fullmatch(r"\+989[0-9]{9}", value):
		frappe.throw(_("Enter an Iranian mobile number beginning with 09 or +989."))
	return value


def _prepare(row):
	if not isinstance(row, dict):
		frappe.throw(_("A registration row must be an object."))
	first_name = str(row.get("first_name") or "").strip()
	if not first_name or len(first_name) > 140:
		frappe.throw(_("A student first name is required."))
	email = str(row.get("email") or "").strip().lower()
	if not email or not validate_email_address(email):
		frappe.throw(_("A valid student email address is required by Education."))
	return {"identity_key": _identity_key(row.get("national_id")), "phone": _phone(row.get("phone")),
		"first_name": first_name, "last_name": str(row.get("last_name") or "").strip(), "email": email}


def _review(data):
	reservation = frappe.db.get_value("Student Identity", {"identity_key": data["identity_key"]}, "student")
	if reservation:
		student = frappe.get_doc("Student", reservation)
		student.check_permission("read")
		if student.student_mobile_number != data["phone"] or student.student_email_id.lower() != data["email"]:
			frappe.throw(_("An existing identity needs staff review before registration."))
		return student.name
	if frappe.db.exists("User", data["email"]) or frappe.db.exists("Student", {"student_email_id": data["email"]}):
		frappe.throw(_("The supplied contact details require staff review."))
	return None


def _register(row):
	data = _prepare(row)
	existing = _review(data)
	if existing:
		return {"student": existing, "created": False}
	identity = frappe.get_doc({"doctype": "Student Identity", "identity_key": data["identity_key"]})
	identity.insert(ignore_permissions=True)
	# Keep the account disabled until the first password change succeeds.
	user = frappe.get_doc({"doctype": "User", "email": data["email"], "first_name": data["first_name"],
		"last_name": data["last_name"], "mobile_no": data["phone"], "enabled": 0,
		"user_type": "Website User", "send_welcome_email": 0}).insert(ignore_permissions=True)
	user.add_roles("Student")
	from frappe.utils.password import update_password
	update_password(user.name, "0" + data["phone"][3:])
	student = frappe.get_doc({"doctype": "Student", "first_name": data["first_name"],
		"last_name": data["last_name"], "student_email_id": data["email"],
		"student_mobile_number": data["phone"], "user": user.name}).insert()
	identity.student = student.name
	identity.user = user.name
	identity.pending_activation = 1
	identity.save(ignore_permissions=True)
	return {"student": student.name, "created": True}


@frappe.whitelist(methods=["POST"])
def register_student(first_name, national_id, phone, email, last_name=None):
	_require_manager()
	return _register(dict(first_name=first_name, national_id=national_id, phone=phone, email=email, last_name=last_name))


@frappe.whitelist(methods=["POST"])
def enroll_returning_student(student, program, academic_year, academic_term=None):
	school = _require_manager()
	frappe.get_doc("Student", student).check_permission("read")
	frappe.get_doc("Program", program).check_permission("read")
	frappe.get_doc("Academic Year", academic_year).check_permission("read")
	# Serialize enrollment attempts for the same student, including retries.
	frappe.db.sql("select name from `tabStudent` where name=%s for update", student)
	filters = {"student": student, "program": program, "academic_year": academic_year, "docstatus": ["<", 2]}
	rows = frappe.get_all("Program Enrollment", filters=filters, fields=["name", "academic_term"])
	existing = next((row.name for row in rows if (row.academic_term or "") == (academic_term or "")), None)
	if existing:
		frappe.get_doc("Program Enrollment", existing).check_permission("read")
		return {"enrollment": existing, "created": False}
	enrollment = frappe.get_doc({"doctype": "Program Enrollment", "student": student, "program": program,
		"academic_year": academic_year, "academic_term": academic_term or None,
		"enrollment_date": today(), "padars_school": school}).insert()
	return {"enrollment": enrollment.name, "created": True}
