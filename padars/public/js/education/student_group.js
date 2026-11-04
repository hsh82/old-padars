frappe.ui.form.on("Student Group", {
  onload(frm) {
    padars.school_context.loadAuthorizedSchools(frm, "padars_school", "academic_year");
    padars.school_context.setAcademicTermQuery(frm, "academic_year", "academic_term");
    padars.school_context.setSchoolGridStudentQuery(
      frm,
      "students",
      "student",
      "padars_school",
      () => ({
        academic_year: frm.doc.academic_year || "",
        program: frm.doc.program || "",
        course: frm.doc.course || "",
      }),
    );
    padars.school_context.setSchoolGridInstructorQuery(frm, "instructors", "instructor", "padars_school");
    padars.school_context.setProgramCourseQuery(frm, "course", "program");
  },

  padars_school(frm) {
    if (frm.is_new()) {
      padars.school_context.clearFields(frm, ["academic_year", "academic_term", "program", "course"]);
      padars.school_context.setSchoolYearFromContext(frm, "padars_school", "academic_year");
    } else {
      frappe.show_alert({
        message: __("Changing School does not move existing group members. Review the roster before saving."),
        indicator: "orange",
      });
    }
    padars.school_context.setAcademicTermQuery(frm, "academic_year", "academic_term");
  },

  academic_year(frm) {
    if (frm.doc.academic_term) frm.set_value("academic_term", null);
    padars.school_context.setAcademicTermQuery(frm, "academic_year", "academic_term");
  },

  program(frm) {
    if (frm.doc.course) frm.set_value("course", null);
    if (frm.doc.students && frm.doc.students.length) {
      frappe.show_alert({ message: __("Review existing students after changing Program."), indicator: "orange" });
    }
  },

  refresh(frm) {
    if (!frm.doc.max_strength || !frm.doc.students) return;
    if (frm.doc.students.length >= frm.doc.max_strength) {
      frm.dashboard.set_headline_alert(
        __("This group is at or above its configured capacity."),
        "orange",
      );
    }
  },
});
