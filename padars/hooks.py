app_name = "padars"
app_title = "Padars"
app_publisher = "HSH82"
app_description = "A Tms-lms manger for Managing Online schools. Using Moodle lms[mutms],based on education"
app_email = "sh.hamed1254@gmail.com"
app_license = "mit"

required_apps = ["education"]

app_include_js = [
	"/assets/padars/js/common/school_context.js",
	"/assets/padars/js/common/lms_sync.js",
]
app_include_css = "/assets/padars/css/padars.css"

doctype_js = {
	"School": "public/js/school.js",
	"Student": "public/js/education/student.js",
	"Program Enrollment": "public/js/education/program_enrollment.js",
	"Student Group": "public/js/education/student_group.js",
	"Course Schedule": "public/js/education/course_schedule.js",
	"Assessment Plan": "public/js/education/assessment_plan.js",
	"Assessment Result": "public/js/education/assessment_result.js",
	"Student Attendance": "public/js/education/student_attendance.js",
	"Assessment Result Tool": "public/js/education/assessment_result_tool.js",
	"School Course Offering": "public/js/school_course_offering.js",
}

# Education's generic RPC surface predates Padars' shared-site tenancy model.
# These narrow replacements validate an explicit school/group context or fail
# closed; upstream source is never modified.
override_whitelisted_methods = {
	"education.education.api.enroll_student": "padars.education_api.enroll_student",
	"education.education.api.check_attendance_records_exist": "padars.education_api.check_attendance_records_exist",
	"education.education.api.mark_attendance": "padars.education_api.mark_attendance",
	"education.education.doctype.student_group.student_group.get_students": "padars.education_api.get_students",
	"education.education.doctype.student_group.student_group.fetch_students": "padars.education_api.fetch_school_group_students",
	"education.education.doctype.student_attendance_tool.student_attendance_tool.get_student_attendance_records": "padars.education_api.get_student_attendance_records",
	"education.education.doctype.student_report_generation_tool.student_report_generation_tool.preview_report_card": "padars.education_api.preview_report_card",
}

fixtures = [
	{"dt": "Custom Field", "filters": [["module", "=", "Padars"]]},
]

after_install = "padars.install.after_install"

permission_query_conditions = {
	"School": "padars.permissions.school_permission_query_conditions",
	"School Membership": "padars.permissions.school_permission_query_conditions",
	"School Course Offering": "padars.permissions.school_permission_query_conditions",
	"LMS Entity Mapping": "padars.permissions.school_permission_query_conditions",
	"LMS Enrollment State": "padars.permissions.school_permission_query_conditions",
	"LMS Sync Operation": "padars.permissions.school_permission_query_conditions",
	"Program Enrollment": "padars.permissions.school_permission_query_conditions",
	"Student Group": "padars.permissions.school_permission_query_conditions",
	"Course Enrollment": "padars.permissions.school_permission_query_conditions",
	"Course Schedule": "padars.permissions.school_permission_query_conditions",
	"Assessment Plan": "padars.permissions.school_permission_query_conditions",
	"Assessment Result": "padars.permissions.school_permission_query_conditions",
	"Student Attendance": "padars.permissions.school_permission_query_conditions",
	"Student": "padars.permissions.school_permission_query_conditions",
	"Instructor": "padars.permissions.school_permission_query_conditions",
}

has_permission = {
	"School": "padars.permissions.has_school_permission",
	"School Membership": "padars.permissions.has_school_permission",
	"School Course Offering": "padars.permissions.has_school_permission",
	"LMS Entity Mapping": "padars.permissions.has_school_permission",
	"LMS Enrollment State": "padars.permissions.has_school_permission",
	"LMS Sync Operation": "padars.permissions.has_school_permission",
	"Program Enrollment": "padars.permissions.has_school_permission",
	"Student Group": "padars.permissions.has_school_permission",
	"Course Enrollment": "padars.permissions.has_school_permission",
	"Course Schedule": "padars.permissions.has_school_permission",
	"Assessment Plan": "padars.permissions.has_school_permission",
	"Assessment Result": "padars.permissions.has_school_permission",
	"Student Attendance": "padars.permissions.has_school_permission",
	"Student": "padars.permissions.has_school_permission",
	"Instructor": "padars.permissions.has_school_permission",
}

doc_events = {
	"Student": {"validate": "padars.education_hooks.validate_student_identity"},
	"Program Enrollment": {"validate": "padars.education_hooks.validate_program_enrollment"},
	"Student Group": {"validate": "padars.education_hooks.validate_student_group"},
	"Course Schedule": {"validate": "padars.education_hooks.validate_linked_education_context"},
	"Assessment Plan": {"validate": "padars.education_hooks.validate_linked_education_context"},
	"Assessment Result": {"validate": "padars.education_hooks.validate_linked_education_context"},
	"Student Attendance": {"validate": "padars.education_hooks.validate_linked_education_context"},
}

scheduler_events = {
	"hourly": ["padars.integrations.moodle.service.recover_stale_sync_operations"],
}

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "padars",
# 		"logo": "/assets/padars/logo.png",
# 		"title": "Padars",
# 		"route": "/padars",
# 		"has_permission": "padars.api.permission.has_app_permission",
# 	}
# ]

# The dock, the rail down the left of the desk, is a document rather than a hook. Author it in
# Manage Dock on a developer-mode site and press Export to App, and it is written to
# `padars/dock/padars/padars.json` for git to carry. An app that ships none has no
# rail: its sidebar gets a switcher in the header instead.
#
# A companion app, one that extends a host app rather than standing on its own, says so with
# `mount_on` on that same record, and its entries are appended to the host's rail. Mounting keeps
# the companion off the apps screen, so it takes precedence over any add_to_apps_screen above.

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/padars/css/padars.css"
# app_include_js = "/assets/padars/js/padars.js"

# include js, css files in header of web template
# web_include_css = "/assets/padars/css/padars.css"
# web_include_js = "/assets/padars/js/padars.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "padars/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_kanban_js = {"doctype" : "public/js/doctype_kanban.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "padars/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "padars.utils.jinja_methods",
# 	"filters": "padars.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "padars.install.before_install"
# after_install = "padars.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "padars.uninstall.before_uninstall"
# after_uninstall = "padars.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "padars.utils.before_app_install"
# after_app_install = "padars.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "padars.utils.before_app_uninstall"
# after_app_uninstall = "padars.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "padars.build.after_build"

# To hook into the build process of other apps
# The list of apps being built is passed as an argument

# after_app_build = "padars.build.after_app_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "padars.notifications.get_notification_config"

# Awesome Bar
# -----------
# Extra search results: list of dicts with label, description, route, index.
# route: ["List", "ToDo"], "/desk/docs/some/page", or "https://example.com"
# awesomebar_search = ["padars.search.awesomebar_results"]

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"padars.tasks.all"
# 	],
# 	"daily": [
# 		"padars.tasks.daily"
# 	],
# 	"hourly": [
# 		"padars.tasks.hourly"
# 	],
# 	"weekly": [
# 		"padars.tasks.weekly"
# 	],
# 	"monthly": [
# 		"padars.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "padars.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "padars.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "padars.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "padars.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["padars.utils.before_request"]
# after_request = ["padars.utils.after_request"]

# Job Events
# ----------
# before_job = ["padars.utils.before_job"]
# after_job = ["padars.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"padars.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

