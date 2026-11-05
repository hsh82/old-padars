"""Annual curriculum snapshots composed from Education academic records."""

import hashlib

import frappe
from frappe import _
from frappe.model.document import Document

from padars.permissions import can_manage_school, is_platform_admin
from padars.school_context import get_primary_school


GRADE_LEVELS = {str(value) for value in range(7, 13)}


def _digest(value):
	return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _require_school_manager():
	school = get_primary_school(required=True)
	if not is_platform_admin() and not can_manage_school(school):
		frappe.throw(_("Only a school manager can configure curriculum."), frappe.PermissionError)
	return school


def validate_program(doc, method=None):
	grade = str(doc.get("padars_grade_level") or "").strip()
	stream = " ".join(str(doc.get("padars_stream") or "").split())
	doc.padars_grade_level = grade or None
	doc.padars_stream = stream or None
	courses = [row.course for row in doc.courses if row.course]
	if len(courses) != len(set(courses)):
		frappe.throw(_("A Program can include a Course only once."))
	if bool(grade) != bool(stream):
		frappe.throw(_("Set both Grade Level and Stream, or leave both empty."))
	if grade and grade not in GRADE_LEVELS:
		frappe.throw(_("Padars Programs must use Grade Levels 7 through 12."))
	if not grade:
		doc.padars_grade_stream_key = None
		return

	key = f"{grade}:{stream.casefold()}"
	doc.padars_grade_stream_key = _digest(key)
	duplicate = frappe.db.exists("Program", {
		"padars_grade_stream_key": _digest(key),
		"name": ["!=", doc.name or ""],
	})
	if duplicate:
		frappe.throw(_("A Program already exists for Grade {0} / {1}.").format(grade, stream))


class SchoolCurriculumAdoption(Document):
	def validate(self):
		self.validate_scope()
		self.validate_template()
		self.validate_courses()
		self.validate_version()
		self.validate_history()

	def validate_scope(self):
		if not frappe.db.exists("School", {"name": self.school, "status": "Active"}):
			frappe.throw(_("Choose an active School."))
		if not is_platform_admin() and self.school != get_primary_school(required=True):
			frappe.throw(_("A manager may adopt a curriculum only for their School."), frappe.PermissionError)
		if not frappe.db.exists("Academic Year", self.academic_year):
			frappe.throw(_("The Academic Year does not exist."))

	def validate_template(self):
		program = frappe.db.get_value("Program", self.program,
			["program_name", "padars_grade_level", "padars_stream"], as_dict=True)
		if not program or not program.padars_grade_level or not program.padars_stream:
			frappe.throw(_("Choose an Education Program configured with a Grade Level and Stream."))
		if program.padars_grade_level not in GRADE_LEVELS:
			frappe.throw(_("The Program Grade Level must be between 7 and 12."))
		self.adoption_title = _("{0} · {1} · v{2}").format(
			self.academic_year, program.program_name, self.version
		)
		if not self.source_program_modified:
			self.source_program_modified = frappe.db.get_value("Program", self.program, "modified")

	def validate_courses(self):
		seen = set()
		for row in self.courses:
			if not row.course or not frappe.db.exists("Course", row.course):
				frappe.throw(_("Every curriculum row must link to an Education Course."))
			if row.course in seen:
				frappe.throw(_("A curriculum can include a Course only once."))
			seen.add(row.course)
			if row.weekly_hours is None:
				row.weekly_hours = 0
			if float(row.weekly_hours) < 0:
				frappe.throw(_("Expected weekly hours cannot be negative."))
			if not row.course_name:
				row.course_name = frappe.db.get_value("Course", row.course, "course_name")
		if self.status == "Active" and not self.courses:
			frappe.throw(_("Add at least one Course before activating this curriculum."))

	def validate_version(self):
		if int(self.version or 0) < 1:
			frappe.throw(_("Curriculum version must be a positive integer."))
		if self.is_new():
			latest = frappe.db.sql("""
				select coalesce(max(version), 0) from `tabSchool Curriculum Adoption`
				where school=%s and academic_year=%s and program=%s
			""", (self.school, self.academic_year, self.program))[0][0]
			if int(self.version) != int(latest) + 1:
				frappe.throw(_("Curriculum versions must be created in sequence."))
		self.version_key = _digest(f"{self.school}|{self.academic_year}|{self.program}|{self.version}")
		self.active_key = (
			_digest(f"{self.school}|{self.academic_year}|{self.program}")
			if self.status == "Active" else None
		)
		if self.status == "Active":
			other = frappe.db.exists("School Curriculum Adoption", {
				"school": self.school,
				"academic_year": self.academic_year,
				"program": self.program,
				"status": "Active",
				"name": ["!=", self.name or ""],
			})
			if other:
				frappe.throw(_("Archive the current adoption before activating another version."))

	def validate_history(self):
		old = self.get_doc_before_save()
		if not old or old.status == "Draft":
			return
		unchanged = (
			old.school == self.school
			and old.academic_year == self.academic_year
			and old.program == self.program
			and old.version == self.version
			and old.source_program_modified == self.source_program_modified
			and _course_state(old.courses) == _course_state(self.courses)
		)
		if not unchanged:
			frappe.throw(_("An activated curriculum snapshot is immutable."))
		if old.status == "Archived" and self.status != "Archived":
			frappe.throw(_("An archived curriculum version cannot be reactivated."))
		if old.status == "Active" and self.status not in {"Active", "Archived"}:
			frappe.throw(_("An active curriculum may only be archived."))


