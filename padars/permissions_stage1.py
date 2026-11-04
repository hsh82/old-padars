"""Fail-closed, school-aware authorization helpers for Stage 1."""

import frappe
from frappe.utils import getdate, today


PLATFORM_ROLES = {"System Manager", "Padars Platform Administrator"}
SCHOOL_MANAGER_ROLE = "Padars School Manager"
ACADEMIC_STAFF_ROLE = "Padars Academic Staff"
TEACHER_ROLE = "Padars Teacher"
STUDENT_ROLE = "Student"

SCHOOL_SCOPED_DOCTYPES = {
	"School", "School Membership", "School Course Offering", "LMS Entity Mapping",
	"LMS Enrollment State", "LMS Sync Operation", "Program Enrollment", "Student Group",
	"Course Enrollment", "Course Schedule", "Assessment Plan", "Assessment Result",
	"Student Attendance", "Student", "Instructor",
}
SCHOOL_FIELD_BY_DOCTYPE = {
	"Program Enrollment": "padars_school", "Student Group": "padars_school",
	"Course Schedule": "padars_school", "Assessment Plan": "padars_school",
	"Assessment Result": "padars_school", "Student Attendance": "padars_school",
	"School Course Offering": "school", "LMS Entity Mapping": "school",
	"LMS Enrollment State": "school", "LMS Sync Operation": "school",
}


def _is_membership_current(row):
	current_date = getdate(today())
	return ((not row.get("valid_from") or getdate(row.valid_from) <= current_date)
		and (not row.get("valid_to") or getdate(row.valid_to) >= current_date))


def get_active_memberships(user=None, school=None, instructor=None, school_role=None):
	"""Internal authorization lookup; a membership label never grants a role alone."""
	filters = {"status": "Active"}
	for key, value in (("user", user), ("school", school), ("instructor", instructor), ("school_role", school_role)):
		if value:
			filters[key] = value
	rows = frappe.get_all(
		"School Membership", filters=filters,
		fields=["name", "school", "user", "instructor", "school_role", "valid_from", "valid_to"],
		ignore_permissions=True,
	)
	return [row for row in rows if _is_membership_current(row)]


def is_platform_admin(user=None):
	"""Administrator/System Manager remain the verified platform recovery route."""
	user = user or frappe.session.user
	return user == "Administrator" or bool(PLATFORM_ROLES.intersection(frappe.get_roles(user)))


def _has_role(user, role):
	return role in frappe.get_roles(user)


def _has_membership_role(user, school, school_role):
	return bool(get_active_memberships(user=user, school=school, school_role=school_role))


def can_manage_school(school, user=None):
	user = user or frappe.session.user
	if is_platform_admin(user):
		return True
	return ((_has_role(user, SCHOOL_MANAGER_ROLE) and _has_membership_role(user, school, "School Administrator"))
		or (_has_role(user, ACADEMIC_STAFF_ROLE) and _has_membership_role(user, school, "Academic Staff")))


def is_school_manager(school, user=None):
	user = user or frappe.session.user
	return is_platform_admin(user) or (_has_role(user, SCHOOL_MANAGER_ROLE)
		and _has_membership_role(user, school, "School Administrator"))


def get_user_schools(user=None):
	user = user or frappe.session.user
	if is_platform_admin(user):
		return None
	return sorted({row.school for row in get_active_memberships(user=user)})


def has_school_access(school, user=None):
	user = user or frappe.session.user
	return is_platform_admin(user) or school in (get_user_schools(user) or [])


def has_school_membership(school, user=None, instructor=None, school_role=None):
	return bool(get_active_memberships(user=user, school=school, instructor=instructor, school_role=school_role))


def get_teacher_instructors(user=None, school=None):
	user = user or frappe.session.user
	if not (_has_role(user, TEACHER_ROLE) and _has_role(user, "Instructor")):
		return []
	return [row.instructor for row in get_active_memberships(user=user, school=school, school_role="Teacher") if row.instructor]


def get_student_for_user(user=None):
	user = user or frappe.session.user
	if not _has_role(user, STUDENT_ROLE):
		return None
	return frappe.db.get_value("Student", {"user": user, "enabled": 1}, "name")


