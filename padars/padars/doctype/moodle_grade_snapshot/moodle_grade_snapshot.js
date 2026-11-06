frappe.ui.form.on("Moodle Grade Snapshot", {
	refresh(frm) {
		const wrapper = $(frm.fields_dict.grade_preview.wrapper).empty();
		let items;
		try { items = JSON.parse(frm.doc.items || "[]"); }
		catch { wrapper.append($("<p>").text(__("Grade data could not be read. Contact support."))); return; }
		wrapper.append($("<p>").text(__("Instructional source snapshot. These grades have not been imported or approved as official Education results.")));
		if (!items.length) { wrapper.append($("<p>").text(__("Moodle returned no grade items."))); return; }
		const table = $("<table>").addClass("table table-bordered");
		const header = $("<tr>");
		[__("Item"), __("ID"), __("Type"), __("Raw grade"), __("Range"), __("Status")].forEach((label) => header.append($("<th>").text(label)));
		table.append($("<thead>").append(header));
		const body = $("<tbody>");
		items.forEach((item) => {
			const row = $("<tr>");
			[item.name, item.id, item.module || item.itemtype, item.graderaw ?? "—",
				`${item.grademin ?? "—"}–${item.grademax ?? "—"}`, __(item.status)].forEach((value) => row.append($("<td>").text(value)));
			body.append(row);
		});
		wrapper.append($("<div>").addClass("table-responsive").append(table.append(body)));
	},
});

frappe.ui.form.on("Moodle Grade Snapshot", {
	refresh(frm) {
		if (frm.is_new()) return;
		if (["Padars School Manager", "Padars Platform Administrator", "System Manager"].some((role) => frappe.user.has_role(role))) {
			frm.add_custom_button(__("Create Grade Mapping"), () => frappe.new_doc("Moodle Grade Mapping", {
				school: frm.doc.school, course_offering: frm.doc.course_offering, source_snapshot: frm.doc.name,
			}), __("Education"));
		}
		frm.add_custom_button(__("Review Education Import"), () => frappe.prompt([
			{fieldname: "assessment_plan", fieldtype: "Link", options: "Assessment Plan", label: __("Assessment Plan"), reqd: 1,
				get_query: () => ({filters: {padars_course_offering: frm.doc.course_offering, docstatus: 1}})},
		], (values) => reviewMoodleGradeImport(frm, values.assessment_plan), __("Review Education Import"), __("Review")), __("Education"));
	},
});

function reviewMoodleGradeImport(frm, plan) {
	frappe.call({method: "padars.integrations.moodle.grade_import.preview_grade_import",
		args: {source_snapshot: frm.doc.name, assessment_plan: plan}, freeze: true}).then((response) => {
		const preview = response.message;
		const dialog = new frappe.ui.Dialog({title: __("Review Instructional Grades"), fields: [
			{fieldname: "preview", fieldtype: "HTML"},
			{fieldname: "reason", fieldtype: "Small Text", label: __("Review Reason"), reqd: 1},
		], primary_action_label: __("Import as Draft"), primary_action(values) {
			if (!preview.ready) return;
			frappe.call({method: "padars.integrations.moodle.grade_import.apply_grade_import",
				args: {source_snapshot: frm.doc.name, assessment_plan: plan, expected_digest: preview.digest, reason: values.reason}, freeze: true,
			}).then((result) => { dialog.hide(); frappe.set_route("Form", "Assessment Result", result.message.result); });
		}});
		const wrapper = $(dialog.fields_dict.preview.wrapper).empty();
		(preview.issues || []).forEach((issue) => wrapper.append($("<p>").attr("role", "alert").text(issue)));
		wrapper.append($("<p>").text(__("This updates a draft only. Official approval and report publication are separate actions.")));
		Object.entries(preview.scores || {}).forEach(([criterion, score]) => {
			wrapper.append($("<p>").text(__("{0}: previous {1}; proposed {2}", [criterion, preview.previous[criterion] ?? "—", score])));
		});
		dialog.show();
		if (!preview.ready) dialog.get_primary_btn().prop("disabled", true);
	});
}