def _course_state(rows):
	return [(row.course, row.course_name, int(row.required or 0), float(row.weekly_hours or 0)) for row in rows]


@frappe.whitelist(methods=["POST"])
def create_curriculum_adoption_from_program(program, academic_year):
	school = _require_school_manager()
	program_doc = frappe.get_doc("Program", program)
	program_doc.check_permission("read")
	if not program_doc.padars_grade_level or not program_doc.padars_stream:
		frappe.throw(_("Configure Grade Level and Stream on the Program first."))
	if not program_doc.courses:
		frappe.throw(_("Add Courses to the Education Program before adopting it."))
	year_doc = frappe.get_doc("Academic Year", academic_year)
	year_doc.check_permission("read")
	# Serialize version allocation for this year; the unique version key is the
	# final guard if another writer races this transaction.
	frappe.db.sql("select name from `tabAcademic Year` where name=%s for update", academic_year)
	previous = frappe.get_list("School Curriculum Adoption",
		filters={"school": school, "academic_year": academic_year, "program": program},
		fields=["version"], order_by="version desc", page_length=1)
	version = int(previous[0].version) + 1 if previous else 1
	doc = frappe.get_doc({"doctype": "School Curriculum Adoption", "school": school,
		"academic_year": academic_year, "program": program, "version": version,
		"source_program_modified": program_doc.modified, "status": "Draft"})
	for row in program_doc.courses:
		doc.append("courses", {"course": row.course, "course_name": row.course_name,
			"required": row.required, "weekly_hours": 0})
	doc.insert()
	return {"name": doc.name, "version": doc.version, "status": doc.status}


def validate_student_group(doc, method=None):
	if doc.academic_term:
		term_year = frappe.db.get_value("Academic Term", doc.academic_term, "academic_year")
		if term_year != doc.academic_year:
			frappe.throw(_("The Academic Term must belong to the Student Group's Academic Year."))

	is_section = bool(doc.get("padars_is_class_section"))
	if not is_section and not doc.get("padars_curriculum_adoption"):
		doc.padars_section_code = None
		doc.padars_class_section_key = None
		for row in doc.students:
			row.padars_class_assignment_key = None
		return
	if not is_section or doc.group_based_on != "Batch":
		frappe.throw(_("A curriculum adoption can only be linked to a Batch class section."))
	if not is_platform_admin() and not can_manage_school(doc.padars_school):
		frappe.throw(_("Only a School Manager can configure class sections."), frappe.PermissionError)
	if not doc.padars_section_code or not doc.padars_curriculum_adoption:
		frappe.throw(_("A class section requires a Section Code and Curriculum Adoption."))
	adoption = frappe.db.get_value("School Curriculum Adoption", doc.padars_curriculum_adoption,
		["school", "academic_year", "program", "status"], as_dict=True)
	old = doc.get_doc_before_save()
	retained_archived_adoption = bool(old and old.padars_curriculum_adoption == doc.padars_curriculum_adoption)
	if not adoption or (adoption.status != "Active" and not (adoption.status == "Archived" and retained_archived_adoption)):
		frappe.throw(_("Choose an active Curriculum Adoption."))
	if (adoption.school != doc.padars_school or adoption.academic_year != doc.academic_year
			or adoption.program != doc.program):
		frappe.throw(_("The class section School, year, and Program must match its Curriculum Adoption."))
	code = " ".join(str(doc.padars_section_code).split()).casefold()
	doc.padars_section_code = " ".join(str(doc.padars_section_code).split())
	doc.padars_class_section_key = _digest(
		f"{doc.padars_school}|{doc.academic_year}|{doc.program}|{code}"
	)
	if frappe.db.exists("Student Group", {
		"padars_class_section_key": doc.padars_class_section_key,
		"name": ["!=", doc.name or ""],
	}):
		frappe.throw(_("A class section with this code already exists for the School, year, and Program."))
	if _has_school_offerings(doc.name):
		fixed = ("padars_school", "academic_year", "program", "group_based_on",
			"padars_is_class_section", "padars_section_code", "padars_curriculum_adoption")
		if old and any(old.get(field) != doc.get(field) for field in fixed):
			frappe.throw(_("A class section with Course Offerings cannot change its academic identity."))
	_validate_class_roster(doc)


