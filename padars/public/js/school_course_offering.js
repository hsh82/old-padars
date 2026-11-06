frappe.ui.form.on("School Course Offering", {
  onload(frm) {
    padars.school_context.loadAuthorizedSchools(frm, "school", "academic_year");
    padars.school_context.setActiveSchoolQuery(frm, "school");

    frm.set_query("course", () => ({
      query: "education.education.doctype.program_enrollment.program_enrollment.get_program_courses",
      filters: { program: frm.doc.program || "" },
    }));

    frm.set_query("student_group", () => ({
      filters: {
        padars_school: frm.doc.school || "",
        academic_year: frm.doc.academic_year || "",
        program: frm.doc.program || "",
        course: frm.doc.course || "",
      },
    }));
    frm.set_query("instructor", () => ({
      filters: { status: "Active", padars_user: ["is", "set"] },
    }));
  },

  school(frm) {
    padars.school_context.clearFields(frm, [
      "academic_year",
      "program",
      "course",
      "student_group",
      "instructor",
    ]);
    padars.school_context.setSchoolYearFromContext(frm, "school", "academic_year");
  },

  academic_year(frm) {
    if (!frm.doc.academic_year) return;
    if (frm.doc.student_group) frm.set_value("student_group", null);
  },

  program(frm) {
    if (frm.doc.course) frm.set_value("course", null);
    if (frm.doc.student_group) frm.set_value("student_group", null);
  },

  course(frm) {
    if (frm.doc.student_group) frm.set_value("student_group", null);
  },

  refresh(frm) {
    if (frm.is_new()) return;
    if (["Padars School Manager", "Padars Platform Administrator", "System Manager"].some((role) => frappe.user.has_role(role))) {
      frm.add_custom_button(__("Assessment Scheme"), () => frappe.new_doc("School Assessment Scheme", {
        course_offering: frm.doc.name,
      }), __("Assessments"));
    }
    if (["Padars School Manager", "Padars Platform Administrator", "System Manager", "Padars Teacher", "Padars Academic Staff", "Padars Grade Entry Staff"].some((role) => frappe.user.has_role(role))) {
      frm.add_custom_button(__("Fetch Learning Activities"), () => frappe.call({
        method: "padars.integrations.moodle.learning.request_learning_discovery", args: {course_offering: frm.doc.name}, freeze: true,
      }).then(() => frappe.msgprint(__("Learning discovery queued. Open Learning Sources after synchronization finishes."))), __("Learning"));
      frm.add_custom_button(__("Learning Sources"), () => frappe.set_route("List", "Moodle Learning Snapshot", {course_offering: frm.doc.name}), __("Learning"));
      frm.add_custom_button(__("Moodle Grade Sources"), () => frappe.set_route("List", "Moodle Grade Snapshot", {course_offering: frm.doc.name}), __("Assessments"));
    }
    if (["Padars School Manager", "Padars Platform Administrator", "System Manager"].some((role) => frappe.user.has_role(role))) {
      frm.add_custom_button(__("Fetch Moodle Grades"), () => frappe.call({
        method: "padars.integrations.moodle.grades.request_grade_discovery",
        args: {course_offering: frm.doc.name}, freeze: true,
      }).then((response) => frappe.set_route("Form", "LMS Sync Operation", response.message.operation)), __("Assessments"));
    }
    refreshSyncState(frm);
    const mappingRequestId = (frm.__padars_mapping_request_id || 0) + 1;
    frm.__padars_mapping_request_id = mappingRequestId;
    frm.remove_custom_button(__("Request Moodle Course Creation"), __("Moodle"));
    frm.remove_custom_button(__("View Synchronization Status"), __("Moodle"));
    frm.remove_custom_button(__("Retry Failed Synchronization"), __("Moodle"));
    frm.remove_custom_button(__("View Moodle Mapping"), __("Moodle"));

    const isManager = frappe.user.has_role("Padars School Manager")
      || frappe.user.has_role("Padars Platform Administrator")
      || frappe.user.has_role("Padars Moodle Manager")
      || frappe.user.has_role("System Manager");
    if (isManager) {
      frm.add_custom_button(
        __("Request Moodle Course Creation"),
        () => requestProvisioning(frm),
        __("Moodle"),
      );
    }
    if (isManager && frm.doc.status !== "Archived") {
      frm.remove_custom_button(__("Enroll Students in Moodle"), __("Moodle"));
      frm.add_custom_button(__("Enroll Students in Moodle"), () => selectStudentsForMoodle(frm), __("Moodle"));
      frm.remove_custom_button(__("Assign Teacher"), __("Staff"));
      frm.remove_custom_button(__("Unassign Teacher"), __("Staff"));
      frm.add_custom_button(__("Assign Teacher"), () => {
        frappe.prompt([
          {
            fieldtype: "Link", fieldname: "instructor", label: __("Instructor"),
            options: "Instructor", default: frm.doc.instructor || "", reqd: 1,
            get_query: () => ({ filters: { status: "Active", padars_user: ["is", "set"] } }),
          },
          { fieldtype: "Check", fieldname: "can_enter_marks", label: __("Enter Grades"), default: 1 },
          { fieldtype: "Check", fieldname: "can_manage_attendance", label: __("Manage Attendance"), default: 1 },
        ], (values) => {
          frappe.call({
            method: "padars.staff.assign_teacher_to_offering",
            args: { offering: frm.doc.name, ...values },
          }).then(() => frm.reload_doc());
        }, __("Assign Teacher"), __("Assign"));
      }, __("Staff"));
      if (frm.doc.instructor) {
        frm.add_custom_button(__("Unassign Teacher"), () => {
          frappe.call({
            method: "padars.staff.assign_teacher_to_offering",
            args: { offering: frm.doc.name, instructor: null },
          }).then(() => frm.reload_doc());
        }, __("Staff"));
      }
    }
    frm.add_custom_button(
      __("View Synchronization Status"),
      () => openSyncMonitor(frm),
      __("Moodle"),
    );
    padars.lms
      .getMapping("School Course Offering", frm.doc.name)
      .then((mapping) => {
        if (!mapping || !frm.page || frm.__padars_mapping_request_id !== mappingRequestId) return;
        frm.remove_custom_button(__("View Moodle Mapping"), __("Moodle"));
        frm.add_custom_button(
          __("View Moodle Mapping"),
          () => frappe.set_route("Form", "LMS Entity Mapping", mapping.name),
          __("Moodle"),
        );
        if (mapping.remote_url) {
          frm.remove_custom_button(__("Open Moodle Course"), __("Moodle"));
          frm.add_custom_button(
            __("Open Moodle Course"),
            () => window.open(mapping.remote_url, "_blank", "noopener"),
            __("Moodle"),
          );
        }
      })
      .catch(() => {});
  },
});

