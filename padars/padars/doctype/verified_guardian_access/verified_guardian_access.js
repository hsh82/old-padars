frappe.ui.form.on("Verified Guardian Access", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.status !== "Active") return;
		if (!["Padars School Manager", "Padars Platform Administrator", "System Manager"].some((role) => frappe.user.has_role(role))) return;
		frm.add_custom_button(__("Revoke Access"), () => frappe.prompt([
			{fieldname: "reason", fieldtype: "Small Text", label: __("Revocation Reason"), reqd: 1},
		], (values) => frappe.call({method: "padars.guardian_access.revoke_guardian_access",
			args: {access: frm.doc.name, reason: values.reason}}).then(() => frm.reload_doc()), __("Revoke Guardian Access"), __("Revoke")));
	},
});
