#!/usr/bin/env python3
"""Check the built wheel, without importing Frappe or contacting a site."""

import argparse
import ast
import json
from email.parser import Parser
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile


REQUIRED = {
	"padars/hooks.py", "padars/install.py", "padars/modules.txt", "padars/patches.txt",
	"padars/fixtures/custom_field.json", "padars/fixtures/03_padars_permission_type.json",
	"padars/padars/workspace/padars/padars.json",
	"padars/padars/page/padars_setup/padars_setup.json",
	"padars/padars/page/lms_sync_monitor/lms_sync_monitor.json",
	"padars/padars/page/student_registration/student_registration.json",
	"padars/padars/print_format/padars_report_card/padars_report_card.json",
}
PORTALS = ("school", "teacher", "report-cards", "student-activation", "student-application")
CRITICAL_DOCTYPES = (
	"school", "school_course_offering", "lms_sync_operation", "student_identity",
	"school_assessment_scheme", "report_card_publication", "verified_guardian_access",
	"moodle_grade_snapshot", "moodle_grade_mapping", "moodle_grade_review",
	"moodle_learning_snapshot", "course_activity_selection",
	"session_attendance_policy", "attendance_evidence_proposal", "attendance_evidence_review", "attendance_evidence_use",
)


def inspect_wheel(path):
	errors = []
	with ZipFile(path) as wheel:
		names = set(wheel.namelist())
		required = set(REQUIRED)
		for route in PORTALS:
			required.update((f"padars/www/{route}.html", f"padars/www/{route.replace('-', '_')}.py"))
		for doctype in CRITICAL_DOCTYPES:
			required.add(f"padars/padars/doctype/{doctype}/{doctype}.json")
		for name in sorted(required - names):
			errors.append(f"Missing packaged artifact: {name}")
		for name in sorted(names):
			parts = PurePosixPath(name).parts
			if ".." in parts or name.startswith("/") or any(part in {".env", "site_config.json", "__pycache__", "node_modules"} for part in parts):
				errors.append(f"Unsafe or unnecessary packaged file: {name}")
			if name.endswith(".json"):
				try:
					data = json.loads(wheel.read(name))
				except (ValueError, UnicodeDecodeError):
					errors.append(f"Invalid packaged JSON: {name}")
					continue
				if "/doctype/" in name and isinstance(data, dict) and data.get("doctype") == "DocType":
					controller = name.removesuffix(".json") + ".py"
					if controller not in names:
						errors.append(f"Missing DocType controller: {controller}")
			if name.endswith(".py"):
				try:
					ast.parse(wheel.read(name), filename=name)
				except SyntaxError:
					errors.append(f"Invalid packaged Python: {name}")
		metadata = [name for name in names if name.endswith(".dist-info/METADATA")]
		if len(metadata) != 1:
			errors.append("Expected exactly one wheel metadata record")
		else:
			meta = Parser().parsestr(wheel.read(metadata[0]).decode())
			if meta.get("Name") != "padars" or not meta.get("Version") or "3.14" not in (meta.get("Requires-Python") or ""):
				errors.append("Missing or inconsistent Padars package/runtime metadata")
		if "padars/hooks.py" in names:
			tree = ast.parse(wheel.read("padars/hooks.py"))
			hooks = {}
			for statement in tree.body:
				if isinstance(statement, ast.Assign):
					for target in statement.targets:
						if isinstance(target, ast.Name):
							try:
								hooks[target.id] = ast.literal_eval(statement.value)
							except (ValueError, TypeError):
								pass
			if "education" not in hooks.get("required_apps", []):
				errors.append("Education is not declared as a required Frappe app")
			def strings(value):
				if isinstance(value, str):
					yield value
				elif isinstance(value, dict):
					for child in value.values():
						yield from strings(child)
				elif isinstance(value, (list, tuple)):
					for child in value:
						yield from strings(child)
			for key in ("doctype_js", "app_include_js", "app_include_css", "web_include_js"):
				for value in strings(hooks.get(key, [])):
					name = "padars/public/" + value.removeprefix("/assets/padars/") if value.startswith("/assets/padars/") else "padars/" + value
					if name not in names:
						errors.append(f"Missing hook asset: {name}")
	return errors


def main():
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("wheel", type=Path)
	args = parser.parse_args()
	try:
		errors = inspect_wheel(args.wheel)
	except (BadZipFile, OSError) as exc:
		parser.error(f"Cannot read wheel: {exc}")
	for error in errors:
		print(error)
	if errors:
		return 1
	print(f"PASS: {args.wheel.name}: schema/controllers, portal routes, hook assets, fixtures and metadata")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
