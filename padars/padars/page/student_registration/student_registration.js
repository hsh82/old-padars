frappe.pages["student-registration"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({parent: wrapper, title: __("Student Registration"), single_column: true});
  $(page.body).html(`<p>${__("Register a student or use Data Import for CSV and Excel. Use an Iranian mobile number.")}</p><div class="registration-actions"></div>`);
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
  button("Import CSV or Excel", () => {
    frappe.set_route("Form", "Data Import", "new-data-import", {reference_doctype: "Student", import_type: "Insert New Records"});
  });
  button("Review Applications", () => frappe.set_route("List", "Student Registration Application"));
};
