frappe.ui.form.on("Program Enrollment", {
  onload(frm) {
    padars.school_context.loadAuthorizedSchools(frm, "padars_school", "academic_year");
    padars.school_context.setAcademicTermQuery(frm, "academic_year", "academic_term");
    setStudentQuery(frm);
  },

  padars_school(frm) {
    padars.school_context.clearFields(frm, ["academic_year", "academic_term", "student", "program"]);
    padars.school_context.setSchoolYearFromContext(frm, "padars_school", "academic_year");
    setStudentQuery(frm);
  },

  academic_year(frm) {
    if (frm.doc.academic_term) frm.set_value("academic_term", null);
    if (frm.doc.student) frm.set_value("student", null);
    padars.school_context.setAcademicTermQuery(frm, "academic_year", "academic_term");
    setStudentQuery(frm);
  },

  program(frm) {
    if (frm.doc.student) frm.set_value("student", null);
    setStudentQuery(frm);
  },
});

function setStudentQuery(frm) {
  padars.school_context.setSchoolStudentQuery(frm, "student", "padars_school", () => ({
    academic_year: frm.doc.academic_year || "",
    program: frm.doc.program || "",
  }));
}
