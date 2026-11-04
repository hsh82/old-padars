frappe.ui.form.on("Assessment Result Tool", {
  refresh(frm) {
    if (frm.doc.assessment_plan) {
      frm.set_intro(__("Assessment result entry remains subject to server-side plan and score validation."));
    }
  },
});
