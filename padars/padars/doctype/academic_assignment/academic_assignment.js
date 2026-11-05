frappe.ui.form.on("Academic Assignment", {
  setup(frm) {
    frm.set_query("scope_type", () => ({
      filters: { name: ["in", ["Program", "Student Group", "School Course Offering"]] },
    }));
  },
});
