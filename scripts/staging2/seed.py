"""Explicit synthetic staging setup; never imported by app installation hooks.

Run from Bench sites/ after setting padars_staging_demo=1 in the target's config.
Credentials are written only to a private file outside the application checkout.
"""
import argparse
import json
import os
from pathlib import Path
import secrets

import frappe
from frappe.utils import getdate, today
from frappe.utils.password import update_password


def seed(credentials_path):
    assert frappe.conf.get("padars_staging_demo") == 1, "Explicit staging-only configuration is required"
    assert frappe.conf.get("mute_emails"), "Staging email must be muted"
    assert not frappe.db.get_single_value("LMS Settings", "enabled"), "External LMS must remain disabled"
    credentials_path = Path(credentials_path)
    assert credentials_path.exists(), "Create private administrator credentials during site installation first"
    credentials = json.loads(credentials_path.read_text())
    assert credentials["site"] == frappe.local.site
    if frappe.db.get_default("padars_staging_demo_seed_v1"):
        print("Synthetic staging seed already installed; preserved existing data and passwords")
        return
    assert not frappe.db.count("School") and not frappe.db.count("Student"), "Only an empty staging school may be seeded"
    frappe.set_user("Administrator")
    if not frappe.is_setup_complete():
        from frappe.desk.page.setup_wizard.setup_wizard import setup_complete
        setup_complete({"language": "English", "lang": "en", "country": "Iran", "timezone": "Asia/Tehran",
            "currency": "IRR", "company_name": "Padars Staging School", "company_abbr": "PSS",
            "chart_of_accounts": "Standard", "fy_start_date": "2026-01-01", "fy_end_date": "2026-12-31",
            "setup_demo": 0, "enable_telemetry": 0})
        assert frappe.is_setup_complete()

    holiday_list = frappe.get_doc({"doctype": "Holiday List", "holiday_list_name": "Staging School Calendar",
        "from_date": "2026-09-01", "to_date": "2027-08-31"}).insert()
    company = frappe.get_doc("Company", "Padars Staging School")
    company.default_holiday_list = holiday_list.name
    company.save()

    def account(email, first_name, profile, website=False):
        password = secrets.token_urlsafe(18)
        doc = frappe.get_doc({"doctype": "User", "email": email, "first_name": first_name,
            "enabled": 1, "send_welcome_email": 0, "user_type": "Website User" if website else "System User",
            "role_profiles": [{"role_profile": profile}]}).insert()
        update_password(doc.name, password)
        credentials["accounts"][doc.name] = {"password": password, "profile": profile}
        return doc.name

    manager = account("manager@stage2.example.invalid", "School Manager", "Padars School Manager")
    teacher = account("teacher@stage2.example.invalid", "Mathematics Teacher", "Padars Teacher")
    guardian_user = account("guardian@stage2.example.invalid", "Demo Guardian", "Padars Guardian", True)
    year = frappe.get_doc({"doctype": "Academic Year", "academic_year_name": "2026-2027 Staging",
        "year_start_date": "2026-09-01", "year_end_date": "2027-08-31"}).insert()
    term_names = []
    for name, start, end in [("First Term", "2026-09-01", "2027-01-31"), ("Second Term", "2027-02-01", "2027-08-31")]:
        term = frappe.get_doc({"doctype": "Academic Term", "academic_year": year.name,
            "term_name": name, "term_start_date": start, "term_end_date": end}).insert()
        term_names.append(term.name)
    school = frappe.get_doc({"doctype": "School", "school_code": "STAGE2", "school_name": "Padars Staging School",
        "current_academic_year": year.name, "primary_school_manager": manager, "company": "Padars Staging School",
        "require_sms_verification": 0}).insert()
    course = frappe.get_doc({"doctype": "Course", "course_name": "Staging Mathematics"}).insert()
    program = frappe.get_doc({"doctype": "Program", "program_name": "Staging Grade 11",
        "padars_grade_level": "11", "padars_stream": "General",
        "courses": [{"course": course.name, "required": 1}]}).insert()
    from padars.curriculum import create_curriculum_adoption_from_program, generate_course_offerings
    adoption = frappe.get_doc("School Curriculum Adoption", create_curriculum_adoption_from_program(program.name, year.name)["name"])
    adoption.courses[0].weekly_hours = 2
    adoption.status = "Active"
    adoption.save()
    group = frappe.get_doc({"doctype": "Student Group", "student_group_name": "Staging Grade 11 A",
        "academic_year": year.name, "academic_term": term_names[0], "program": program.name, "group_based_on": "Batch",
        "padars_school": school.name, "padars_is_class_section": 1, "padars_section_code": "11A",
        "padars_curriculum_adoption": adoption.name}).insert()
    offering = frappe.get_doc("School Course Offering", generate_course_offerings(group.name)["offerings"][0])
    instructor = frappe.get_doc({"doctype": "Instructor", "instructor_name": "Staging Mathematics Teacher"}).insert()
    from padars.staff import link_instructor_to_user, assign_teacher_to_offering
    link_instructor_to_user(instructor.name, teacher)
    assign_teacher_to_offering(offering.name, instructor.name)
    students = []
    for number in range(1, 4):
        user = account(f"student{number}@stage2.example.invalid", f"Demo Student {number}", "Padars Student", True)
        student = frappe.get_doc({"doctype": "Student", "first_name": f"Demo Student {number}",
            "student_email_id": user, "user": user, "enabled": 1}).insert()
        frappe.get_doc({"doctype": "Program Enrollment", "student": student.name, "program": program.name,
            "academic_year": year.name, "academic_term": term_names[0], "enrollment_date": "2026-09-01",
            "padars_school": school.name}).insert().submit()
        group.append("students", {"student": student.name, "active": 1})
        students.append(student.name)
    group.save()
    guardian = frappe.get_doc({"doctype": "Guardian", "guardian_name": "Demo Guardian",
        "email_address": guardian_user, "user": guardian_user}).insert()
    child = frappe.get_doc("Student", students[0])
    child.append("guardians", {"guardian": guardian.name, "relation": "Others"})
    child.save()
    from padars.guardian_access import verify_guardian_access
    verify_guardian_access(child.name, guardian.name, guardian_user, "Synthetic staging relationship; no real student data")
    room = frappe.get_doc({"doctype": "Room", "room_name": "Staging Room A"}).insert()
    from datetime import timedelta
    monday = getdate(today()) - timedelta(days=getdate(today()).weekday())
    sessions = []
    for day in range(14):
        date = monday + timedelta(days=day)
        if date.weekday() not in (0, 2, 4):
            continue
        schedule = frappe.get_doc({"doctype": "Course Schedule", "student_group": group.name,
            "program": program.name, "course": course.name, "instructor": instructor.name, "room": room.name,
            "schedule_date": date, "from_time": "09:00:00", "to_time": "10:00:00",
            "padars_course_offering": offering.name, "padars_session_mode": "Physical"}).insert()
        sessions.append(schedule.name)
    frappe.get_doc({"doctype": "Student Attendance", "student": students[0], "course_schedule": sessions[0],
        "student_group": group.name, "date": monday, "status": "Present"}).insert().submit()
    credentials["demo"] = {"school": school.name, "year": year.name, "terms": term_names, "program": program.name,
        "course": course.name, "group": group.name, "offering": offering.name, "instructor": instructor.name,
        "students": students, "guardian": guardian.name, "sessions": sessions}
    frappe.db.set_default("padars_staging_demo_seed_v1", 1)
    # Write before commit so a filesystem failure rolls back academic seeding.
    temp = credentials_path.with_suffix(".tmp")
    descriptor = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as output:
        json.dump(credentials, output, indent=2)
    os.replace(temp, credentials_path)
    frappe.db.commit()
    frappe.clear_cache()
    print("PASS: synthetic school, 2 terms, Grade 11 class, teacher, 3 enrolled students, guardian and 2-week timetable")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", required=True)
    parser.add_argument("--credentials", required=True)
    args = parser.parse_args()
    frappe.init(args.site)
    frappe.connect()
    try:
        seed(args.credentials)
    except Exception as exc:
        frappe.db.rollback()
        print(f"SEED BLOCKER: {type(exc).__name__}: {str(exc)[:400]}")
        raise SystemExit(1)
    finally:
        frappe.destroy()
