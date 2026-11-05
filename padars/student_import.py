"""Use Frappe Data Import for Student CSV/XLSX while applying registration rules."""

import frappe
from frappe import _
from frappe.core.doctype.data_import.import_provider import ImportProvider
from frappe.core.doctype.data_import.importer import ACTION_INSERT, ACTION_UPDATE, INSERT

from padars.registration import _identity_key, _phone, _require_manager
from padars.student_identity import reserve_provisional


@frappe.whitelist(methods=["POST"])
def create_student_intake():
	_require_manager()
	# Save first so Frappe's uploader can authorize writes against a scoped,
	# persisted Data Import rather than an untyped, unsaved document.
	doc = frappe.get_doc({"doctype": "Data Import", "reference_doctype": "Student Identity",
		"import_type": "Insert New Records"}).insert()
	return {"name": doc.name}


class ProvisionalStudentImportProvider(ImportProvider):
	def get_import_fields(self):
		fields = [
			{"fieldname": "national_id", "label": "National ID", "fieldtype": "Data", "reqd": 1},
			{"fieldname": "phone", "label": "Phone", "fieldtype": "Data", "reqd": 1},
			{"fieldname": "first_name", "label": "First Name", "fieldtype": "Data"},
			{"fieldname": "last_name", "label": "Last Name", "fieldtype": "Data"},
		]
		for field in fields:
			field["parent"] = "Student Identity"
		return {"fields": fields, "child_tables": []}

	def validate(self, import_file):
		_require_manager()
		warnings, seen = [], set()
		for row in import_file.data:
			try:
				data = row.parse_doc(self.doctype)
				key = _identity_key(data.get("national_id"))
				phone = _phone(data.get("phone"))
				if key in seen:
					frappe.throw(_("Duplicate identity in this file."))
				seen.add(key)
				existing = frappe.db.get_value("Student Identity", {"identity_key": key},
					["phone", "pending_activation", "user"], as_dict=True)
				if existing and (existing.phone != phone or not existing.pending_activation or existing.user):
					frappe.throw(_("Identity requires review."))
			except (frappe.ValidationError, frappe.PermissionError):
				frappe.clear_messages()
				warnings.append({"row": row.row_number, "message": _("Check the identity, phone, and existing records.")})
		return warnings

	def import_row(self, importer, doc):
		_require_manager()
		if importer.import_type != INSERT:
			frappe.throw(_("Use Insert New Records for student imports."))
		identity, created = reserve_provisional(doc.get("national_id"), doc.get("phone"),
			doc.get("first_name"), doc.get("last_name"))
		return identity, ACTION_INSERT if created else ACTION_UPDATE


def validate_import(doc, method=None):
	from padars.permissions import is_platform_admin, is_school_manager
	from padars.school_context import get_primary_school
	if not is_platform_admin() and is_school_manager(get_primary_school()) and doc.reference_doctype != "Student Identity":
		frappe.throw(_("School managers may only import student identities."), frappe.PermissionError)
	if doc.reference_doctype not in {"Student", "Student Identity"}:
		return
	if doc.google_sheets_url:
		frappe.throw(_("Student registration imports must use a private local file."))
	if doc.import_file:
		if not doc.import_file.startswith("/private/files/") or not frappe.db.exists("File", {
			"file_url": doc.import_file, "is_private": 1,
		}):
			frappe.throw(_("Student registration imports must use a private local file."))
