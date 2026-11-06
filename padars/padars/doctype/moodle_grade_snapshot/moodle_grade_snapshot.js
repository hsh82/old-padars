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
