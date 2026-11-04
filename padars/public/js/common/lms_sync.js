(function () {
  const padars = (window.padars = window.padars || {});
  const lms = (padars.lms = padars.lms || {});

  lms.getLatestOperation = function (targetDoctype, targetName) {
    return frappe.call({
      method: "frappe.client.get_list",
      args: {
        doctype: "LMS Sync Operation",
        fields: [
          "name",
          "school",
          "operation_type",
          "target_doctype",
          "target_name",
          "state",
          "attempt_count",
          "last_attempt_at",
          "next_retry_at",
          "last_error",
          "modified",
        ],
        filters: { target_doctype: targetDoctype, target_name: targetName },
        order_by: "modified desc",
        limit_page_length: 1,
      },
    }).then((response) => (response.message || [])[0] || null);
  };

  lms.getMapping = function (localDoctype, localName) {
    return frappe.call({
      method: "frappe.client.get_list",
      args: {
        doctype: "LMS Entity Mapping",
        fields: ["name", "remote_type", "remote_id", "remote_context", "status", "last_verified_at"],
        filters: { local_doctype: localDoctype, local_name: localName, status: "Active" },
        order_by: "modified desc",
        limit_page_length: 1,
      },
    }).then((response) => (response.message || [])[0] || null);
  };

  lms.labelForState = function (state) {
    return {
      Pending: __("Pending"),
      Queued: __("Pending"),
      Running: __("Processing"),
      Succeeded: __("Successful"),
      Failed: __("Failed"),
    }[state] || __("Not requested");
  };

  lms.statusClass = function (state) {
    if (state === "Succeeded") return "success";
    if (state === "Failed") return "failed";
    if (state === "Running") return "running";
    return "pending";
  };

  lms.indicatorColor = function (state) {
    if (state === "Succeeded") return "green";
    if (state === "Failed") return "red";
    if (state === "Running") return "blue";
    return "orange";
  };

  lms.safeError = function (value) {
    return String(value || "").replace(/\s+/g, " ").trim().slice(0, 240);
  };
})();