def _has_school_offerings(group_name):
	return bool(group_name and frappe.db.exists("School Course Offering", {"student_group": group_name}))


def _validate_class_roster(doc):
	if not doc.students:
		return
	for row in doc.students:
		if not row.active:
			row.padars_class_assignment_key = None
			continue
		row.padars_class_assignment_key = _digest(
			f"{doc.padars_school}|{doc.academic_year}|{doc.program}|{row.student}"
		)
		frappe.db.sql("select name from `tabStudent` where name=%s for update", row.student)
		other = frappe.db.sql("""
			select sg.name from `tabStudent Group Student` sgs
			join `tabStudent Group` sg on sg.name=sgs.parent
			where sgs.student=%s and sgs.active=1 and sg.name!=%s
			and sg.padars_is_class_section=1 and sg.padars_school=%s
			and sg.academic_year=%s and sg.program=%s limit 1
		""", (row.student, doc.name, doc.padars_school, doc.academic_year, doc.program))
		if other:
			frappe.throw(_("Student {0} is already assigned to class section {1} for this Program and year.").format(
				row.student, other[0][0]))


@frappe.whitelist(methods=["POST"])
def add_enrolled_students_to_section(student_group):
	school = _require_school_manager()
	group = frappe.get_doc("Student Group", student_group)
	group.check_permission("write")
	if not group.padars_is_class_section or group.padars_school != school:
		frappe.throw(_("Choose an authorized Padars class section."), frappe.PermissionError)
	if not group.padars_curriculum_adoption:
		frappe.throw(_("The class section has no Curriculum Adoption."))
	frappe.db.sql("select name from `tabStudent Group` where name=%s for update", student_group)
	group.reload()
	filters = {"padars_school": school, "academic_year": group.academic_year,
		"program": group.program, "docstatus": 1}
	if group.academic_term:
		filters["academic_term"] = group.academic_term
	student_names = set()
	start = 0
	while True:
		enrollments = frappe.get_list("Program Enrollment", filters=filters,
			fields=["student"], order_by="student asc", start=start, page_length=500)
		student_names.update(row.student for row in enrollments)
		if len(enrollments) < 500:
			break
		start += len(enrollments)
	student_names = sorted(student_names)
	if not student_names:
		return {"added": 0, "total": len(group.students)}
	students = []
	for offset in range(0, len(student_names), 500):
		students.extend(frappe.get_list("Student", filters={
			"name": ["in", student_names[offset:offset + 500]], "enabled": 1,
		}, fields=["name", "student_name"], order_by="student_name asc", page_length=500))
	known = {row.student: row for row in group.students}
	added = 0
	for student in students:
		if student.name in known:
			if not known[student.name].active:
				known[student.name].active = 1
				added += 1
			continue
		group.append("students", {"student": student.name, "student_name": student.student_name, "active": 1})
		added += 1
	if added:
		group.save()
	return {"added": added, "total": len(group.students)}


