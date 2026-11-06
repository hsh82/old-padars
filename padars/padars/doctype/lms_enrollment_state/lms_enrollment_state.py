import hashlib

import frappe
from frappe import _
from frappe.model.document import Document

from padars.permissions import has_school_access


class LMSEnrollmentState(Document):
	def validate(self):
		old = self.get_doc_before_save()
		if old:
			if any(self.get(field) != old.get(field) for field in ("school", "user", "course_offering", "role")):
				frappe.throw(_("An existing Moodle enrollment identity cannot be changed."))
			self.desired_revision = int(old.desired_revision or 1) + int(self.desired_state != old.desired_state)
		else:
			if self.desired_state == "Not Enrolled":
				frappe.throw(_("Only an existing enrollment can be withdrawn."))
			self.desired_revision = max(1, int(self.desired_revision or 1))
		self.enrollment_key = hashlib.sha256(
			f"{self.school}\0{self.user}\0{self.course_offering}\0{self.role}".encode()
		).hexdigest()
		if not has_school_access(self.school):
			frappe.throw(_("You do not have access to School {0}.").format(self.school), frappe.PermissionError)

		offering = frappe.db.get_value(
			"School Course Offering", self.course_offering,
			["school", "student_group", "program", "academic_year", "instructor"], as_dict=True
		)
		if not offering:
			frappe.throw(_("Course Offering {0} does not exist.").format(self.course_offering))
		if offering.school != self.school:
			frappe.throw(_("The enrollment state School must match the Course Offering School."))
		if self.desired_state == "Enrolled" and not frappe.db.exists("User", {"name": self.user, "enabled": 1, "user_type": "System User"}):
			frappe.throw(_("The Moodle account must be linked to an enabled System User."))

		if self.desired_state == "Not Enrolled":
			pass  # Withdrawal must remain possible after local eligibility is removed.
		elif self.role == "Student":
			student = frappe.db.get_value("Student", {"user": self.user, "enabled": 1}, "name")
			if not student or not frappe.db.exists(
				"Student Group Student",
				{"parent": offering.student_group, "student": student, "active": 1},
			):
				frappe.throw(_("The Student must be enabled and an active member of the Course Offering group."))
			if not frappe.db.exists(
				"Program Enrollment",
				{
					"student": student,
					"program": offering.program,
					"academic_year": offering.academic_year,
					"docstatus": 1,
				},
			):
				frappe.throw(_("The Student needs a submitted Program Enrollment for this Course Offering."))
		elif self.role == "Teacher":
			if not offering.instructor or not frappe.get_meta("Instructor").has_field("padars_user"):
				frappe.throw(_("Assign an Instructor with a Padars User mapping before enrolling a Teacher."))
			if frappe.db.get_value("Instructor", offering.instructor, "padars_user") != self.user:
				frappe.throw(_("The Teacher must match the User mapped to the Course Offering's Instructor."))
		elif self.role == "School Manager":
			if frappe.db.get_value("School", self.school, "primary_school_manager") != self.user:
				frappe.throw(_("The School Manager enrollment must use this School's primary manager."))

		filters = {"enrollment_key": self.enrollment_key}
		if self.name:
			filters["name"] = ["!=", self.name]
		if frappe.db.exists("LMS Enrollment State", filters):
			frappe.throw(_("This user already has an enrollment state for this offering and role."))
