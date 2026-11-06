frappe.query_reports["Teacher Workload"] = {
  filters: [
    {
      fieldname: "academic_year",
      label: __("Academic Year"),
      fieldtype: "Link",
      options: "Academic Year",
      reqd: 1,
    },
    {
      fieldname: "instructor",
      label: __("Instructor"),
      fieldtype: "Link",
      options: "Instructor",
    },
  ],
};
