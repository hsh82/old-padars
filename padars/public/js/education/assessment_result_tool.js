// Replace Education's HTML template with DOM text/attribute setters: names,
// comments and criteria are school data and must not be interpreted as HTML.
frappe.ui.form.on("Assessment Result Tool", {
  refresh(frm) {
    frm.set_intro(__("Marks are saved as drafts. Open a saved result for manager approval."));
    frm.page.clear_primary_action();
  },

  submit_result(frm) {
    frm.page.clear_primary_action();
  },

  get_marks(frm, criteria) {
    const wrapper = $(frm.fields_dict.result_html.wrapper).empty();
    if (!criteria.length || !(frm.doc.students || []).length) {
      wrapper.append($("<p>").text(__("No assessment criteria or active students found.")));
      return;
    }
    const table = $("<table>").addClass("table table-bordered");
    const header = $("<tr>");
    [__("Student"), __("Student Name")].forEach((label) => header.append($("<th>").text(label)));
    criteria.forEach((criterion) => header.append($("<th>").text(`${criterion.assessment_criteria} (${criterion.maximum_score})`)));
    [__("Comment"), __("Total"), __("Status")].forEach((label) => header.append($("<th>").text(label)));
    table.append($("<thead>").append(header));
    const body = $("<tbody>");
    (frm.doc.students || []).forEach((student) => {
      const row = $("<tr>");
      row.append($("<td>").text(student.student), $("<td>").text(student.student_name));
      const inputs = [];
      const submitted = student.docstatus === 1;
      criteria.forEach((criterion) => {
        const input = $("<input>").attr({type: "number", min: "0", max: criterion.maximum_score, step: "any",
          "aria-label": `${student.student_name}: ${criterion.assessment_criteria}`}).prop("disabled", submitted);
        if (student.assessment_details && student.assessment_details[criterion.assessment_criteria]) {
          input.val(student.assessment_details[criterion.assessment_criteria][0]);
        }
        inputs.push({input, criterion});
        row.append($("<td>").append(input));
      });
      const comment = $("<input>").attr({type: "text", "aria-label": __("Comment for {0}", [student.student_name])})
        .val(student.assessment_details?.comment || "").prop("disabled", submitted);
      const total = $("<td>").text(student.assessment_details?.total_score?.[0] ?? "");
      const status = $("<span>").attr("aria-live", "polite").text(submitted ? __("Submitted") : __("Draft"));
      const link = $("<a>").text(__("Open result")).hide();
      const showResult = (name) => {
        if (name) link.attr("href", `/app/assessment-result/${encodeURIComponent(name)}`).show();
      };
      if (student.assessment_details) showResult(student.name);
      const statusCell = $("<td>").append(status, document.createTextNode(" "), link);
      row.append($("<td>").append(comment), total, statusCell);
      const save = () => {
        if (submitted || inputs.some(({input}) => input.val() === "" || !input[0].checkValidity())) return;
        const details = Object.create(null);
        inputs.forEach(({input, criterion}) => { details[criterion.assessment_criteria] = Number(input.val()); });
        const controls = row.find("input").prop("disabled", true);
        status.text(__("Saving"));
        frappe.call({
          method: "education.education.api.mark_assessment_result",
          args: {assessment_plan: frm.doc.assessment_plan,
            scores: {student: student.student, assessment_details: details, comment: comment.val()}},
          callback(response) {
            if (response.message) {
              total.text(response.message.total_score);
              status.text(__("Draft saved"));
              showResult(response.message.name);
            }
          },
          error() { status.text(__("Save failed; change a value to retry.")); },
          always() { controls.prop("disabled", false); },
        });
      };
      inputs.forEach(({input}) => input.on("change", save));
      comment.on("change", save);
      body.append(row);
    });
    wrapper.append(table.append(body));
  },
});
