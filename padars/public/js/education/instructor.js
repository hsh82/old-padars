frappe.ui.form.on("Instructor", {
  setup(frm) {
    frm.set_query("padars_user", () => ({
      filters: { enabled: 1, user_type: "System User" },
    }));
  },

  refresh(frm) {
    const isManager = frappe.user.has_role("Padars School Manager")
      || frappe.user.has_role("Padars Moodle Manager")
      || frappe.user.has_role("Padars Platform Administrator")
      || frappe.user.has_role("System Manager");
    if (frm.is_new() || !isManager) return;
    frm.remove_custom_button(__("Link Frappe User"), __("Staff"));
    frm.add_custom_button(__("Link Frappe User"), () => {
      frappe.prompt([
        {
          fieldtype: "Link",
          fieldname: "user",
          label: __("Frappe User"),
          options: "User",
          default: frm.doc.padars_user || "",
          reqd: 1,
          get_query: () => ({ filters: { enabled: 1, user_type: "System User" } }),
        },
      ], (values) => {
        frappe.call({
          method: "padars.integrations.moodle.teacher_identity.link_instructor_to_user",
          args: { instructor: frm.doc.name, user: values.user },
        }).then(() => frm.reload_doc());
      }, __("Link Instructor to User"), __("Link"));
    }, __("Staff"));
  },
});
