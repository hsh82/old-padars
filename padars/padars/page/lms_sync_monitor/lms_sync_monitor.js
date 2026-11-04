frappe.pages["lms-sync-monitor"].on_page_load = function (wrapper) {
  wrapper.__padars_lms_monitor = new PadarsLMSMonitor(wrapper);
};

frappe.pages["lms-sync-monitor"].on_page_show = function (wrapper) {
  if (wrapper.__padars_lms_monitor) wrapper.__padars_lms_monitor.refresh();
};

class PadarsLMSMonitor {
  constructor(wrapper) {
    this.wrapper = wrapper;
    this.page = frappe.ui.make_app_page({
      parent: wrapper,
      title: __("LMS Synchronization Monitor"),
      single_column: true,
    });
    this.makeFilters();
    this.makeLayout();
    this.applyRouteOptions();
  }

  makeFilters() {
    this.school = this.page.add_field({
      label: __("School"),
      fieldtype: "Link",
      fieldname: "school",
      options: "School",
    });
    this.state = this.page.add_field({
      label: __("Status"),
      fieldtype: "Select",
      fieldname: "state",
      options: ["", "Pending", "Queued", "Running", "Succeeded", "Failed"],
    });
    this.entityType = this.page.add_field({
      label: __("Entity Type"),
      fieldtype: "Select",
      fieldname: "target_doctype",
      options: ["", "School", "User", "School Course Offering", "LMS Enrollment State"],
    });
    this.targetName = this.page.add_field({
      label: __("Target Record"),
      fieldtype: "Data",
      fieldname: "target_name",
    });
    this.fromDate = this.page.add_field({
      label: __("From Date"),
      fieldtype: "Date",
      fieldname: "from_date",
    });
    this.toDate = this.page.add_field({
      label: __("To Date"),
      fieldtype: "Date",
      fieldname: "to_date",
    });
    [this.school, this.state, this.entityType, this.targetName, this.fromDate, this.toDate].forEach(
      (field) => field.$input && field.$input.on("change", () => this.refresh()),
    );
    this.page.add_inner_button(__("Refresh"), () => this.refresh());
    this.page.add_inner_button(__("Clear Filters"), () => this.clearFilters());
  }

  makeLayout() {
    this.body = $(this.page.body);
    this.body.addClass("padars-sync-monitor");
    this.body.html(`
      <div class="padars-sync-monitor__content">
        <div class="text-muted small mb-3">${__("Refresh manually to check the latest synchronization state.")}</div>
        <div class="padars-sync-monitor__table"></div>
      </div>
    `);
  }

  applyRouteOptions() {
    const options = frappe.route_options || {};
    if (options.school) this.school.set_value(options.school);
    if (options.state) this.state.set_value(options.state);
    if (options.target_doctype) this.entityType.set_value(options.target_doctype);
    if (options.target_name) this.targetName.set_value(options.target_name);
    frappe.route_options = null;
  }

  clearFilters() {
    [this.school, this.state, this.entityType, this.targetName, this.fromDate, this.toDate].forEach(
      (field) => field.set_value("")
    );
    this.refresh();
  }

  getFilters() {
    const filters = {};
    if (this.school.get_value()) filters.school = this.school.get_value();
    if (this.state.get_value()) filters.state = this.state.get_value();
    if (this.entityType.get_value()) filters.target_doctype = this.entityType.get_value();
    if (this.targetName.get_value()) filters.target_name = this.targetName.get_value();
    if (this.fromDate.get_value() && this.toDate.get_value()) {
      filters.modified = [
        "between",
        [`${this.fromDate.get_value()} 00:00:00`, `${this.toDate.get_value()} 23:59:59`],
      ];
    } else if (this.fromDate.get_value()) {
      filters.modified = [">=", `${this.fromDate.get_value()} 00:00:00`];
    } else if (this.toDate.get_value()) {
      filters.modified = ["<=", `${this.toDate.get_value()} 23:59:59`];
    }
    return filters;
  }

