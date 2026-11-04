frappe.ui.form.on("Assessment Result", {
  onload(frm) {
    padars.school_context.setAcademicTermQuery(frm, "academic_year", "academic_term");
    padars.school_context.setProgramCourseQuery(frm, "course", "program");
    padarsConfigureAssessmentResultOfferingQuery(frm);
  },

  academic_year(frm) {
    padars.school_context.setAcademicTermQuery(frm, "academic_year", "academic_term");
    padarsConfigureAssessmentResultOfferingQuery(frm);
  },

  student_group(frm) {
    padarsConfigureAssessmentResultOfferingQuery(frm);
  },

  course(frm) {
    padarsConfigureAssessmentResultOfferingQuery(frm);
  },
});

function padarsConfigureAssessmentResultOfferingQuery(frm) {
  if (!padars.school_context.hasField(frm, "padars_course_offering")) return;
  frm.set_query("padars_course_offering", () => ({
    filters: {
      academic_year: frm.doc.academic_year || "",
      student_group: frm.doc.student_group || "",
      course: frm.doc.course || "",
    },
  }));
}