def _quoted(values):
	return ", ".join(frappe.db.escape(value) for value in values)


def _manager_schools(user):
	return [school for school in (get_user_schools(user) or []) if can_manage_school(school, user)]


def _school_condition(doctype, schools):
	field = SCHOOL_FIELD_BY_DOCTYPE.get(doctype)
	if not schools or not field or not frappe.get_meta(doctype).has_field(field):
		return "1=0"
	return f"`tab{doctype}`.`{field}` in ({_quoted(schools)})"


def _student_group_condition(student, doctype):
	if not student:
		return "1=0"
	escaped = frappe.db.escape(student)
	if doctype == "Student Group":
		return "exists (select 1 from `tabStudent Group Student` sgs where sgs.parent = `tabStudent Group`.`name` and sgs.student = %s and sgs.active = 1)" % escaped
	if doctype == "Course Schedule":
		return "exists (select 1 from `tabStudent Group Student` sgs where sgs.parent = `tabCourse Schedule`.`student_group` and sgs.student = %s and sgs.active = 1)" % escaped
	if doctype in {"Assessment Result", "Student Attendance", "Program Enrollment"}:
		return f"`tab{doctype}`.`student` = {escaped}"
	if doctype == "Course Enrollment":
		return "exists (select 1 from `tabProgram Enrollment` pe where pe.name = `tabCourse Enrollment`.`program_enrollment` and pe.student = %s)" % escaped
	return "1=0"


def _teacher_condition(user, doctype):
	instructors = get_teacher_instructors(user)
	if not instructors:
		return "1=0"
	quoted = _quoted(instructors)
	if doctype == "Instructor":
		return f"`tabInstructor`.`name` in ({quoted})"
	if doctype == "School Course Offering":
		return f"`tabSchool Course Offering`.`instructor` in ({quoted})"
	if doctype == "Student Group":
		return "exists (select 1 from `tabStudent Group Instructor` sgi where sgi.parent = `tabStudent Group`.`name` and sgi.instructor in (%s))" % quoted
	if doctype == "Student":
		return "exists (select 1 from `tabStudent Group Student` sgs join `tabStudent Group Instructor` sgi on sgi.parent = sgs.parent where sgs.student = `tabStudent`.`name` and sgs.active = 1 and sgi.instructor in (%s))" % quoted
	if doctype in {"Course Schedule", "Student Attendance"}:
		return "exists (select 1 from `tabStudent Group Instructor` sgi where sgi.parent = `tab%s`.`student_group` and sgi.instructor in (%s))" % (doctype, quoted)
	if doctype == "Assessment Result":
		return "exists (select 1 from `tabStudent Group Student` sgs join `tabStudent Group Instructor` sgi on sgi.parent = sgs.parent where sgs.student = `tabAssessment Result`.`student` and sgs.active = 1 and sgi.instructor in (%s))" % quoted
	return "1=0"


def _or_conditions(conditions):
	conditions = [condition for condition in conditions if condition and condition != "1=0"]
	return "(" + " or ".join(conditions) + ")" if conditions else "1=0"


def _membership_list_condition(user):
	schools = _manager_schools(user)
	return f"`tabSchool Membership`.`school` in ({_quoted(schools)})" if schools else "1=0"


def school_permission_query_conditions(user=None, doctype=None):
	"""List/report condition. Empty membership means zero rows, not all rows."""
	user = user or frappe.session.user
	if is_platform_admin(user):
		return ""
	if doctype == "School":
		schools = get_user_schools(user) or []
		return f"`tabSchool`.`name` in ({_quoted(schools)})" if schools else "1=0"
	if doctype == "School Membership":
		return _membership_list_condition(user)
	manager_schools = _manager_schools(user)
	conditions = []
	if doctype == "Student" and manager_schools:
		conditions.append("exists (select 1 from `tabSchool Membership` sm where sm.status = 'Active' and sm.user = `tabStudent`.`user` and sm.school in (%s) and (sm.valid_from is null or sm.valid_from <= curdate()) and (sm.valid_to is null or sm.valid_to >= curdate()))" % _quoted(manager_schools))
	elif doctype == "Instructor" and manager_schools:
		conditions.append("exists (select 1 from `tabSchool Membership` sm where sm.status = 'Active' and sm.instructor = `tabInstructor`.`name` and sm.school in (%s) and (sm.valid_from is null or sm.valid_from <= curdate()) and (sm.valid_to is null or sm.valid_to >= curdate()))" % _quoted(manager_schools))
	else:
		conditions.append(_school_condition(doctype, manager_schools))
	conditions.append(_teacher_condition(user, doctype))
	conditions.append(_student_group_condition(get_student_for_user(user), doctype))
	return _or_conditions(conditions)


