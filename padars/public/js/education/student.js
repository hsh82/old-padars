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
		if (!frm.is_new() && (frappe.user.has_role("Padars School Manager")
			|| frappe.user.has_role("Padars Platform Administrator") || frappe.user.has_role("System Manager"))) {
			frm.add_custom_button(__("Review Approved Results"), () => reviewApprovedResults(frm), __("Assessments"));
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

function reviewApprovedResults(frm) {
	frappe.prompt([
		{fieldname: "program", fieldtype: "Link", options: "Program", label: __("Program"), reqd: 1},
		{fieldname: "academic_year", fieldtype: "Link", options: "Academic Year", label: __("Academic Year"), reqd: 1},
		{fieldname: "academic_term", fieldtype: "Link", options: "Academic Term", label: __("Academic Term (optional)")},
	], (values) => {
		frappe.call({method: "padars.assessment.preview_approved_results", args: {student: frm.doc.name, ...values},
			freeze: true, freeze_message: __("Loading approved results...")}).then((response) => {
			const dialog = new frappe.ui.Dialog({title: __("Approved Results"), fields: [{fieldname: "results", fieldtype: "HTML"}]});
			const container = $(dialog.fields_dict.results.wrapper).empty();
			const rows = response.message?.results || [];
			if (!rows.length) {
				container.append($("<p>").text(__("No approved results found for this selection.")));
			} else {
				const table = $("<table>").addClass("table table-bordered");
				const header = $("<tr>");
				[__("Course"), __("Assessment"), __("Term"), __("Score"), __("Grade")].forEach((label) => header.append($("<th>").text(label)));
				table.append($("<thead>").append(header));
				const body = $("<tbody>");
				rows.forEach((item) => {
					const row = $("<tr>");
					[item.course, item.assessment_plan, item.academic_term || "—", `${item.total_score} / ${item.maximum_score}`, item.grade || "—"]
						.forEach((value) => row.append($("<td>").text(value)));
					body.append(row);
				});
				container.append(table.append(body));
			}
			dialog.show();
		});
	}, __("Review Approved Results"), __("Review"));
}

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
