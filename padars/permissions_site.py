"""Authorization within a single-school site.

Assignments narrow native Frappe role permissions; they never grant a role.
"""

import frappe
from frappe.utils import getdate, today

from padars.school_context import get_primary_school

PLATFORM_ROLES = {"System Manager", "Padars Platform Administrator"}
STAFF_ROLES = {"Padars Academic Staff", "Padars Teacher", "Padars Grade Entry Staff", "Padars Read Only"}
MANAGER_ROLE = "Padars School Manager"
SCOPED_DOCTYPES = {
	"School", "School Membership", "Academic Assignment", "School Course Offering", "LMS Entity Mapping",
	"School Curriculum Adoption",
	"LMS Enrollment State", "LMS Sync Operation", "Program Enrollment", "Student Group", "Course Enrollment",
	"Course Schedule", "Assessment Plan", "Assessment Result", "Student Attendance", "Student", "Instructor",
	"Student Log", "Guardian", "Program",
	"Program Enrollment Tool", "Student Group Creation Tool", "Course Scheduling Tool",
	"Student Attendance Tool", "Assessment Result Tool", "Student Report Generation Tool",
}


def is_platform_admin(user=None):
	user = user or frappe.session.user
	return user == "Administrator" or bool(PLATFORM_ROLES.intersection(frappe.get_roles(user)))


def is_lms_operator(user=None):
	user = user or frappe.session.user
	return is_platform_admin(user) or "Padars Moodle Manager" in frappe.get_roles(user)


def is_school_manager(school=None, user=None):
	user = user or frappe.session.user
	if is_platform_admin(user):
		return True
	return bool(school and school == get_primary_school() and MANAGER_ROLE in frappe.get_roles(user))


def can_manage_school(school, user=None):
	return is_school_manager(school, user)


def can_manage_moodle(school, user=None):
	user = user or frappe.session.user
	return is_lms_operator(user) or is_school_manager(school, user)


def get_user_schools(user=None):
	user = user or frappe.session.user
	if is_platform_admin(user):
		return None
	school = get_primary_school()
	roles = set(frappe.get_roles(user))
	return [school] if school and roles.intersection(STAFF_ROLES | {MANAGER_ROLE, "Padars Moodle Manager", "Student"}) else []


def has_school_access(school, user=None):
	return bool(school and school == get_primary_school() and (is_platform_admin(user) or school in (get_user_schools(user) or [])))


def get_student_for_user(user=None):
	user = user or frappe.session.user
	if "Student" not in frappe.get_roles(user):
		return None
	return frappe.db.get_value("Student", {"user": user, "enabled": 1}, "name")


def _assignments(user, action="read"):
	if not (STAFF_ROLES | {MANAGER_ROLE}).intersection(frappe.get_roles(user)):
		return []
	rows = frappe.get_all(
		"Academic Assignment", filters={"user": user, "status": "Active"},
		fields=["scope_type", "scope_name", "instructor", "valid_from", "valid_to", "can_edit",
			"can_enter_marks", "can_manage_attendance", "can_view_sensitive"],
	)
	current = getdate(today())
	return [r for r in rows if (not r.valid_from or getdate(r.valid_from) <= current)
		and (not r.valid_to or getdate(r.valid_to) >= current)
		and (action == "read" or r.get(action))]


def get_teacher_instructors(user=None, school=None):
	user = user or frappe.session.user
	if "Padars Teacher" not in frappe.get_roles(user) or (school and school != get_primary_school()):
		return []
	return sorted({row.instructor for row in _assignments(user) if row.instructor})


def _scopes(user, action="read"):
	rows = _assignments(user, action)
	programs = {r.scope_name for r in rows if r.scope_type == "Program"}
	broad_groups = {r.scope_name for r in rows if r.scope_type == "Student Group"}
	direct_offers = {r.scope_name for r in rows if r.scope_type == "School Course Offering"}
	if programs:
		broad_groups.update(frappe.get_all("Student Group", filters={"program": ["in", list(programs)]}, pluck="name"))
	offers = set(direct_offers)
	if broad_groups:
		offers.update(frappe.get_all("School Course Offering", filters={"student_group": ["in", list(broad_groups)]}, pluck="name"))
	visible_groups = set(broad_groups)
	if direct_offers:
		visible_groups.update(frappe.get_all("School Course Offering", filters={"name": ["in", list(direct_offers)]}, pluck="student_group"))
	return frappe._dict(programs=programs, broad_groups=broad_groups, groups=visible_groups,
		offerings=offers, direct_offers=direct_offers, instructors={r.instructor for r in rows if r.instructor})


def _in(field, values):
	values = sorted(v for v in values if v)
	if not values:
		return "1=0"
	return f"{field} in ({', '.join(frappe.db.escape(v) for v in values)})"


