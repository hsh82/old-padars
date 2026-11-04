frappe.ui.form.on("School", {
  refresh(frm) {
    if (frm.is_new()) return;
    frm.remove_custom_button(__("Request Moodle Tenant Provisioning"), __("Moodle"));
    frm.remove_custom_button(__("View LMS Synchronization"), __("Moodle"));
    frm.add_custom_button(
      __("Request Moodle Tenant Provisioning"),
      () => requestTenantProvisioning(frm),
      __("Moodle"),
    );
    frm.add_custom_button(
      __("View LMS Synchronization"),
      () => openSchoolSyncMonitor(frm),
      __("Moodle"),
    );
    padars.lms.getLatestOperation("School", frm.doc.name).then((operation) => {
      if (!frm.page) return;
      frm.page.set_indicator(
        operation ? padars.lms.labelForState(operation.state) : __("Not requested"),
        operation ? padars.lms.indicatorColor(operation.state) : "gray",
      );
    }).catch(() => {
      if (frm.page) frm.page.set_indicator(__("Status unavailable"), "orange");
    });
  },
});

function requestTenantProvisioning(frm) {
  if (frm.__padars_tenant_busy) return;
  frm.__padars_tenant_busy = true;
  frappe.call({
    method: "padars.api.request_school_tenant_sync",
    args: { school: frm.doc.name },
  }).then(() => {
    frappe.show_alert({ message: __("Moodle tenant provisioning requested."), indicator: "blue" });
    frm.trigger("refresh");
  }).catch(() => {
    frappe.msgprint(__("The Moodle tenant provisioning request could not be submitted."));
  }).finally(() => {
    frm.__padars_tenant_busy = false;
  });
}

function openSchoolSyncMonitor(frm) {
  frappe.route_options = { target_doctype: "School", target_name: frm.doc.name };
  frappe.set_route("lms-sync-monitor");
}
