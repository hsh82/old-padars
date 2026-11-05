"""Use Frappe Data Import for Student CSV/XLSX while applying registration rules."""

import frappe
from frappe import _
from frappe.core.doctype.data_import.import_provider import ImportProvider
from frappe.core.doctype.data_import.importer import ACTION_INSERT, ACTION_UPDATE, INSERT

from padars.registration import _prepare, _register, _require_manager, _review


class StudentImportProvider(ImportProvider):
	def get_import_fields(self):
		fields = [
			{"fieldname": "first_name", "label": "First Name", "fieldtype": "Data", "reqd": 1},
			{"fieldname": "last_name", "label": "Last Name", "fieldtype": "Data"},
			{"fieldname": "national_id", "label": "National ID", "fieldtype": "Data", "reqd": 1},
			{"fieldname": "phone", "label": "Phone", "fieldtype": "Data", "reqd": 1},
			{"fieldname": "email", "label": "Email", "fieldtype": "Data", "reqd": 1},
		]
		for field in fields:
			field["parent"] = "Student"
		return {"fields": fields, "child_tables": []}

	def validate(self, import_file):
		_require_manager()
		warnings, seen_ids, seen_emails = [], set(), set()
		for row in import_file.data:
			try:
				data = _prepare(row.parse_doc(self.doctype))
				if data["identity_key"] in seen_ids or data["email"] in seen_emails:
					frappe.throw(_("Duplicate identity or email in the import file."))
				seen_ids.add(data["identity_key"])
				seen_emails.add(data["email"])
				_review(data)
			except (frappe.ValidationError, frappe.PermissionError):
				frappe.clear_messages()
				warnings.append({"row": row.row_number, "message": _("Check the registration details and existing records.")})
		return warnings

	def import_row(self, importer, doc):
		_require_manager()
		if importer.import_type != INSERT:
			frappe.throw(_("Use Insert New Records for student registration imports."))
		result = _register(doc)
		return frappe.get_doc("Student", result["student"]), ACTION_INSERT if result["created"] else ACTION_UPDATE


def validate_import(doc, method=None):
	if doc.reference_doctype != "Student":
		return
	if doc.google_sheets_url:
		frappe.throw(_("Student registration imports must use a private local file."))
	if doc.import_file:
		if not doc.import_file.startswith("/private/files/") or not frappe.db.exists("File", {
			"file_url": doc.import_file, "is_private": 1,
		}):
			frappe.throw(_("Student registration imports must use a private local file."))