def school_permission_query_conditions(user=None, doctype=None):
	user = user or frappe.session.user
	if is_platform_admin(user):
		return ""
	if doctype == "Student Log":
		if "Padars Sensitive Records" not in frappe.get_roles(user):
			return "1=0"
		groups = _scopes(user, "can_view_sensitive").groups
		if not groups:
			return "1=0"
		return "exists (select 1 from `tabStudent Group Student` sgs where sgs.student=`tabStudent Log`.`student` and sgs.active=1 and " + _in("sgs.parent", groups) + ")"
	if doctype in {"LMS Entity Mapping", "LMS Enrollment State", "LMS Sync Operation"}:
		return "" if can_manage_moodle(get_primary_school(), user) else "1=0"
	if is_school_manager(get_primary_school(), user):
		return ""
	if doctype in {"School Membership", "Academic Assignment", "LMS Entity Mapping", "LMS Enrollment State", "LMS Sync Operation", "Guardian", "Student Log"}:
		return "1=0"
	if doctype == "School":
		return _in("`tabSchool`.`name`", get_user_schools(user) or [])
	scope = _scopes(user)
	student = get_student_for_user(user)
	own = frappe.db.escape(student) if student else None
	group_list = ", ".join(frappe.db.escape(v) for v in sorted(scope.groups) if v)
	broad = _in(f"`tab{doctype}`.`student_group`", scope.broad_groups)
	offer = _in(f"`tab{doctype}`.`padars_course_offering`", scope.offerings)
	if doctype == "Student Group":
		parts = [_in("`tabStudent Group`.`name`", scope.groups)]
	elif doctype == "School Course Offering":
		parts = [_in("`tabSchool Course Offering`.`name`", scope.offerings)]
	elif doctype == "Student":
		parts = [f"exists (select 1 from `tabStudent Group Student` sgs where sgs.student=`tabStudent`.`name` and sgs.active=1 and sgs.parent in ({group_list}))" if group_list else "1=0"]
		if own:
			parts.append(f"`tabStudent`.`name`={own}")
	elif doctype == "Program":
		programs = set(scope.programs)
		if scope.groups:
			programs.update(frappe.get_all("Student Group", filters={"name": ["in", list(scope.groups)]}, pluck="program"))
		parts = [_in("`tabProgram`.`name`", programs)]
	elif doctype == "Instructor":
		parts = [_in("`tabInstructor`.`name`", scope.instructors)]
	elif doctype == "Program Enrollment":
		parts = [_in("`tabProgram Enrollment`.`program`", scope.programs)]
		if group_list:
			parts.append(f"exists (select 1 from `tabStudent Group` sg join `tabStudent Group Student` sgs on sgs.parent=sg.name where sg.name in ({group_list}) and sgs.active=1 and sgs.student=`tabProgram Enrollment`.`student` and sg.academic_year=`tabProgram Enrollment`.`academic_year` and sg.program=`tabProgram Enrollment`.`program`)")
		if own:
			parts.append(f"`tabProgram Enrollment`.`student`={own}")
	elif doctype == "Course Enrollment":
		parts = [_in("`tabCourse Enrollment`.`program`", scope.programs)]
		if group_list:
			parts.append(f"exists (select 1 from `tabStudent Group` sg join `tabStudent Group Student` sgs on sgs.parent=sg.name join `tabSchool Course Offering` sco on sco.student_group=sg.name and sco.course=`tabCourse Enrollment`.`course` where sg.name in ({group_list}) and sgs.active=1 and sgs.student=`tabCourse Enrollment`.`student` and sco.name in ({', '.join(frappe.db.escape(v) for v in sorted(scope.offerings)) or "''"}))")
	elif doctype in {"Course Schedule", "Assessment Plan", "Assessment Result"}:
		parts = [broad, offer]
		if doctype == "Course Schedule" and own:
			parts.append(f"exists (select 1 from `tabStudent Group Student` sgs where sgs.parent=`tabCourse Schedule`.`student_group` and sgs.student={own} and sgs.active=1)")
	elif doctype == "Student Attendance":
		parts = [broad]
		if scope.offerings:
			parts.append("exists (select 1 from `tabCourse Schedule` cs where cs.name=`tabStudent Attendance`.`course_schedule` and " + _in("cs.padars_course_offering", scope.offerings) + ")")
		if own:
			parts.append(f"`tabStudent Attendance`.`student`={own}")
	else:
		return "1=0"
	return "(" + " or ".join(parts) + ")"


def _matches_write_scope(doc, scope):
	group = doc.name if doc.doctype == "Student Group" else doc.get("student_group")
	offering = doc.name if doc.doctype == "School Course Offering" else doc.get("padars_course_offering")
	if doc.doctype == "Student Attendance" and doc.get("course_schedule"):
		offering = frappe.db.get_value("Course Schedule", doc.course_schedule, "padars_course_offering")
	if group and doc.doctype != "Student Group":
		group_data = frappe.db.get_value("Student Group", group, ["program", "academic_year"], as_dict=True)
		if not group_data:
			return False
		for field in ("program", "academic_year"):
			if doc.get(field) and group_data.get(field) and doc.get(field) != group_data.get(field):
				return False
	if offering and doc.doctype != "School Course Offering":
		offering_data = frappe.db.get_value("School Course Offering", offering,
			["student_group", "program", "academic_year", "course"], as_dict=True)
		if not offering_data:
			return False
		for field in ("student_group", "program", "academic_year", "course"):
			if doc.get(field) and doc.get(field) != offering_data.get(field):
				return False
	matched = bool(doc.get("program") in scope.programs or group in scope.broad_groups or offering in scope.offerings)
	if doc.doctype == "Student Group":
		matched = bool(doc.get("program") in scope.programs or group in scope.broad_groups)
	if matched and doc.doctype in {"Assessment Result", "Student Attendance"}:
		matched = bool(group and doc.get("student") and frappe.db.exists("Student Group Student", {"parent": group, "student": doc.student, "active": 1}))
	return matched


