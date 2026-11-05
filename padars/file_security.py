"""Prevent public URLs for files attached to sensitive academic records."""

import frappe
from frappe import _

PRIVATE_PARENT_DOCTYPES = {
	"Student", "Guardian", "Student Log", "Student Group", "Program Enrollment", "Course Enrollment",
	"Student Attendance", "Assessment Plan", "Assessment Result", "Academic Assignment", "Course Schedule",
	"School Course Offering", "LMS Entity Mapping", "LMS Enrollment State", "LMS Sync Operation",
}


def validate_private_attachment(doc, method=None):
	if doc.attached_to_doctype in PRIVATE_PARENT_DOCTYPES:
		if not doc.is_private or (doc.file_url and not doc.file_url.startswith("/private/files/")):
			frappe.throw(_("Academic attachments must use private site files."), frappe.PermissionError)


def validate_share(doc, method=None):
	from padars.permissions_site import SCOPED_DOCTYPES

	parent = doc.share_doctype
	if parent == "File":
		parent = frappe.db.get_value("File", doc.share_name, "attached_to_doctype")
	if parent in SCOPED_DOCTYPES or parent in PRIVATE_PARENT_DOCTYPES:
		frappe.throw(_("Academic records and their files cannot be shared directly; use an academic assignment."),
			frappe.PermissionError)


def assert_no_protected_shares():
	from padars.permissions_site import SCOPED_DOCTYPES

	protected = sorted(SCOPED_DOCTYPES | PRIVATE_PARENT_DOCTYPES)
	if frappe.db.exists("DocShare", {"share_doctype": ["in", protected]}):
		frappe.throw(_("Remove direct shares of academic records before configuring this school."))
	if frappe.db.sql("""select ds.name from `tabDocShare` ds join `tabFile` f on f.name=ds.share_name
		where ds.share_doctype='File' and f.attached_to_doctype in %(parents)s limit 1""", {"parents": tuple(protected)}):
		frappe.throw(_("Remove direct shares of academic attachments before configuring this school."))
	if frappe.db.sql("""select name from `tabFile` where attached_to_doctype in %(parents)s
		and (is_private=0 or coalesce(file_url, '') not like '/private/files/%%') limit 1""",
		{"parents": tuple(sorted(PRIVATE_PARENT_DOCTYPES))}):
		frappe.throw(_("Move existing academic attachments to private site files before configuring this school."))


def has_permission(doc, ptype, user=None, **kwargs):
	if doc.attached_to_doctype not in PRIVATE_PARENT_DOCTYPES:
		return True
	if not doc.is_private or not doc.attached_to_name or not (doc.file_url or "").startswith("/private/files/"):
		return False
	parent_type = "write" if ptype in {"write", "create", "delete", "share"} else "read"
	return frappe.has_permission(doc.attached_to_doctype, parent_type, doc.attached_to_name, user=user)


def permission_query_conditions(user=None, doctype=None):
	from padars.permissions import is_platform_admin, school_permission_query_conditions

	user = user or frappe.session.user
	if is_platform_admin(user):
		return ""
	conditions = []
	for parent in sorted(PRIVATE_PARENT_DOCTYPES):
		quoted = frappe.db.escape(parent)
		if frappe.has_permission(parent, "read", user=user):
			scope = school_permission_query_conditions(user, parent) or "1=1"
			allowed = (f"(`tabFile`.`is_private`=1 and `tabFile`.`file_url` like '/private/files/%%' and exists (select 1 from `tab{parent}` "
				f"where `tab{parent}`.`name`=`tabFile`.`attached_to_name` and ({scope})))")
		else:
			allowed = "1=0"
		conditions.append(f"(coalesce(`tabFile`.`attached_to_doctype`, '') != {quoted} or {allowed})")
	return " and ".join(conditions)
