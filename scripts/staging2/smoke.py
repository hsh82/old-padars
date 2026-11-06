"""Text-only HTTP checks against an isolated synthetic Stage 2 deployment."""
import argparse
import json
import re
from pathlib import Path

import requests


def verify(base_url, credentials):
    data = json.loads(Path(credentials).read_text())
    assert data["site"] == "stage2.kara.loc"
    headers = {"Host": data["site"]}
    # Never attempt authentication until the explicit route identifies Stage 2.
    response = requests.get(base_url + "/login", headers=headers, timeout=30)
    assert response.status_code == 200, f"Login HTTP {response.status_code}"
    assert response.headers.get("X-Padars-Site") == data["site"], "Wrong site; authentication refused"
    assert response.headers.get("X-Padars-Environment") == "Staging 2"
    demo = data["demo"]

    def get(session, path, status=200, **kwargs):
        result = session.get(base_url + path, timeout=45, **kwargs)
        assert result.status_code == status, f"{path}: HTTP {result.status_code}; expected {status}"
        return result

    def login(email):
        session = requests.Session()
        session.headers.update(headers)
        result = session.post(base_url + "/api/method/login", data={"usr": email,
            "pwd": data["accounts"][email]["password"]}, timeout=30)
        assert result.status_code == 200, f"{email}: login HTTP {result.status_code}"
        expected = {"Padars School Manager": "app/padars", "Padars Teacher": "teacher",
            "Padars Student": "school", "Padars Guardian": "school"}[data["accounts"][email]["profile"]]
        assert result.json()["home_page"].lstrip("/") == expected, f"{email}: incorrect role landing page"
        assert get(session, "/api/method/frappe.auth.get_logged_user").json()["message"] == email
        return session

    manager = login("manager@stage2.example.invalid")
    get(manager, "/app/padars")
    for doctype in ("School", "Program", "Student Group", "School Course Offering", "Course Schedule", "Student"):
        get(manager, f"/api/resource/{doctype}")
    get(manager, "/api/resource/Role Profile", 403)
    get(manager, "/api/resource/Custom Field", 403)
    get(manager, "/api/resource/LMS Settings/LMS Settings", 403)
    print("PASS: School Manager login, Desk and academic lists; profile/custom-field/infrastructure access denied")

    page = get(manager, "/teacher").text
    csrf = re.search(r'frappe\.csrf_token\s*=\s*"([^"]+)"', page)
    assert csrf, "Native authenticated CSRF token missing"
    manager.headers["X-Frappe-CSRF-Token"] = csrf.group(1)
    draft = manager.post(base_url + "/api/method/padars.student_import.create_student_intake", timeout=30)
    assert draft.status_code == 200, f"Create intake HTTP {draft.status_code}"
    parent = draft.json()["message"]["name"]
    uploaded = manager.post(base_url + "/api/method/upload_file", data={"doctype": "Data Import",
        "docname": parent, "fieldname": "import_file", "is_private": "1"},
        files={"file": ("stage2-empty-intake.csv", b"National ID,Phone,First Name,Last Name\n", "text/csv")}, timeout=30)
    assert uploaded.status_code == 200, f"Private import upload HTTP {uploaded.status_code}"
    attachment = uploaded.json()["message"]
    assert attachment["is_private"] and attachment["attached_to_name"] == parent
    assert get(manager, attachment["file_url"]).content.startswith(b"National ID,")
    denied = manager.post(base_url + "/api/method/upload_file", data={"doctype": "Role Profile",
        "docname": "Padars Company Administrator", "is_private": "1"},
        files={"file": ("denied.csv", b"synthetic", "text/csv")}, timeout=30)
    assert denied.status_code == 403, f"Unrelated attachment HTTP {denied.status_code}"
    print("PASS: native saved-parent private CSV upload/download; unrelated attachment denied")

    teacher = login("teacher@stage2.example.invalid")
    assert "My Teaching" in get(teacher, "/teacher").text
    overview = get(teacher, "/api/method/padars.teaching.get_teaching_overview").json()["message"]
    assert overview["courses"] and overview["sessions"]
    assert overview["courses"][0]["roster_count"] == 3
    get(teacher, "/api/resource/Role Profile", 403)
    print("PASS: assigned teacher portal, timetable and three-student roster; profile administration denied")

    for number in (1, 2):
        student = login(f"student{number}@stage2.example.invalid")
        assert "Weekly timetable" in get(student, "/school").text
        overview = get(student, "/api/method/padars.portal.get_academic_overview").json()["message"]
        assert overview["courses"] and overview["sessions"]
        other = demo["students"][1 if number == 1 else 0]
        get(student, "/api/method/padars.portal.get_academic_overview", 403, params={"student": other})
        get(student, "/api/resource/Role Profile", 403)
        get(student, attachment["file_url"], 403)
        cards = get(student, "/api/method/padars.publication.list_report_cards").json()["message"]
        own_card = demo["publications"][number - 1]
        assert [row["name"] for row in cards] == [own_card]
        assert "Staging Mathematics" in get(student, "/report-cards", params={"publication": own_card}).text
        get(student, "/api/method/padars.publication.read_report_card", 403,
            params={"publication": demo["publications"][1 if number == 1 else 0]})
        if number == 1:
            pdf = get(student, "/api/method/padars.publication.download_report_card", params={"publication": own_card})
            assert pdf.content.startswith(b"%PDF"), "Report card PDF generation failed"
    print("PASS: two student logins and own timetable/course; other student's overview and role administration denied")

    guardian = login("guardian@stage2.example.invalid")
    get(guardian, "/school", params={"student": demo["students"][0]})
    own = get(guardian, "/api/method/padars.portal.get_academic_overview", params={"student": demo["students"][0]}).json()["message"]
    assert own["courses"] and own["attendance"]
    get(guardian, "/api/method/padars.portal.get_academic_overview", 403, params={"student": demo["students"][1]})
    cards = get(guardian, "/api/method/padars.publication.list_report_cards", params={"student": demo["students"][0]}).json()["message"]
    assert [row["name"] for row in cards] == [demo["publications"][0]]
    get(guardian, "/api/method/padars.publication.read_report_card", 403, params={"publication": demo["publications"][1]})
    print("PASS: verified guardian's child timetable/attendance/report; unrelated child and report denied")
    print("PASS: published student report pages and generated PDF; cross-student reports denied")

    from padars.hooks import app_include_js
    for asset in app_include_js:
        get(manager, asset)
    print("PASS: installed Padars Desk JavaScript is served")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://nginx")
    parser.add_argument("--credentials", required=True)
    args = parser.parse_args()
    verify(args.base_url.rstrip("/"), args.credentials)