function refreshSyncState(frm) {
  const requestId = (frm.__padars_sync_request_id || 0) + 1;
  frm.__padars_sync_request_id = requestId;
  padars.lms
    .getLatestOperation("School Course Offering", frm.doc.name)
    .then((operation) => {
      if (frm.__padars_sync_request_id !== requestId || !frm.page) return;
      frm.__padars_latest_sync_operation = operation;
      if (!operation) {
        frm.page.set_indicator(__("Not requested"), "gray");
        return;
      }
      frm.page.set_indicator(padars.lms.labelForState(operation.state), padars.lms.indicatorColor(operation.state));
      if (operation.state === "Failed" && operation.last_error) {
        frm.set_intro(
          __("Moodle synchronization needs attention: {0}", [padars.lms.safeError(operation.last_error)]),
          "red",
        );
        addRetryButton(frm, operation);
      }
    })
    .catch(() => {
      if (frm.__padars_sync_request_id === requestId && frm.page) {
        frm.page.set_indicator(__("Status unavailable"), "orange");
      }
    });
}

function addRetryButton(frm, operation) {
  frm.remove_custom_button(__("Retry Failed Synchronization"), __("Moodle"));
  frm.add_custom_button(
    __("Retry Failed Synchronization"),
    () => retryProvisioning(frm, operation),
    __("Moodle"),
  );
}

function requestProvisioning(frm) {
  if (frm.__padars_sync_busy) return;
  frm.__padars_sync_busy = true;
  frappe.call({
    method: "padars.api.request_course_offering_sync",
    args: { course_offering: frm.doc.name },
  })
    .then(() => {
      frappe.show_alert({ message: __("Moodle course synchronization requested."), indicator: "blue" });
      refreshSyncState(frm);
    })
    .catch(() => frappe.msgprint(__("The Moodle synchronization request could not be submitted.")))
    .finally(() => {
      frm.__padars_sync_busy = false;
    });
}

function retryProvisioning(frm, operation) {
  if (frm.__padars_sync_busy) return;
  frm.__padars_sync_busy = true;
  frappe.call({
    method: "padars.api.retry_sync_operation",
    args: { operation: operation.name },
  })
    .then(() => {
      frappe.show_alert({ message: __("Moodle synchronization retry requested."), indicator: "blue" });
      refreshSyncState(frm);
    })
    .catch(() => frappe.msgprint(__("The Moodle synchronization retry could not be submitted.")))
    .finally(() => {
      frm.__padars_sync_busy = false;
    });
}

function openSyncMonitor(frm) {
  frappe.route_options = {
    target_doctype: "School Course Offering",
    target_name: frm.doc.name,
  };
  frappe.set_route("lms-sync-monitor");
}

function selectStudentsForMoodle(frm) {
  frappe.call({
    method: "padars.api.get_course_offering_students",
    args: { course_offering: frm.doc.name },
  }).then(({ message }) => {
    const students = message || [];
    if (!students.length) {
      frappe.msgprint(__("This offering has no activated students with a submitted Program Enrollment in its active group."));
      return;
    }
    new frappe.ui.form.MultiSelectDialog({
      doctype: "Student",
      target: frm,
      setters: {},
      get_query: () => ({ filters: { name: ["in", students] } }),
      action(selected) {
        if (!selected || !selected.length) return;
        frappe.call({
          method: "padars.api.request_student_enrollments",
          args: { course_offering: frm.doc.name, students: selected },
        }).then(() => {
          frappe.show_alert({ message: __("Moodle enrollment synchronization queued."), indicator: "blue" });
          refreshSyncState(frm);
        }).catch(() => frappe.msgprint(__("The selected students could not be queued for Moodle enrollment.")));
      },
    });
  }).catch(() => frappe.msgprint(__("Eligible students could not be loaded for this offering.")));
}
