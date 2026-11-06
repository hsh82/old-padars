#!/usr/bin/env python3
"""Read-only installed-schema gate. Run in Bench's Python environment."""

import argparse
import json
import os
from pathlib import Path

import frappe
import padars


def verify(site, sites_path, fresh=False, expected_app_root=None):
	app_root = Path(padars.__file__).resolve().parent.parent
	if expected_app_root and app_root != Path(expected_app_root).resolve():
		raise AssertionError("The effective Padars import is not the intended checkout")
	sites_path = str(Path(sites_path).resolve())
	os.chdir(sites_path)  # Native Frappe logging and site paths are relative to sites/.
	frappe.init(site, sites_path=sites_path)
	try:
		frappe.connect()
		installed = set(frappe.get_installed_apps())
		assert {"frappe", "erpnext", "education", "padars"}.issubset(installed)
		if fresh:
			assert installed == {"frappe", "erpnext", "education", "padars"}
			assert not frappe.db.get_single_value("LMS Settings", "enabled")
			assert frappe.db.count("Student") == 0
			assert frappe.db.count("LMS Entity Mapping") == 0
		assert frappe.db.get_value("Role", "Padars Guardian", "desk_access") == 0
		count = 0
		for path in (app_root / "padars/padars/doctype").glob("*/*.json"):
			definition = json.loads(path.read_text())
			if definition.get("doctype") != "DocType":
				continue
			meta = frappe.get_meta(definition["name"])
			for field in definition.get("fields", []):
				assert meta.has_field(field["fieldname"]), f"Missing {meta.name}.{field['fieldname']}"
				if field.get("unique"):
					assert meta.get_field(field["fieldname"]).unique, f"Missing uniqueness metadata: {meta.name}.{field['fieldname']}"
					assert frappe.db.get_column_index(f"tab{meta.name}", field["fieldname"], unique=True), f"Missing unique database index: {meta.name}.{field['fieldname']}"
			count += 1
		for path in (app_root / "padars/fixtures").glob("*.json"):
			for row in json.loads(path.read_text()):
				assert frappe.db.exists(row["doctype"], row["name"]), f"Missing fixture: {row['doctype']} {row['name']}"
		for folder, doctype in (("page", "Page"), ("workspace", "Workspace"), ("print_format", "Print Format")):
			for path in (app_root / f"padars/padars/{folder}").glob("*/*.json"):
				definition = json.loads(path.read_text())
				assert frappe.db.exists(doctype, definition["name"]), f"Missing {doctype}: {definition['name']}"
		for name in ("Academic Term", "Grading Scale", "Assessment Criteria", "Assessment Group", "Room"):
			assert any(row.role == "Padars School Manager" and row.read and row.create and row.write for row in frappe.get_meta(name).permissions), name
		print(f"PASS: {site}: {count} Padars DocTypes, fixtures, pages, workspace, print format and academic role permissions")
		if fresh:
			print("PASS: required apps only, LMS disabled, empty student/mapping data, portal-only guardian role")
	finally:
		frappe.destroy()


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--site", required=True)
	parser.add_argument("--sites-path", default="sites")
	parser.add_argument("--fresh", action="store_true")
	parser.add_argument("--expected-app-root")
	args = parser.parse_args()
	verify(args.site, args.sites_path, args.fresh, args.expected_app_root)
