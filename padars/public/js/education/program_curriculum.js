frappe.ui.form.on("Program", {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.padars_grade_level || !frm.doc.padars_stream || !frm.doc.courses?.length) return;
		if (!frappe.user.has_role("Padars School Manager") && !frappe.user.has_role("Padars Platform Administrator")
				&& !frappe.user.has_role("System Manager")) return;
		frm.add_custom_button(__("Create Curriculum Adoption"), () => {
			frappe.prompt([
				{
					fieldtype: "Link",
					fieldname: "academic_year",
					label: __("Academic Year"),
					options: "Academic Year",
					reqd: 1,
				},
			], (values) => {
				frappe.call({
					method: "padars.curriculum.create_curriculum_adoption_from_program",
					args: { program: frm.doc.name, academic_year: values.academic_year },
				}).then(({ message }) => {
					frappe.set_route("Form", "School Curriculum Adoption", message.name);
				});
			}, __("Create Curriculum Adoption"), __("Create"));
		}, __("Curriculum"));
	},
});
