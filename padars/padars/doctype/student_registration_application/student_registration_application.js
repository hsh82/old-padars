frappe.ui.form.on("Student Registration Application", {
  refresh(frm) {
    if (!frm.is_new() && frm.doc.status === "Submitted") {
      frm.add_custom_button(__("Approve"), () => frappe.call({
        method: "padars.student_application.approve", args: {application: frm.doc.name}, freeze: true,
      }).then(() => frm.reload_doc()));
      frm.add_custom_button(__("Reject"), () => frappe.call({
        method: "padars.student_application.reject", args: {application: frm.doc.name}, freeze: true,
      }).then(() => frm.reload_doc()));
    }
  },
});
