frappe.ui.form.on("Program Enrollment", {
  onload(frm) {
    padars.school_context.loadAuthorizedSchools(frm, "padars_school", "academic_year");
    padars.school_context.setAcademicTermQuery(frm, "academic_year", "academic_term");
    // A student belongs to this site and may not have an enrollment yet.
    frm.set_query("student", () => ({ filters: { enabled: 1 } }));
  },

  padars_school(frm) {
    padars.school_context.clearFields(frm, ["academic_year", "academic_term", "program"]);
    padars.school_context.setSchoolYearFromContext(frm, "padars_school", "academic_year");
  },

  academic_year(frm) {
    if (frm.doc.academic_term) frm.set_value("academic_term", null);
    padars.school_context.setAcademicTermQuery(frm, "academic_year", "academic_term");
  },
});