  refresh() {
    if (this.loading) return;
    this.loading = true;
    this.renderLoading();
    frappe
      .call({
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
          filters: this.getFilters(),
          order_by: "modified desc",
          limit_page_length: 50,
        },
      })
      .then((response) => this.renderRows(response.message || []))
      .catch(() => this.renderError())
      .finally(() => {
        this.loading = false;
      });
  }

  renderLoading() {
    this.body.find(".padars-sync-monitor__table").html(
      `<div class="text-muted">${__("Loading synchronization operations...")}</div>`,
    );
  }

  renderError() {
    this.body.find(".padars-sync-monitor__table").html(
      `<div class="text-danger">${__("Synchronization data could not be loaded. Check your access and try again.")}</div>`,
    );
  }

  renderRows(rows) {
    if (!rows.length) {
      this.body.find(".padars-sync-monitor__table").html(
        `<div class="text-muted">${__("No synchronization operations found.")}</div>`,
      );
      return;
    }

    const header = [
      __("School"),
      __("Entity Type"),
      __("Operation"),
      __("Target"),
      __("Status"),
      __("Last Attempt"),
      __("Error"),
      __("Actions"),
    ];
    const table = $(`<table class="table table-bordered padars-sync-table"><thead><tr></tr></thead><tbody></tbody></table>`);
    header.forEach((label) => table.find("thead tr").append($(`<th>${escapeText(label)}</th>`)));
    const tbody = table.find("tbody");
    rows.forEach((row) => tbody.append(this.renderRow(row)));
    const container = this.body.find(".padars-sync-monitor__table").empty().append(table);
    container.find("[data-action='open']").on("click", (event) => {
      const button = $(event.currentTarget);
      frappe.set_route("Form", button.data("doctype"), button.data("name"));
    });
    container.find("[data-action='mapping']").on("click", (event) => this.openMapping($(event.currentTarget)));
    container.find("[data-action='retry']").on("click", (event) => this.retry($(event.currentTarget)));
  }

  renderRow(row) {
    const stateClass = padars.lms.statusClass(row.state);
    const stateLabel = padars.lms.labelForState(row.state);
    const lastAttempt = row.last_attempt_at
      ? frappe.datetime.str_to_user(row.last_attempt_at)
      : __("Not attempted");
    const retry = row.state === "Failed"
      ? `<button class="btn btn-xs btn-secondary" data-action="retry" data-name="${escapeText(row.name)}">${escapeText(__("Retry"))}</button>`
      : "";
    return $(`
      <tr>
        <td>${escapeText(row.school || "")}</td>
        <td>${escapeText(row.target_doctype || "")}</td>
        <td>${escapeText(__(row.operation_type || ""))}</td>
        <td>${escapeText(row.target_name || "")}</td>
        <td><span class="padars-status-badge padars-status-${stateClass}">${escapeText(stateLabel)}</span></td>
        <td>${escapeText(lastAttempt)}</td>
        <td class="padars-sync-error">${escapeText(safeError(row.last_error))}</td>
        <td class="text-nowrap">
          <button class="btn btn-xs btn-secondary" data-action="open" data-doctype="${escapeText(row.target_doctype)}" data-name="${escapeText(row.target_name)}">${escapeText(__("Open"))}</button>
          <button class="btn btn-xs btn-secondary" data-action="mapping" data-doctype="${escapeText(row.target_doctype)}" data-name="${escapeText(row.target_name)}">${escapeText(__("Mapping"))}</button>
          ${retry}
        </td>
      </tr>
    `);
  }

  openMapping(button) {
    padars.lms
      .getMapping(button.data("doctype"), button.data("name"))
      .then((mapping) => {
        if (mapping) {
          frappe.set_route("Form", "LMS Entity Mapping", mapping.name);
        } else {
          frappe.msgprint(__("No active LMS mapping exists for this record."));
        }
      })
      .catch(() => frappe.msgprint(__("The LMS mapping could not be loaded.")));
  }

  retry(button) {
    if (button.prop("disabled")) return;
    button.prop("disabled", true);
    frappe
      .call({ method: "padars.api.retry_sync_operation", args: { operation: button.data("name") } })
      .then(() => {
        frappe.show_alert({ message: __("Retry requested."), indicator: "blue" });
        this.refresh();
      })
      .catch(() => frappe.msgprint(__("The retry request could not be submitted.")))
      .finally(() => button.prop("disabled", false));
  }
}

function escapeText(value) {
  return frappe.utils.escape_html(String(value || ""));
}

function safeError(value) {
  return padars.lms.safeError(value);
}
