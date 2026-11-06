frappe.ui.form.on("Student", {
  refresh(frm) {
    if (frm.is_new() || !["Padars School Manager", "Padars Platform Administrator", "System Manager"].some((role) => frappe.user.has_role(role))) return;
    frm.add_custom_button(__("Publish Report Card"), () => {
      const select = new frappe.ui.Dialog({title: __("Review Report Card Sources"), fields: [
        {fieldname: "enrollment", fieldtype: "Link", options: "Program Enrollment", label: __("Submitted Enrollment"), reqd: 1,
          get_query: () => ({filters: {student: frm.doc.name, docstatus: 1}})},
        {fieldname: "schemes", fieldtype: "Table", label: __("One Approved Scheme per Enrolled Course"), reqd: 1,
          fields: [{fieldname: "scheme", fieldtype: "Link", options: "School Assessment Scheme", label: __("Scheme"), in_list_view: 1, reqd: 1,
            get_query: () => ({filters: {docstatus: 1}})}]},
        {fieldname: "correction_reason", fieldtype: "Small Text", label: __("Correction Reason (for a replacement version)")},
      ], primary_action_label: __("Preview"), primary_action: async (values) => {
        const schemes = (values.schemes || []).map((row) => row.scheme);
        const {message} = await frappe.call({method: "padars.publication.preview_report_card", args: {enrollment: values.enrollment, schemes}});
        const review = new frappe.ui.Dialog({title: __("Approve Publication"), fields: [{fieldname: "preview", fieldtype: "HTML"}],
          primary_action_label: __("Publish Reviewed Report"), primary_action: async () => {
            review.get_primary_btn().prop("disabled", true);
            try {
              const result = await frappe.call({method: "padars.publication.publish_report_card", args: {
                enrollment: values.enrollment, schemes, expected_digest: message.digest, correction_reason: values.correction_reason,
              }});
              review.hide(); select.hide();
              frappe.set_route("Form", "Report Card Publication", result.message.name);
            } finally { review.get_primary_btn().prop("disabled", false); }
          }});
        const content = $(review.fields_dict.preview.wrapper).empty();
        content.append($("<p>").text(`${message.snapshot.student_name} · ${message.snapshot.program} · ${message.snapshot.academic_year} · ${message.snapshot.academic_term || __("Annual")}`));
        const table = $("<table>").addClass("table");
        message.snapshot.courses.forEach((course) => table.append($("<tr>").append(
          $("<td>").text(course.course_name), $("<td>").text(`${course.score}/${course.maximum}`), $("<td>").text(course.grade))));
        content.append(table);
        review.show();
      }});
      select.show();
    }, __("Assessments"));
  },
});
