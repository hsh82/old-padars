import frappe


ADMIN_ROLES = {"System Manager", "Education Manager"}
SCHOOL_SCOPED_DOCTYPES = {
	"School",
	"School Membership",
	"School Course Offering",
	"LMS Entity Mapping",
	"LMS Enrollment State",
	"LMS Sync Operation",
}


def is_school_admin(user=None):
	user = user or frappe.session.user
	return user == "Administrator" or bool(ADMIN_ROLES.intersection(frappe.get_roles(user)))


def get_user_schools(user=None):
	user = user or frappe.session.user
	if is_school_admin(user):
		return None

	return frappe.get_all(
		"School Membership",
		filters={"user": user, "status": "Active"},
		pluck="school",
		ignore_permissions=True,
	)


def has_school_access(school, user=None):
	user = user or frappe.session.user
	return is_school_admin(user) or school in (get_user_schools(user) or [])


def school_permission_query_conditions(user=None, doctype=None):
	user = user or frappe.session.user
	if is_school_admin(user):
		return ""

	schools = get_user_schools(user) or []
	if not schools:
		return "1=0"

	quoted_schools = ", ".join(frappe.db.escape(school) for school in schools)
	field = "name" if doctype == "School" else "school"
	return f"`tab{doctype}`.`{field}` in ({quoted_schools})"


def has_school_permission(doc, ptype, user=None):
	user = user or frappe.session.user
	if is_school_admin(user):
		return True

	if not doc or doc.doctype not in SCHOOL_SCOPED_DOCTYPES:
		return None

	school = doc.name if doc.doctype == "School" else doc.get("school")
	if not school:
		return ptype == "create" and False

	return school in (get_user_schools(user) or [])

