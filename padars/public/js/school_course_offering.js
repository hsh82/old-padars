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
    padars.school_context.setSchoolInstructorQuery(frm, "instructor", "school");
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
    refreshSyncState(frm);
    const mappingRequestId = (frm.__padars_mapping_request_id || 0) + 1;
    frm.__padars_mapping_request_id = mappingRequestId;
    frm.remove_custom_button(__("Request Moodle Course Creation"), __("Moodle"));
    frm.remove_custom_button(__("View Synchronization Status"), __("Moodle"));
    frm.remove_custom_button(__("Retry Failed Synchronization"), __("Moodle"));
    frm.remove_custom_button(__("View Moodle Mapping"), __("Moodle"));

    frm.add_custom_button(
      __("Request Moodle Course Creation"),
      () => requestProvisioning(frm),
      __("Moodle"),
    );
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
