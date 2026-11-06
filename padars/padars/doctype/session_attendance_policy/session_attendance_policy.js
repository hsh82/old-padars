frappe.ui.form.on("Session Attendance Policy", {
	refresh(frm) {
		frm.toggle_display("selected_activities", false);
		loadPolicyActivities(frm);
		frm.set_intro(__("Automatic completion can propose attendance only for an Asynchronous session. A teacher must confirm it. Missing evidence never marks absence; an activity cannot count for unrelated sessions."));
	},
	course_schedule(frm) { loadPolicyActivities(frm); },
	source_snapshot(frm) { loadPolicyActivities(frm); },
});

function loadPolicyActivities(frm) {
	if (!frm.doc.course_schedule) return;
	const request = (frm.__evidence_request || 0) + 1;
	frm.__evidence_request = request;
	const wrapper = $(frm.fields_dict.activity_picker.wrapper).empty().text(__("Loading activities..."));
	frappe.call({method: "padars.attendance_evidence.get_session_evidence_context",
		args: {course_schedule: frm.doc.course_schedule, source_snapshot: frm.doc.source_snapshot || undefined},
	}).then(({message: context}) => {
		if (request !== frm.__evidence_request) return;
		wrapper.empty();
		if (!context.can_manage) { wrapper.text(__("Attendance authority is required.")); return; }
		if (frm.is_new()) {
			const defaults = {};
			["school", "course_offering", "source_snapshot", "window_start", "window_end"].forEach((key) => {
				if (!frm.doc[key]) defaults[key] = context[key];
			});
			if (Object.keys(defaults).length) frm.set_value(defaults);
		}
		let selected;
		try { selected = new Set(JSON.parse(frm.doc.selected_activities || "[]")); }
		catch { selected = new Set(); }
		if (!context.activities.length) wrapper.append($("<p>").text(__("Fetch Moodle learning data first. No eligible automatic-completion activities are available.")));
		context.activities.forEach((activity) => {
			const input = $("<input>").attr("type", "checkbox").prop("checked", selected.has(activity.cmid)).prop("disabled", frm.doc.docstatus !== 0);
			input.on("change", () => {
				if (input.prop("checked")) selected.add(activity.cmid); else selected.delete(activity.cmid);
				frm.set_value("selected_activities", JSON.stringify([...selected].sort((a, b) => a - b)));
			});
			wrapper.append($("<label>").addClass("d-block").append(input).append(document.createTextNode(` ${activity.name} · ${activity.module}`)));
		});
	}).catch(() => wrapper.text(__("Activities could not be loaded. Check access and retry.")));
}
