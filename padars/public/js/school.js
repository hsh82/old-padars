frappe.ui.form.on("School", {
  refresh(frm) {
    if (frm.is_new()) return;
    const operator = isMoodleOperator();
    const manager = operator || frappe.user.has_role("Padars School Manager");

    frm.remove_custom_button(__("Enable Moodle"), __("Moodle"));
    frm.remove_custom_button(__("Disable Moodle"), __("Moodle"));
    frm.remove_custom_button(__("Reconnect Moodle Tenant"), __("Moodle"));
    frm.remove_custom_button(__("Check Moodle Connection"), __("Moodle"));
    frm.remove_custom_button(__("View LMS Synchronization"), __("Moodle"));
    frm.remove_custom_button(__("Open Moodle"), __("Moodle"));

    if (operator) {
      frm.add_custom_button(
        frm.doc.lms_enabled ? __("Disable Moodle") : __("Enable Moodle"),
        () => setMoodleEnabled(frm, !frm.doc.lms_enabled),
        __("Moodle"),
      );
      if (frm.doc.lms_enabled) {
        frm.add_custom_button(__("Reconnect Moodle Tenant"), () => reconnectMoodle(frm), __("Moodle"));
        frm.add_custom_button(__("Check Moodle Connection"), checkMoodleConnection, __("Moodle"));
      }
    }

    if (manager) {
      frm.add_custom_button(__("View LMS Synchronization"), () => openSchoolSyncMonitor(frm), __("Moodle"));
    }
    if (frm.doc.lms_enabled && frm.doc.lms_moodle_url && manager) {
      frm.add_custom_button(__("Open Moodle"), () => window.open(frm.doc.lms_moodle_url, "_blank", "noopener"), __("Moodle"));
    }

    if (frm.doc.lms_status) {
      frm.page.set_indicator(frm.doc.lms_status, statusColor(frm.doc.lms_status));
    }
    if (frm.doc.lms_last_error) {
      frm.set_intro(padars.lms.safeError(frm.doc.lms_last_error), "red");
    }
  },
});

function isMoodleOperator() {
  return frappe.user.has_role("Padars Moodle Manager")
    || frappe.user.has_role("Padars Platform Administrator")
    || frappe.user.has_role("System Manager");
}

function statusColor(status) {
  return { Connected: "green", Provisioning: "blue", Error: "red", Disabled: "gray" }[status] || "gray";
}

function setMoodleEnabled(frm, enabled) {
  const message = enabled
    ? __("Enable Moodle and start tenant provisioning for this School?")
    : __("Disable Moodle synchronization? The existing tenant and Moodle data will be preserved.");
  frappe.confirm(message, () => {
    frappe.call({
      method: "padars.api.set_school_lms_enabled",
      args: { school: frm.doc.name, enabled: enabled ? 1 : 0 },
    }).then(() => frm.reload_doc())
      .catch(() => frappe.msgprint(__("The Moodle setting could not be changed.")));
  });
}

function reconnectMoodle(frm) {
  frappe.call({
    method: "padars.api.reconnect_school_lms",
    args: { school: frm.doc.name },
  }).then(() => {
    frappe.show_alert({ message: __("Moodle tenant verification queued."), indicator: "blue" });
    frm.reload_doc();
  }).catch(() => frappe.msgprint(__("The Moodle tenant could not be queued for verification.")));
}

function checkMoodleConnection() {
  frappe.call({ method: "padars.api.check_moodle_connection" }).then(({ message }) => {
    frappe.msgprint({
      title: __("Moodle Connection"),
      message: __("Connected to {0} (Moodle {1}).", [message.sitename || "Moodle", message.release || "version unavailable"]),
    });
  }).catch(() => frappe.msgprint(__("The Moodle connection check failed.")));
}

function openSchoolSyncMonitor(frm) {
  frappe.route_options = { school: frm.doc.name };
  frappe.set_route("lms-sync-monitor");
}
