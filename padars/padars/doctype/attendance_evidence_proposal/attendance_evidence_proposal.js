frappe.ui.form.on("Attendance Evidence Proposal", {
	refresh(frm) {
		frm.set_intro(__("This is an evidence proposal. Official attendance changes only after authorized confirmation. Pending or unavailable evidence is not absence."));
		if (frm.is_new() || frm.doc.evaluation_state !== "Proposed Present") return;
		frm.add_custom_button(__("Confirm Present"), () => frappe.prompt([
			{fieldname: "reason", fieldtype: "Small Text", label: __("Evidence Review Reason"), reqd: 1},
		], (values) => frappe.call({method: "padars.attendance_evidence.confirm_attendance_evidence",
			args: {proposal: frm.doc.name, reason: values.reason}, freeze: true,
		}).then(({message}) => frappe.set_route("Form", "Student Attendance", message.attendance)), __("Confirm Evidence Attendance"), __("Confirm")));
	},
});