@frappe.whitelist(methods=["POST"])
def generate_course_offerings(student_group):
	school = _require_school_manager()
	group = frappe.get_doc("Student Group", student_group)
	group.check_permission("write")
	if not group.padars_is_class_section or group.padars_school != school:
		frappe.throw(_("Choose an authorized Padars class section."), frappe.PermissionError)
	if not group.padars_curriculum_adoption:
		frappe.throw(_("The class section has no Curriculum Adoption."))
	frappe.db.sql("select name from `tabStudent Group` where name=%s for update", student_group)
	group.reload()
	adoption = frappe.get_doc("School Curriculum Adoption", group.padars_curriculum_adoption)
	adoption.check_permission("read")
	if adoption.status not in {"Active", "Archived"}:
		frappe.throw(_("Course Offerings require an active or archived Curriculum Adoption."))
	if (adoption.school != school or adoption.academic_year != group.academic_year
			or adoption.program != group.program):
		frappe.throw(_("The class section does not match its Curriculum Adoption."))
	created, reused, names = 0, 0, []
	for row in adoption.courses:
		filters = {"school": school, "academic_year": group.academic_year,
			"course": row.course, "student_group": group.name}
		existing = frappe.get_list("School Course Offering", filters=filters,
			fields=["name", "curriculum_adoption", "status"], page_length=2)
		if len(existing) > 1:
			frappe.throw(_("Duplicate Course Offerings already exist for this class."))
		if existing:
			offering = frappe.get_doc("School Course Offering", existing[0].name)
			if offering.curriculum_adoption not in (None, "", adoption.name):
				frappe.throw(_("An existing Course Offering belongs to another curriculum version."))
			if not offering.curriculum_adoption:
				if offering.status != "Draft":
					frappe.throw(_("Review the existing non-draft Course Offering before linking it to this curriculum."))
				offering.curriculum_adoption = adoption.name
				offering.save()
			reused += 1
			names.append(offering.name)
			continue
		identifier = _offering_identifier(group.padars_section_code, row.course)
		offering = frappe.get_doc({"doctype": "School Course Offering", "school": school,
			"academic_year": group.academic_year, "program": group.program, "course": row.course,
			"student_group": group.name, "offering_identifier": identifier,
			"curriculum_adoption": adoption.name, "curriculum_course_required": row.required,
			"expected_weekly_hours": row.weekly_hours, "status": "Draft"}).insert()
		created += 1
		names.append(offering.name)
	return {"created": created, "reused": reused, "offerings": names}


def validate_offering_curriculum(doc, method=None):
	"""Keep annual offering context derived from its Education class group."""
	group = frappe.db.get_value("Student Group", doc.student_group,
		["academic_year", "academic_term", "program", "course", "group_based_on",
			"padars_school", "padars_is_class_section", "padars_curriculum_adoption"], as_dict=True)
	if not group:
		frappe.throw(_("The Student Group does not exist."))
	if group.academic_year != doc.academic_year:
		frappe.throw(_("The Student Group must belong to the offering's Academic Year."))
	if group.program and group.program != doc.program:
		frappe.throw(_("The Student Group Program does not match the offering."))
	if group.group_based_on == "Course" and group.course != doc.course:
		frappe.throw(_("The Student Group Course does not match the offering."))
	if group.padars_school != doc.school:
		frappe.throw(_("The Student Group belongs to another School."))
	if doc.academic_term and doc.academic_term != group.academic_term:
		frappe.throw(_("The Academic Term is derived from the Student Group."))
	doc.academic_term = group.academic_term

	if not group.padars_is_class_section:
		if doc.curriculum_adoption:
			frappe.throw(_("A curriculum adoption can only be used by its linked class section."))
		doc.curriculum_course_required = 0
		doc.expected_weekly_hours = 0
		return

	if not group.padars_curriculum_adoption:
		frappe.throw(_("The class section must have a Curriculum Adoption."))
	if doc.curriculum_adoption and doc.curriculum_adoption != group.padars_curriculum_adoption:
		frappe.throw(_("The offering Curriculum Adoption must match its class section."))
	adoption = frappe.get_doc("School Curriculum Adoption", group.padars_curriculum_adoption)
	if (adoption.school != doc.school or adoption.academic_year != doc.academic_year
			or adoption.program != doc.program):
		frappe.throw(_("The offering context does not match its Curriculum Adoption."))
	if adoption.status not in {"Active", "Archived"}:
		frappe.throw(_("Course Offerings require an active or archived Curriculum Adoption."))
	curriculum_course = next((row for row in adoption.courses if row.course == doc.course), None)
	if not curriculum_course:
		frappe.throw(_("The Course is not included in the class section's Curriculum Adoption."))
	doc.curriculum_adoption = adoption.name
	doc.curriculum_course_required = curriculum_course.required
	doc.expected_weekly_hours = curriculum_course.weekly_hours


def _offering_identifier(section_code, course):
	readable = f"{section_code}-{course}"
	if len(readable) <= 140:
		return readable
	return f"{section_code[:48]}-{course[:48]}-{_digest(readable)[:12]}"