def has_school_permission(doc, ptype, user=None, **kwargs):
	user = user or frappe.session.user
	if is_platform_admin(user):
		return True
	if not doc or doc.doctype not in SCOPED_DOCTYPES:
		return False
	if doc.doctype == "Assessment Result" and ptype in {"submit", "cancel", "amend"}:
		return False  # Approval and correction are introduced with report-card workflows.
	if doc.doctype == "LMS Entity Mapping":
		return can_manage_moodle(get_primary_school(), user) and ptype in {"read", "print", "select"}
	if doc.doctype in {"LMS Enrollment State", "LMS Sync Operation"}:
		if ptype in {"read", "print", "select"}:
			return can_manage_moodle(get_primary_school(), user)
		return is_lms_operator(user) and ptype in {"write", "create", "manage_moodle"}
	if doc.doctype != "Student Log" and is_school_manager(get_primary_school(), user):
		if ptype in {"write", "create"} and doc.doctype in {"Assessment Result", "Student Attendance"}:
			custom = "enter_grade" if doc.doctype == "Assessment Result" else "manage_attendance"
			return frappe.has_permission(doc.doctype, custom, doc=doc, user=user, ignore_share_permissions=True)
		return True
	if ptype == "view_sensitive_student_data" and doc.doctype == "Student Log":
		if doc.is_new():
			return False
		condition = school_permission_query_conditions(user, doc.doctype)
		return bool(frappe.db.sql(f"select name from `tabStudent Log` where name=%s and ({condition}) limit 1", doc.name))
	if doc.doctype == "Student Log" and ptype in {"read", "print", "select"}:
		return frappe.has_permission("Student Log", "view_sensitive_student_data", doc=doc, user=user, ignore_share_permissions=True)
	custom_actions = {"enter_grade": ("Assessment Result", "can_enter_marks"),
		"manage_attendance": ("Student Attendance", "can_manage_attendance")}
	if ptype in custom_actions:
		expected_doctype, action = custom_actions[ptype]
		return doc.doctype == expected_doctype and _can_write_in_scope(doc, _scopes(user, action))
	if ptype in {"read", "print", "select"}:
		if doc.is_new():
			return False
		condition = school_permission_query_conditions(user, doc.doctype)
		return bool(frappe.db.sql(f"select name from `tab{doc.doctype}` where name=%s and ({condition}) limit 1", doc.name))
	if ptype not in {"write", "create"}:
		return False
	if doc.doctype in {"Assessment Result", "Student Attendance"}:
		custom = "enter_grade" if doc.doctype == "Assessment Result" else "manage_attendance"
		return frappe.has_permission(doc.doctype, custom, doc=doc, user=user, ignore_share_permissions=True)
	action = {"Assessment Result": "can_enter_marks", "Student Attendance": "can_manage_attendance"}.get(doc.doctype, "can_edit")
	if doc.doctype not in {"Assessment Result", "Student Attendance", "Student Group", "School Course Offering", "Course Schedule", "Assessment Plan"}:
		return False
	return _can_write_in_scope(doc, _scopes(user, action))


def _can_write_in_scope(doc, scope):
	if not _matches_write_scope(doc, scope):
		return False
	if not doc.is_new():
		# Check both versions: a read-only assignment must not permit moving an
		# unrelated record into a scope where this user has write access.
		old = frappe.get_doc(doc.doctype, doc.name)
		if not _matches_write_scope(old, scope):
			return False
		fixed_fields = {
			"Student Group": ("academic_year", "program", "group_based_on", "padars_school"),
			"School Course Offering": ("school", "academic_year", "program", "course", "student_group", "instructor"),
			"Course Schedule": ("academic_year", "program", "course", "student_group", "instructor", "padars_course_offering"),
			"Assessment Plan": ("academic_year", "program", "course", "student_group", "padars_course_offering"),
			"Assessment Result": ("assessment_plan", "student", "academic_year", "program", "course", "student_group", "padars_course_offering"),
			"Student Attendance": ("student", "student_group", "course_schedule"),
		}.get(doc.doctype, ())
		if any(old.get(field) != doc.get(field) for field in fixed_fields):
			return False
		if doc.doctype == "Student Group":
			def roster(record):
				return [(r.student, r.active, r.group_roll_number) for r in record.get("students", [])]
			if roster(old) != roster(doc):
				return False
		return True
	return True
