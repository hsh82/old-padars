frappe.ui.form.on("Moodle Grade Mapping", {
	onload(frm) {
		frm.set_query("assessment_criteria", () => ({query: "padars.integrations.moodle.grade_import.search_plan_criteria", filters: {assessment_plan: frm.doc.assessment_plan}}));
		frm.set_query("assessment_plan", () => ({filters: {padars_course_offering: frm.doc.course_offering, docstatus: 1}}));
		frm.set_query("source_snapshot", () => ({filters: {course_offering: frm.doc.course_offering}}));
	},
	refresh(frm) {
		frm.set_intro(__("Use the numeric item ID shown on the source snapshot. Submit this mapping after reviewing source/target ranges and rounding. Weights belong to the School Assessment Scheme."));
		if (frm.doc.docstatus === 1 && ["Padars School Manager", "Padars Platform Administrator", "System Manager"].some((role) => frappe.user.has_role(role))) {
			frm.add_custom_button(__("Retire Mapping"), () => frappe.prompt([
				{fieldname: "reason", fieldtype: "Small Text", label: __("Retirement Reason"), reqd: 1},
			], (values) => frm.set_value("retirement_reason", values.reason).then(() => frm.save("Update"))
				.then(() => frappe.call({method: "frappe.client.cancel", args: {doctype: frm.doc.doctype, name: frm.doc.name}}))
				.then(() => frm.reload_doc()), __("Retire Mapping"), __("Retire")));
		}
	},
});
