frappe.ui.form.on("Course Schedule", {
  onload(frm) {
    configureOfferingQuery(frm);
  },

  student_group(frm) {
    configureOfferingQuery(frm);
  },

  course(frm) {
    configureOfferingQuery(frm);
  },
});

function configureOfferingQuery(frm) {
  if (!padars.school_context.hasField(frm, "padars_course_offering")) return;
  frm.set_query("padars_course_offering", () => ({
    filters: {
      student_group: frm.doc.student_group || "",
      course: frm.doc.course || "",
    },
  }));
}

frappe.ui.form.on("Course Schedule", {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.padars_course_offering || frm.doc.padars_session_mode !== "Asynchronous") return;
		if (!["Padars School Manager", "Padars Platform Administrator", "System Manager", "Padars Teacher", "Padars Academic Staff"].some((role) => frappe.user.has_role(role))) return;
		frm.add_custom_button(__("Configure Activity Evidence"), () => frappe.call({
			method: "padars.attendance_evidence.get_session_evidence_context", args: {course_schedule: frm.doc.name},
		}).then(({message: context}) => {
			if (!context.can_manage) { frappe.msgprint(__("Attendance authority is required.")); return; }
			frappe.new_doc("Session Attendance Policy", {course_schedule: frm.doc.name, school: context.school,
				course_offering: context.course_offering, source_snapshot: context.latest_source,
				window_start: context.window_start, window_end: context.window_end});
		}), __("Attendance Evidence"));
		frm.add_custom_button(__("Evaluate Activity Evidence"), () => frappe.call({
			method: "padars.attendance_evidence.get_session_evidence_context", args: {course_schedule: frm.doc.name},
		}).then(({message: context}) => {
			if (!context.can_manage || !context.policy || !context.latest_source) {
				frappe.msgprint(__("Attendance authority, an approved policy and learning sources are required.")); return;
			}
			frappe.prompt([{fieldname: "student", fieldtype: "Link", options: "Student", label: __("Student"), reqd: 1,
				get_query: () => ({filters: {name: ["in", context.students.map((row) => row.student)]}})}],
				(values) => frappe.call({method: "padars.attendance_evidence.evaluate_attendance_evidence",
					args: {policy: context.policy, student: values.student, source_snapshot: context.latest_source}, freeze: true,
				}).then(({message}) => frappe.set_route("Form", "Attendance Evidence Proposal", message.name)), __("Evaluate Evidence"), __("Evaluate"));
		}), __("Attendance Evidence"));
	},
});
