"""Seed a clearly labelled synthetic assessment through the real approval workflow."""
import argparse
import json
import os
from pathlib import Path

import frappe
from frappe.utils import today


def populate(path):
    assert frappe.conf.get("padars_staging_demo") == 1 and frappe.conf.get("mute_emails")
    assert frappe.db.get_default("padars_staging_demo_seed_v1")
    if frappe.db.get_default("padars_staging_assessment_seed_v1"):
        print("Synthetic assessment already installed; preserved existing marks")
        return
    credentials = json.loads(path.read_text())
    assert credentials["site"] == frappe.local.site
    demo = credentials["demo"]
    manager = next(user for user, row in credentials["accounts"].items() if row.get("profile") == "Padars School Manager")
    teacher = next(user for user, row in credentials["accounts"].items() if row.get("profile") == "Padars Teacher")
    frappe.set_user("Administrator")
    group = frappe.get_doc("Student Group", demo["group"])
    assessment_group = frappe.get_doc({"doctype": "Assessment Group", "assessment_group_name": "Staging Term Assessment",
        "parent_assessment_group": "All Assessment Groups", "is_group": 0}).insert()
    criterion = frappe.get_doc({"doctype": "Assessment Criteria", "assessment_criteria": "Staging Written Assessment"}).insert()
    scale = frappe.get_doc({"doctype": "Grading Scale", "grading_scale_name": "Staging Example Scale",
        "intervals": [{"grade_code": "F", "threshold": 0}, {"grade_code": "P", "threshold": 50}]}).insert()
    scale.submit()
    plan = frappe.get_doc({"doctype": "Assessment Plan", "student_group": group.name,
        "program": demo["program"], "course": demo["course"], "academic_year": demo["year"],
        "academic_term": demo["terms"][0], "assessment_group": assessment_group.name, "grading_scale": scale.name,
        "schedule_date": today(), "from_time": "13:00:00", "to_time": "14:00:00", "examiner": demo["instructor"],
        "maximum_assessment_score": 100,
        "assessment_criteria": [{"assessment_criteria": criterion.name, "maximum_score": 100}]}).insert()
    plan.submit()
    frappe.set_user(manager)
    scheme = frappe.get_doc({"doctype": "School Assessment Scheme", "scheme_title": "Synthetic staging example; not school grading policy",
        "course_offering": demo["offering"], "academic_term": demo["terms"][0], "grading_scale": scale.name,
        "output_maximum": 20, "decimal_places": 2,
        "components": [{"assessment_plan": plan.name, "assessment_criteria": criterion.name, "weight": 100}]}).insert()
    scheme.submit()
    from padars.assessment import mark_assessment_result
    from padars.publication import preview_report_card, publish_report_card
    publications = []
    for student, score in zip(demo["students"], (80, 75, 90), strict=True):
        frappe.set_user(teacher)
        result = mark_assessment_result(plan.name, {"student": student, "assessment_details": {criterion.name: score}})
        frappe.set_user(manager)
        frappe.get_doc("Assessment Result", result["name"]).submit()
        enrollment = frappe.db.get_value("Program Enrollment", {"student": student, "docstatus": 1}, "name")
        preview = preview_report_card(enrollment, [scheme.name])
        publications.append(publish_report_card(enrollment, [scheme.name], preview["digest"])["name"])
    demo.update({"assessment_plan": plan.name, "assessment_scheme": scheme.name, "publications": publications})
    temp = path.with_suffix(".tmp")
    descriptor = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as output:
        json.dump(credentials, output, indent=2)
    os.replace(temp, path)
    frappe.db.set_default("padars_staging_assessment_seed_v1", 1)
    frappe.db.commit()
    print("PASS: teacher entered synthetic marks; school manager approved and published 3 report cards")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", required=True)
    parser.add_argument("--credentials", required=True)
    args = parser.parse_args()
    frappe.init(args.site)
    frappe.connect()
    try:
        populate(Path(args.credentials))
    except Exception as exc:
        frappe.db.rollback()
        print(f"ASSESSMENT BLOCKER: {type(exc).__name__}: {str(exc)[:400]}")
        raise SystemExit(1)
    finally:
        frappe.destroy()
