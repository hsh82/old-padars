frappe.ui.form.on("Student Attendance", {
  refresh(frm) {
    if (frm.doc.student_group && frm.doc.student) {
      frm.set_intro(__("Student attendance is validated by Education against the selected group."));
    }
  },
});

frappe.ui.form.on("Student Attendance", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.docstatus !== 1 || !frm.doc.course_schedule) return;
		if (!["Padars School Manager", "Padars Platform Administrator", "System Manager", "Padars Teacher", "Padars Academic Staff"].some((role) => frappe.user.has_role(role))) return;
		frappe.call({method: "padars.attendance_evidence.get_attendance_evidence_context", args: {attendance: frm.doc.name}}).then(({message: context}) => {
			if (!context.is_evidence) return;
			frm.add_custom_button(__("Evidence Review History"), () => frappe.set_route("List", "Attendance Evidence Review", {attendance: frm.doc.name}));
			if (!context.can_override) return;
			frm.add_custom_button(__("Override Evidence Attendance"), () => frappe.prompt([
				{fieldname: "status", fieldtype: "Select", options: "Present\nAbsent", label: __("Corrected Status"), reqd: 1, default: frm.doc.status},
				{fieldname: "late_minutes", fieldtype: "Int", label: __("Late Minutes (Present only)"), default: frm.doc.padars_late_minutes || 0},
				{fieldname: "reason", fieldtype: "Small Text", label: __("Correction Reason"), reqd: 1},
			], (values) => frappe.call({method: "padars.attendance_evidence.override_evidence_attendance",
				args: {attendance: frm.doc.name, ...values}, freeze: true,
			}).then(() => frm.reload_doc()), __("Override Evidence Attendance"), __("Correct")));
		});
	},
});
