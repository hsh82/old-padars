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

MAX_BATCH_SIZE = 100


def _require_manager():
	school = get_primary_school(required=True)
	if not can_manage_school(school):
		frappe.throw(_("Only a school manager can register students."), frappe.PermissionError)
	return school


def _identity_key(value):
	value = unicodedata.normalize("NFKC", str(value or "")).strip()
	value = "".join(str(unicodedata.decimal(c)) if c.isdecimal() else c.upper() for c in value)
	if not re.fullmatch(r"[A-Z0-9]{6,32}", value):
		frappe.throw(_("Enter a valid national identifier (6–32 letters or digits)."))
	key = frappe.local.conf.get("encryption_key")
	if not key:
		frappe.throw(_("The site encryption key must be configured before registration."))
	return hmac.new(key.encode(), ("padars-student-id-v1:" + value).encode(), hashlib.sha256).hexdigest()


def _phone(value):
	value = unicodedata.normalize("NFKC", str(value or "")).strip()
	value = "".join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in value)
	value = re.sub(r"[ ()-]", "", value)
	if not re.fullmatch(r"\+[1-9][0-9]{7,14}", value):
		frappe.throw(_("Enter a phone number in international format, beginning with +."))
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
	if frappe.db.get_single_value("Education Settings", "user_creation_skip") != 1:
		frappe.throw(_("Enable Skip User Creation in Education Settings before registering students."))
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
	student = frappe.get_doc({"doctype": "Student", "first_name": data["first_name"],
		"last_name": data["last_name"], "student_email_id": data["email"],
		"student_mobile_number": data["phone"]}).insert()
	identity.student = student.name
	identity.save(ignore_permissions=True)
	return {"student": student.name, "created": True}


@frappe.whitelist(methods=["POST"])
def register_student(first_name, national_id, phone, email, last_name=None):
	_require_manager()
	return _register(dict(first_name=first_name, national_id=national_id, phone=phone, email=email, last_name=last_name))


@frappe.whitelist(methods=["POST"])
def register_batch(rows, preview=True):
	_require_manager()
	rows = frappe.parse_json(rows) if isinstance(rows, str) else rows
	if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_BATCH_SIZE:
		frappe.throw(_("Provide between 1 and 100 registration rows."))
	preview = frappe.utils.cint(preview) == 1
	results = []
	seen = set()
	seen_emails = set()
	for index, row in enumerate(rows, 1):
		savepoint = f"padars_registration_{index}"
		frappe.db.savepoint(savepoint)
		try:
			data = _prepare(row)
			if data["identity_key"] in seen:
				frappe.throw(_("This identity appears more than once in the batch."))
			if data["email"] in seen_emails:
				frappe.throw(_("This email appears more than once in the batch."))
			seen.add(data["identity_key"])
			seen_emails.add(data["email"])
			if preview:
				result = {"status": "valid", "existing": bool(_review(data))}
			else:
				result = {"status": "success", **_register(row)}
		except Exception:
			frappe.db.rollback(save_point=savepoint)
			frappe.clear_messages()
			result = {"status": "error", "message": _("Row could not be processed; check its values and existing records.")}
		results.append({"row": index, **result})
	return results


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
