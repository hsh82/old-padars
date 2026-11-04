import frappe
from frappe.utils import getdate, today


ADMIN_ROLES = {"System Manager", "Education Manager"}
SCHOOL_SCOPED_DOCTYPES = {
	"School",
	"School Membership",
	"School Course Offering",
	"LMS Entity Mapping",
	"LMS Enrollment State",
	"LMS Sync Operation",
	"Program Enrollment",
	"Student Group",
	"Course Enrollment",
	"Course Schedule",
	"Assessment Plan",
	"Assessment Result",
	"Student Attendance",
	"Student",
	"Instructor",
}

SCHOOL_FIELD_BY_DOCTYPE = {
	"Program Enrollment": "padars_school",
	"Student Group": "padars_school",
	"School Course Offering": "school",
	"LMS Entity Mapping": "school",
	"LMS Enrollment State": "school",
	"LMS Sync Operation": "school",
}


def _is_membership_current(row):
	current_date = getdate(today())
	return (
		(not row.get("valid_from") or getdate(row.valid_from) <= current_date)
		and (not row.get("valid_to") or getdate(row.valid_to) >= current_date)
	)


def get_active_memberships(user=None, school=None, instructor=None):
	filters = {"status": "Active"}
	if user:
		filters["user"] = user
	if school:
		filters["school"] = school
	if instructor:
		filters["instructor"] = instructor

	rows = frappe.get_all(
		"School Membership",
		filters=filters,
		fields=["name", "school", "user", "instructor", "valid_from", "valid_to"],
		ignore_permissions=True,
	)
	return [row for row in rows if _is_membership_current(row)]


def is_school_admin(user=None):
	user = user or frappe.session.user
	return user == "Administrator" or bool(ADMIN_ROLES.intersection(frappe.get_roles(user)))


def get_user_schools(user=None):
	user = user or frappe.session.user
	if is_school_admin(user):
		return None

	return list({row.school for row in get_active_memberships(user=user)})


def has_school_access(school, user=None):
	user = user or frappe.session.user
	return is_school_admin(user) or school in (get_user_schools(user) or [])


def has_school_membership(school, user=None, instructor=None):
	return bool(get_active_memberships(user=user, school=school, instructor=instructor))


def _school_list_condition(user, doctype):
	schools = get_user_schools(user) or []
	if not schools:
		return "1=0"
	quoted_schools = ", ".join(frappe.db.escape(school) for school in schools)
	field = SCHOOL_FIELD_BY_DOCTYPE.get(doctype)
	if field:
		if not frappe.get_meta(doctype).has_field(field):
			return "1=0"
		return f"`tab{doctype}`.`{field}` in ({quoted_schools})"

	if doctype == "Student":
		return (
			"exists (select 1 from `tabSchool Membership` sm "
			"where sm.status = 'Active' and sm.user = `tabStudent`.`user` "
			f"and sm.school in ({quoted_schools}) "
			"and (sm.valid_from is null or sm.valid_from <= curdate()) "
			"and (sm.valid_to is null or sm.valid_to >= curdate()))"
		)
	if doctype == "Instructor":
		return (
			"exists (select 1 from `tabSchool Membership` sm "
			"where sm.status = 'Active' and sm.instructor = `tabInstructor`.`name` "
			f"and sm.school in ({quoted_schools}) "
			"and (sm.valid_from is null or sm.valid_from <= curdate()) "
			"and (sm.valid_to is null or sm.valid_to >= curdate()))"
		)
	if doctype == "Course Enrollment":
		return (
			"exists (select 1 from `tabProgram Enrollment` pe "
			"where pe.name = `tabCourse Enrollment`.`program_enrollment` "
			f"and pe.padars_school in ({quoted_schools}))"
		)
	if doctype in {"Course Schedule", "Assessment Plan", "Assessment Result"}:
		if frappe.get_meta(doctype).has_field("padars_course_offering"):
			return (
				f"exists (select 1 from `tabSchool Course Offering` sco where "
				f"sco.name = `tab{doctype}`.`padars_course_offering` "
				f"and sco.school in ({quoted_schools}))"
			)
		return "1=0"
	if doctype == "Student Attendance":
		return (
			"exists (select 1 from `tabStudent Group` sg "
			"where sg.name = `tabStudent Attendance`.`student_group` "
			f"and sg.padars_school in ({quoted_schools}))"
		)
	return "1=0"


def school_permission_query_conditions(user=None, doctype=None):
	user = user or frappe.session.user
	if is_school_admin(user):
		return ""
	if doctype == "School":
		schools = get_user_schools(user) or []
		if not schools:
			return "1=0"
		quoted_schools = ", ".join(frappe.db.escape(school) for school in schools)
		return f"`tabSchool`.`name` in ({quoted_schools})"
	return _school_list_condition(user, doctype)


def _get_doc_school(doc):
	doctype = doc.doctype
	field = SCHOOL_FIELD_BY_DOCTYPE.get(doctype)
	if field:
		return doc.get(field)
	if doctype == "Student":
		memberships = get_active_memberships(user=doc.get("user")) if doc.get("user") else []
		return memberships[0].school if len(memberships) == 1 else None
	if doctype == "Instructor":
		memberships = get_active_memberships(instructor=doc.name)
		return memberships[0].school if len(memberships) == 1 else None
	if doctype == "Course Enrollment":
		return frappe.db.get_value("Program Enrollment", doc.get("program_enrollment"), "padars_school")
	if doctype in {"Course Schedule", "Assessment Plan", "Assessment Result"}:
		offering = doc.get("padars_course_offering")
		return frappe.db.get_value("School Course Offering", offering, "school") if offering else None
	if doctype == "Student Attendance":
		return frappe.db.get_value("Student Group", doc.get("student_group"), "padars_school")
	return None


def has_school_permission(doc, ptype, user=None):
	user = user or frappe.session.user
	if is_school_admin(user):
		return True

	if not doc or doc.doctype not in SCHOOL_SCOPED_DOCTYPES:
		return None

	if doc.doctype == "School":
		return doc.name in (get_user_schools(user) or [])
	if doc.doctype == "Student" and not doc.get("user"):
		return ptype == "create"
	if doc.doctype == "Student":
		student_schools = {row.school for row in get_active_memberships(user=doc.get("user"))}
		return bool(student_schools.intersection(get_user_schools(user) or []))
	if doc.doctype == "Instructor":
		instructor_schools = {row.school for row in get_active_memberships(instructor=doc.name)}
		return bool(instructor_schools.intersection(get_user_schools(user) or []))
	school = _get_doc_school(doc)
	if not school:
		return None if ptype == "create" else False

	return school in (get_user_schools(user) or [])

