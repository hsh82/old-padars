frappe.ui.form.on("Moodle Learning Snapshot", {
	refresh(frm) {
		const wrapper = $(frm.fields_dict.activity_preview.wrapper).empty();
		let activities;
		try { activities = JSON.parse(frm.doc.activities || "[]"); }
		catch { wrapper.append($("<p>").text(__("Activity data could not be read."))); return; }
		wrapper.append($("<p>").text(__("Select activity titles and dates to share for engagement. Completion is not official attendance. Moodle still controls access to the activity.")));
		if (!activities.length) { wrapper.append($("<p>").text(__("No activities returned."))); return; }
		const inputs = [];
		activities.forEach((activity) => {
			const label = $("<label>").addClass("d-block");
			const input = $("<input>").attr("type", "checkbox").attr("data-cmid", activity.cmid);
			inputs.push({input, cmid: activity.cmid});
			label.append(input).append(document.createTextNode(` ${activity.name} · ${activity.module} · ID ${activity.cmid}`));
			wrapper.append(label);
			if (!activity.visible || activity.restricted) wrapper.append($("<p>").text(__("Hidden or restricted in Moodle. Publishing shares its title and dates; Moodle still controls access.")));
			wrapper.append($("<p>").text(__("Completion: {0}; attendance evidence is not enabled here.", [[__("None"), __("Manual"), __("Automatic")][activity.tracking]])));
			(activity.dates || []).forEach((date) => wrapper.append($("<div>").text(`${date.label} ${new Intl.DateTimeFormat(undefined, {timeZone: frappe.boot.time_zone?.system || "UTC", dateStyle: "medium", timeStyle: "short"}).format(new Date(date.timestamp * 1000))} (${frappe.boot.time_zone?.system || "UTC"})`)));
		});
		const button = $("<button>").attr("type", "button").addClass("btn btn-primary").text(__("Publish Selected Activities"));
		button.on("click", () => frappe.prompt([
			{fieldname: "reason", fieldtype: "Small Text", label: __("Publication Reason"), reqd: 1},
		], (values) => frappe.call({method: "padars.integrations.moodle.learning.publish_activity_selection",
			args: {source_snapshot: frm.doc.name, selected_modules: inputs.filter((item) => item.input.prop("checked")).map((item) => item.cmid), reason: values.reason}, freeze: true,
		}).then((response) => frappe.msgprint(__("Activity selection version {0} published. An empty selection removes all activities from the family portal.", [response.message.version]))), __("Share Activities with Students and Verified Guardians"), __("Publish")));
		button.prop("disabled", true);
		wrapper.append(button);
		frappe.call({method: "padars.integrations.moodle.learning.get_activity_publication_context", args: {source_snapshot: frm.doc.name}})
			.then((response) => {
				const selected = new Set(response.message.selected);
				inputs.forEach((item) => item.input.prop("checked", selected.has(item.cmid)));
				if (!response.message.can_publish) { button.remove(); inputs.forEach((item) => item.input.prop("disabled", true)); }
				else button.prop("disabled", false);
			}).catch(() => wrapper.append($("<p>").attr("role", "alert").text(__("Current publication could not be loaded. Reload before publishing."))));
	},
});
