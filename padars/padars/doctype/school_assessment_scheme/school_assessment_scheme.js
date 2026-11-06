frappe.ui.form.on("School Assessment Scheme", {
  setup(frm) {
    frm.set_query("grading_scale", () => ({filters: {docstatus: 1}}));
    frm.set_query("assessment_plan", "components", () => ({filters: {
      padars_course_offering: frm.doc.course_offering, docstatus: 1,
      ...(frm.doc.academic_term ? {academic_term: frm.doc.academic_term} : {}),
    }}));
  },
  refresh(frm) {
    if (frm.doc.docstatus !== 1) return;
    frm.set_intro(__("This approved version is retained. Create a new version to change its rules."));
    frm.add_custom_button(__("New Version"), () => frappe.new_doc("School Assessment Scheme", {
      course_offering: frm.doc.course_offering, academic_term: frm.doc.academic_term,
      scheme_title: frm.doc.scheme_title, grading_scale: frm.doc.grading_scale,
      output_maximum: frm.doc.output_maximum, decimal_places: frm.doc.decimal_places,
    }));
    frm.add_custom_button(__("Calculate Student Result"), () => frappe.prompt([
      {fieldname: "student", fieldtype: "Link", options: "Student", label: __("Student"), reqd: 1},
    ], ({student}) => frappe.call({method: "padars.grading.calculate_scheme", args: {scheme: frm.doc.name, student}})
      .then(({message}) => {
        const dialog = new frappe.ui.Dialog({title: __("Calculated Result Preview"), fields: [{fieldname: "preview", fieldtype: "HTML"}]});
        const content = $(dialog.fields_dict.preview.wrapper).empty();
        content.append($("<p>").text(__("Score: {0} / {1}; Grade: {2}", [message.score, message.maximum, message.grade])));
        content.append($("<p>").text(__("This is a preview from approved Education results. It has not been published.")));
        const list = $("<ul>");
        message.sources.forEach((source) => list.append($("<li>").text(`${source.result}: ${source.criterion}, ${source.score}/${source.maximum}, ${source.weight}%`)));
        content.append(list);
        dialog.show();
      }), __("Calculate Student Result"), __("Calculate")));
  },
});
