frappe.pages["student-registration"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({parent: wrapper, title: __("Student Registration"), single_column: true});
  $(page.body).html(`<p>${__("Register one student or preview a CSV batch. Phone numbers must use international format. Education must have Skip User Creation enabled.")}</p><p>${__("CSV columns: first_name, last_name, national_id, phone, email. Up to 100 rows.")}</p><div class="registration-actions"></div>`);
  const actions = $(page.body).find(".registration-actions");
  const button = (label, handler) => $("<button class='btn btn-default mr-2'>").text(__(label)).appendTo(actions).on("click", handler);
  button("Register Student", () => {
    const dialog = new frappe.ui.Dialog({title: __("Register Student"), fields: [
      {fieldname: "first_name", label: __("First Name"), fieldtype: "Data", reqd: 1},
      {fieldname: "last_name", label: __("Last Name"), fieldtype: "Data"},
      {fieldname: "national_id", label: __("National ID"), fieldtype: "Data", reqd: 1},
      {fieldname: "phone", label: __("Phone"), fieldtype: "Data", reqd: 1},
      {fieldname: "email", label: __("Email"), fieldtype: "Data", options: "Email", reqd: 1},
    ], primary_action_label: __("Register"), primary_action: (values) => frappe.call({
      method: "padars.registration.register_student", args: values, freeze: true,
    }).then(({message}) => { dialog.hide(); frappe.set_route("Form", "Student", message.student); })});
    dialog.show();
  });
  button("Returning Student", () => {
    const dialog = new frappe.ui.Dialog({title: __("Returning Student"), fields: [
      {fieldname: "student", label: __("Student"), fieldtype: "Link", options: "Student", reqd: 1},
      {fieldname: "program", label: __("Program"), fieldtype: "Link", options: "Program", reqd: 1},
      {fieldname: "academic_year", label: __("Academic Year"), fieldtype: "Link", options: "Academic Year", reqd: 1},
      {fieldname: "academic_term", label: __("Academic Term"), fieldtype: "Link", options: "Academic Term"},
    ], primary_action_label: __("Create Draft Enrollment"), primary_action: (values) => frappe.call({
      method: "padars.registration.enroll_returning_student", args: values, freeze: true,
    }).then(({message}) => { dialog.hide(); frappe.set_route("Form", "Program Enrollment", message.enrollment); })});
    dialog.show();
  });
  button("CSV Batch", () => {
    const dialog = new frappe.ui.Dialog({title: __("CSV Batch"), fields: [
      {fieldname: "file", label: __("CSV File"), fieldtype: "HTML"},
      {fieldname: "result", fieldtype: "HTML"},
    ]});
    const file = $('<input type="file" accept=".csv,text/csv">').appendTo(dialog.fields_dict.file.$wrapper);
    let rows = null;
    // Frappe's CSV parser handles quoted cells and embedded delimiters.
    file.on("change", async () => {
      rows = null;
      try {
        const text = await file[0].files[0].text();
        const parsed = frappe.utils.csv_to_array(text);
        const headers = parsed.shift().map((v) => v.trim().toLowerCase());
        rows = parsed.filter((row) => row.some((cell) => cell.trim())).map((row) => Object.fromEntries(headers.map((name, i) => [name, row[i] || ""])));
        dialog.fields_dict.result.$wrapper.text(__("Ready to preview {0} rows.", [rows.length]));
      } catch (err) { dialog.fields_dict.result.$wrapper.text(__("Unable to read the CSV file.")); }
    });
    const run = (preview) => {
      if (!rows) { frappe.msgprint(__("Choose a CSV file first.")); return; }
      frappe.call({method: "padars.registration.register_batch", args: {rows, preview: preview ? 1 : 0}, freeze: true}).then(({message}) => {
        const summary = message.map((row) => __("Row {0}: {1}", [row.row, row.status])).join("\n");
        dialog.fields_dict.result.$wrapper.empty().append($("<pre>").text(summary));
      });
    };
    dialog.set_primary_action(__("Preview"), () => run(true));
    dialog.set_secondary_action_label(__("Register Rows"));
    dialog.set_secondary_action(() => run(false));
    dialog.show();
  });
};
