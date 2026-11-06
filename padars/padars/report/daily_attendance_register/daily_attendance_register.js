frappe.query_reports["Padars Daily Attendance Register"] = [
  {
    fieldname: "from_date",
    label: __("From Date"),
    fieldtype: "Date",
    reqd: 1,
    default: frappe.datetime.get_today(),
  },
  {
    fieldname: "to_date",
    label: __("To Date"),
    fieldtype: "Date",
    reqd: 1,
    default: frappe.datetime.get_today(),
  },
  {
    fieldname: "student_group",
    label: __("Student Group"),
    fieldtype: "Link",
    options: "Student Group",
  },
]
