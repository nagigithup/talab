app_name = "talab"
app_title = "Talab"
app_publisher = "Talab"
app_description = "Talab Mining Operations System"
app_email = "admin@example.com"
app_license = "mit"

required_apps = ["erpnext"]

# Talab-owned global assets. Styles are deliberately scoped to Talab surfaces
# so Arabic RTL support does not alter Frappe or ERPNext interfaces.
app_include_css = "/assets/talab/css/talab.css"
web_include_css = ["/assets/talab/css/talab.css", "/assets/talab/css/mobile_portal.css"]

fixtures = [
	{
		"dt": "Role",
		"filters": [
			[
				"role_name",
				"in",
				[
					"Talab System Manager",
					"Talab Manager",
					"Cashier",
					"Mill Operator",
					"Mercury Custodian",
					"Purchasing User",
					"Accounts Reviewer",
				],
			]
		],
	},
	{
		"dt": "Custom DocPerm",
		"filters": [
			["parent", "=", "Customer"],
			["role", "in", ["Talab System Manager", "Talab Manager", "Mill Operator"]],
		],
	},
]

permission_query_conditions = {
	"Talab Mill Shift": "talab.permissions.get_mill_shift_permission_query_conditions",
	"Talab Operation Request": "talab.permissions.get_operation_request_permission_query_conditions",
}

has_permission = {
	"Talab Mill Shift": "talab.permissions.has_mill_shift_permission",
	"Talab Operation Request": "talab.permissions.has_operation_request_permission",
}

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "talab",
# 		"logo": "/assets/talab/logo.png",
# 		"title": "Talab",
# 		"route": "/talab",
# 		"has_permission": "talab.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/talab/css/talab.css"
# app_include_js = "/assets/talab/js/talab.js"

# include js, css files in header of web template
# web_include_css = "/assets/talab/css/talab.css"
# web_include_js = "/assets/talab/js/talab.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "talab/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "talab/public/icons.svg"

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
# 	"methods": "talab.utils.jinja_methods",
# 	"filters": "talab.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "talab.install.before_install"
# after_install = "talab.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "talab.uninstall.before_uninstall"
# after_uninstall = "talab.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "talab.utils.before_app_install"
# after_app_install = "talab.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "talab.utils.before_app_uninstall"
# after_app_uninstall = "talab.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "talab.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "talab.notifications.get_notification_config"

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
# 		"talab.tasks.all"
# 	],
# 	"daily": [
# 		"talab.tasks.daily"
# 	],
# 	"hourly": [
# 		"talab.tasks.hourly"
# 	],
# 	"weekly": [
# 		"talab.tasks.weekly"
# 	],
# 	"monthly": [
# 		"talab.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "talab.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "talab.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "talab.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "talab.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["talab.utils.before_request"]
# after_request = ["talab.utils.after_request"]

# Job Events
# ----------
# before_job = ["talab.utils.before_job"]
# after_job = ["talab.utils.after_job"]

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
# 	"talab.auth.validate"
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
