frappe.ui.form.on("Student", {
  refresh(frm) {
    if (frm.doc.user) {
      frm.set_intro(__("Student account linked to {0}.", [frm.doc.user]), "green");
    } else if (frm.doc.student_email_id) {
      frm.set_intro(
        __("No linked account is visible yet. Education user provisioning follows the configured site setting."),
        "orange",
      );
    }
		if (frm.is_new() || !frm.doc.user) return;
		if (frappe.user.has_role("Padars School Manager") || frappe.user.has_role("System Manager")) {
			frm.add_custom_button(__("Reconcile National ID"), () => {
				frappe.prompt([{fieldname: "national_id", fieldtype: "Data", label: __("National ID"), reqd: 1}],
					(values) => frappe.call({method: "padars.student_identity.reconcile_existing_student",
						args: {student: frm.doc.name, national_id: values.national_id}}).then(() => {
						frappe.show_alert({message: __("Identity reconciled."), indicator: "green"});
					}), __("Reconcile Student Identity"), __("Reconcile"));
			}, __("Registration"));
		}
		frm.remove_custom_button(__("Request Moodle User Provisioning"), __("Moodle"));
		if (canManageMoodle()) {
			frm.add_custom_button(
				__("Request Moodle User Provisioning"),
				() => requestStudentUserProvisioning(frm),
				__("Moodle"),
			);
		}
  },
});

function canManageMoodle() {
	return frappe.user.has_role("Padars School Manager")
		|| frappe.user.has_role("Padars Moodle Manager")
		|| frappe.user.has_role("Padars Platform Administrator")
		|| frappe.user.has_role("System Manager");
}

function requestStudentUserProvisioning(frm) {
	frappe.prompt(
		[
			{
				fieldname: "school",
				fieldtype: "Link",
				label: __("School"),
				options: "School",
				reqd: 1,
			},
		],
		(values) => {
			frappe.call({
				method: "padars.api.request_student_user_provisioning",
				args: { student: frm.doc.name, school: values.school },
			}).then(() => {
				frappe.show_alert({ message: __("Moodle user provisioning requested."), indicator: "blue" });
			}).catch(() => {
				frappe.msgprint(__("The Moodle user provisioning request could not be submitted."));
			});
		},
		__("Request Moodle User Provisioning"),
		__("Request"),
	);
}
