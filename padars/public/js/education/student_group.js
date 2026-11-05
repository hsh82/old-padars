frappe.ui.form.on("Student Group", {
  onload(frm) {
    padars.school_context.loadAuthorizedSchools(frm, "padars_school", "academic_year");
    padars.school_context.setAcademicTermQuery(frm, "academic_year", "academic_term");
    padars.school_context.setSchoolGridStudentQuery(
      frm,
      "students",
      "student",
      "padars_school",
      () => ({
        academic_year: frm.doc.academic_year || "",
        program: frm.doc.program || "",
        course: frm.doc.course || "",
      }),
    );
    padars.school_context.setSchoolGridInstructorQuery(frm, "instructors", "instructor", "padars_school");
    padars.school_context.setProgramCourseQuery(frm, "course", "program");
    frm.set_query("padars_curriculum_adoption", () => ({
      filters: {
        school: frm.doc.padars_school || "",
        academic_year: frm.doc.academic_year || "",
        program: frm.doc.program || "",
        status: "Active",
      },
    }));
  },

  padars_school(frm) {
    if (frm.is_new()) {
      padars.school_context.clearFields(frm, ["academic_year", "academic_term", "program", "course"]);
      padars.school_context.setSchoolYearFromContext(frm, "padars_school", "academic_year");
    } else {
      frappe.show_alert({
        message: __("Changing School does not move existing group members. Review the roster before saving."),
        indicator: "orange",
      });
    }
    padars.school_context.setAcademicTermQuery(frm, "academic_year", "academic_term");
  },

  academic_year(frm) {
    if (frm.doc.academic_term) frm.set_value("academic_term", null);
    if (frm.doc.padars_curriculum_adoption) frm.set_value("padars_curriculum_adoption", null);
    padars.school_context.setAcademicTermQuery(frm, "academic_year", "academic_term");
  },

  program(frm) {
    if (frm.doc.course) frm.set_value("course", null);
    if (frm.doc.padars_curriculum_adoption) frm.set_value("padars_curriculum_adoption", null);
    if (frm.doc.students && frm.doc.students.length) {
      frappe.show_alert({ message: __("Review existing students after changing Program."), indicator: "orange" });
    }
  },

  padars_is_class_section(frm) {
    if (!frm.doc.padars_is_class_section) {
      frm.set_value("padars_section_code", null);
      frm.set_value("padars_curriculum_adoption", null);
    }
  },

  refresh(frm) {
    // Education's generic roster action lacks Padars school and enrollment filters.
    frm.remove_custom_button(__("Get Students"));
    if (frm.fields_dict.get_students) frm.set_df_property("get_students", "hidden", 1);
    const isManager = frappe.user.has_role("Padars School Manager")
      || frappe.user.has_role("Padars Platform Administrator")
      || frappe.user.has_role("System Manager");
    if (!frm.is_new() && frm.doc.padars_is_class_section && isManager) {
      frm.add_custom_button(__("Add Enrolled Students"), () => {
        frappe.call({
          method: "padars.curriculum.add_enrolled_students_to_section",
          args: { student_group: frm.doc.name },
        }).then(({ message }) => {
          frappe.show_alert({ message: __("Added {0} student(s).", [message.added]), indicator: "green" });
          frm.reload_doc();
        });
      }, __("Curriculum"));
      frm.add_custom_button(__("Generate Course Offerings"), () => {
        frappe.call({
          method: "padars.curriculum.generate_course_offerings",
          args: { student_group: frm.doc.name },
        }).then(({ message }) => {
          frappe.msgprint(__("Created {0} and reused {1} Course Offering(s).", [message.created, message.reused]));
        });
      }, __("Curriculum"));
    }
    if (!frm.doc.max_strength || !frm.doc.students) return;
    if (frm.doc.students.length >= frm.doc.max_strength) {
      frm.dashboard.set_headline_alert(
        __("This group is at or above its configured capacity."),
        "orange",
      );
    }
  },
});
