frappe.ui.form.on("Student", {
  refresh(frm) {
    if (frm.doc.user) {
      frm.set_intro(__("Student account linked to {0}.", [frm.doc.user]), "green");
    } else if (frm.doc.student_email_id) {
      frm.set_intro(
        __("No linked account is visible yet. Education user provisioning follows the configured site setting."),
        "orange",
      );
    }
  },
});
