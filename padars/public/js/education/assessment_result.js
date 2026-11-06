frappe.ui.form.on("Assessment Result", {
  refresh(frm) {
    if (frm.doc.docstatus !== 1 || !["Padars School Manager", "Padars Platform Administrator", "System Manager"].some((role) => frappe.user.has_role(role))) return;
    frm.add_custom_button(__("Correct Result"), () => frappe.prompt([
      {fieldname: "reason", fieldtype: "Small Text", label: __("Correction Reason"), reqd: 1},
    ], ({reason}) => frappe.call({method: "padars.assessment.correct_assessment_result", args: {
      result: frm.doc.name, expected_modified: frm.doc.modified, reason,
    }}).then(({message}) => frappe.set_route("Form", "Assessment Result", message.name)),
    __("Create Correction Draft"), __("Create Draft")));
  },
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
