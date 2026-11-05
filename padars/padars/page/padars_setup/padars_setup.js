frappe.pages["padars-setup"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({ parent: wrapper, title: __("School Setup"), single_column: true });
  $(page.body).html(`<p class="text-muted">${__("Set up your school with its academic year and primary manager. You can return here later.")}</p>`);
  const openSetup = () => frappe.call("padars.setup.get_setup_status").then(({ message }) => {
    const current = message || {};
    const dialog = new frappe.ui.Dialog({
      title: __("School Setup"),
      fields: [
        { fieldname: "school_name", label: __("School Name"), fieldtype: "Data", reqd: 1, default: current.school_name },
        { fieldname: "school_code", label: __("School Code"), fieldtype: "Data", reqd: 1, default: current.school_code, read_only: !!current.school_code },
        { fieldname: "academic_year", label: __("Academic Year"), fieldtype: "Link", options: "Academic Year", reqd: 1, default: current.current_academic_year },
        { fieldname: "primary_manager", label: __("Primary School Manager"), fieldtype: "Link", options: "User", reqd: 1, default: current.primary_school_manager || frappe.session.user },
      ],
      primary_action_label: __("Save"),
      primary_action(values) {
        return frappe.call({ method: "padars.setup.configure_school", args: values, freeze: true }).then(() => {
          dialog.hide();
          frappe.show_alert({ message: __("School setup saved."), indicator: "green" });
          frappe.set_route("Workspaces", "Padars");
        });
      },
    });
    dialog.show();
  });
  page.set_primary_action(__("Configure School"), openSetup);
  openSetup();
};
