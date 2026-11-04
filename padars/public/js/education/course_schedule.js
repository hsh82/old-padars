frappe.ui.form.on("Course Schedule", {
  onload(frm) {
    configureOfferingQuery(frm);
  },

  student_group(frm) {
    configureOfferingQuery(frm);
  },

  course(frm) {
    configureOfferingQuery(frm);
  },
});

function configureOfferingQuery(frm) {
  if (!padars.school_context.hasField(frm, "padars_course_offering")) return;
  frm.set_query("padars_course_offering", () => ({
    filters: {
      student_group: frm.doc.student_group || "",
      course: frm.doc.course || "",
    },
  }));
}
