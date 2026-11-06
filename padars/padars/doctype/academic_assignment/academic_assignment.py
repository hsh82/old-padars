import hashlib

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from padars.permissions import is_platform_admin
from padars.permissions_site import STAFF_ROLES
from padars.school_context import get_primary_school

SCOPE_TYPES = {"Program", "Student Group", "School Course Offering"}
ASSIGNMENT_TYPES = {"Scoped Staff", "Teacher", "Grade Coordinator", "Class Supervisor"}
ASSIGNMENT_ROLES = {
	"Teacher": "Padars Teacher",
	"Grade Coordinator": "Padars Grade Coordinator",
	"Class Supervisor": "Padars Class Supervisor",
}


class AcademicAssignment(Document):
	def validate(self):
		self.validate_manager()
		if self.scope_type not in SCOPE_TYPES:
			frappe.throw(_("Choose a Program, Student Group, or School Course Offering scope."))
		if not frappe.db.exists(self.scope_type, self.scope_name):
			frappe.throw(_("The selected academic scope does not exist."))
		user = frappe.db.get_value("User", self.user, ["enabled", "user_type"], as_dict=True)
		if not user or not user.enabled or user.user_type != "System User":
			frappe.throw(_("The assigned User must be an enabled System User."))
		self.assignment_type = self.assignment_type or "Scoped Staff"
		if self.assignment_type not in ASSIGNMENT_TYPES:
			frappe.throw(_("Choose a supported academic assignment type."))
		self.validate_scope_school()
		self.validate_assignment_type()
		if self.valid_from and self.valid_to and getdate(self.valid_from) > getdate(self.valid_to):
			frappe.throw(_("Valid To cannot be earlier than Valid From."))
		if self.status == "Active" and self.instructor and self.scope_type == "School Course Offering":
			offering_instructor = frappe.db.get_value("School Course Offering", self.scope_name, "instructor")
			if offering_instructor != self.instructor:
				frappe.throw(_("Instructor must match the Course Offering's Instructor."))
		identity = "\0".join((self.user, self.scope_type, self.scope_name))
		self.active_key = hashlib.sha256(identity.encode()).hexdigest() if self.status == "Active" else None

	def validate_manager(self):
		get_primary_school(required=True)
		if not is_platform_admin() and "Padars School Manager" not in frappe.get_roles():
			frappe.throw(_("Only a School Manager can assign academic scopes."), frappe.PermissionError)

	def validate_scope_school(self):
		school = get_primary_school(required=True)
		if self.scope_type == "Student Group":
			if frappe.db.get_value("Student Group", self.scope_name, "padars_school") != school:
				frappe.throw(_("The Student Group must belong to this School."), frappe.PermissionError)
		elif self.scope_type == "School Course Offering":
			if frappe.db.get_value("School Course Offering", self.scope_name, "school") != school:
				frappe.throw(_("The Course Offering must belong to this School."), frappe.PermissionError)

	def validate_assignment_type(self):
		if self.status != "Active":
			return
		if self.assignment_type == "Teacher":
			if self.scope_type != "School Course Offering" or not self.instructor:
				frappe.throw(_("A Teacher assignment must target a Course Offering and Instructor."))
			mapped_user = frappe.db.get_value("Instructor", self.instructor, "padars_user")
			offering_instructor = frappe.db.get_value("School Course Offering", self.scope_name, "instructor")
			if mapped_user != self.user or offering_instructor != self.instructor:
				frappe.throw(_("The Teacher User and Instructor must match the Course Offering assignment."))
		elif self.assignment_type == "Grade Coordinator":
			if self.scope_type != "Program":
				frappe.throw(_("A Grade Coordinator must be assigned to a Program."))
			if not frappe.db.get_value("Program", self.scope_name, "padars_grade_level"):
				frappe.throw(_("A Grade Coordinator's Program must have a Grade Level."))
		elif self.assignment_type == "Class Supervisor":
			if self.scope_type != "Student Group" or not frappe.db.get_value(
				"Student Group", self.scope_name, "padars_is_class_section"
			):
				frappe.throw(_("A Class Supervisor must be assigned to a Padars class section."))
		elif not STAFF_ROLES.intersection(frappe.get_roles(self.user)):
			frappe.throw(_("Scoped Staff assignments require an existing Padars staff role."))

		if self.status == "Active" and self.assignment_type in ASSIGNMENT_ROLES:
			from padars.staff import _grant_scoped_role

			_grant_scoped_role(self.user, ASSIGNMENT_ROLES[self.assignment_type])
		if self.can_manage_student_care:
			self.can_view_sensitive = 1
		if self.status == "Active" and (self.can_view_sensitive or self.can_manage_student_care):
			from padars.staff import _grant_scoped_role

			_grant_scoped_role(self.user, "Padars Sensitive Records")
