frappe.ui.form.on("Academic Assignment", {
  setup(frm) {
    frm.set_query("scope_type", () => ({
      filters: { name: ["in", ["Program", "Student Group", "School Course Offering"]] },
    }));
  },

  refresh(frm) {
    frm.toggle_display("instructor", frm.doc.assignment_type === "Teacher");
  },

  assignment_type(frm) {
    frm.toggle_display("instructor", frm.doc.assignment_type === "Teacher");
    if (frm.doc.assignment_type === "Teacher") frm.set_value("scope_type", "School Course Offering");
    if (frm.doc.assignment_type === "Grade Coordinator") frm.set_value("scope_type", "Program");
    if (frm.doc.assignment_type === "Class Supervisor") frm.set_value("scope_type", "Student Group");
  },
});