def _get_doc_school(doc):
	field = SCHOOL_FIELD_BY_DOCTYPE.get(doc.doctype)
	if field:
		return doc.get(field)
	if doc.doctype == "Course Enrollment":
		return frappe.db.get_value("Program Enrollment", doc.get("program_enrollment"), "padars_school")
	if doc.doctype == "Student":
		memberships = get_active_memberships(user=doc.get("user")) if doc.get("user") else []
		schools = {row.school for row in memberships}
		return memberships[0].school if len(schools) == 1 else None
	if doc.doctype == "Instructor":
		memberships = get_active_memberships(instructor=doc.name)
		schools = {row.school for row in memberships}
		return memberships[0].school if len(schools) == 1 else None
	return None


def _student_can_read_doc(student, doc):
	if doc.doctype == "Student":
		return doc.name == student
	if doc.doctype in {"Program Enrollment", "Assessment Result", "Student Attendance"}:
		return doc.get("student") == student
	if doc.doctype == "Course Enrollment":
		return frappe.db.get_value("Program Enrollment", doc.get("program_enrollment"), "student") == student
	if doc.doctype == "Student Group":
		return bool(frappe.db.exists("Student Group Student", {"parent": doc.name, "student": student, "active": 1}))
	if doc.doctype == "Course Schedule":
		return bool(frappe.db.exists("Student Group Student", {"parent": doc.get("student_group"), "student": student, "active": 1}))
	return False


def _teacher_can_read_doc(user, doc):
	instructors = get_teacher_instructors(user, _get_doc_school(doc))
	if not instructors:
		return False
	if doc.doctype == "Instructor":
		return doc.name in instructors
	if doc.doctype == "School Course Offering":
		return doc.get("instructor") in instructors
	if doc.doctype in {"Student Group", "Course Schedule", "Student Attendance"}:
		group = doc.name if doc.doctype == "Student Group" else doc.get("student_group")
		return bool(frappe.db.exists("Student Group Instructor", {"parent": group, "instructor": ["in", instructors]}))
	if doc.doctype == "Student":
		return bool(frappe.db.sql("""select 1 from `tabStudent Group Student` sgs join `tabStudent Group Instructor` sgi on sgi.parent = sgs.parent where sgs.student=%s and sgs.active=1 and sgi.instructor in %(instructors)s limit 1""", {"student": doc.name, "instructors": tuple(instructors)}))
	return False


def has_school_permission(doc, ptype, user=None):
	"""Protect direct document URLs and REST/RPC document calls."""
	user = user or frappe.session.user
	if is_platform_admin(user):
		return True
	if not doc or doc.doctype not in SCHOOL_SCOPED_DOCTYPES:
		return None
	if ptype not in {"read", "write", "create", "delete", "submit", "cancel", "amend", "print", "email", "share"}:
		return False
	if doc.doctype == "School":
		return doc.name in (get_user_schools(user) or []) and ptype in {"read", "print"}
	if doc.doctype == "School Membership":
		return is_school_manager(doc.get("school"), user) and ptype in {"read", "write", "create", "delete"}
	if doc.doctype == "Student" and ptype == "create":
		return False  # WP04 reviewed registration service is the only non-platform path.
	school = _get_doc_school(doc)
	if school and can_manage_school(school, user):
		if doc.doctype in {"LMS Entity Mapping", "LMS Enrollment State", "LMS Sync Operation"}:
			return ptype in {"read", "print"}
		return True
	if ptype not in {"read", "print"}:
		return False
	student = get_student_for_user(user)
	return bool((student and _student_can_read_doc(student, doc)) or _teacher_can_read_doc(user, doc))
