frappe.ui.form.on("Student Attendance", {
  refresh(frm) {
    if (frm.doc.student_group && frm.doc.student) {
      frm.set_intro(__("Student attendance is validated by Education against the selected group."));
    }
  },
});
