"""
BookingZone Hooks
==================
Frappe app hooks for BookingZone Super ERP.
Integrates QBO + R365 features with open-source OCR and multi-processor payments.
"""

app_name = "bookingzone"
app_title = "BookingZone"
app_publisher = "BookingZone Inc."
app_description = "Restaurant & Hospitality ERP with QBO + R365 features"
app_email = "support@bookingzone.com"
app_license = "MIT"
app_version = "1.0.0"

# Required Apps
required_apps = ["frappe", "erpnext"]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = "/assets/bookingzone/css/bookingzone.css"
app_include_js = [
    "/assets/bookingzone/js/payment_form.js",
    "/assets/bookingzone/js/ocr_upload.js"
]

# include js, css files in header of web template
web_include_css = "/assets/bookingzone/css/bookingzone-web.css"
web_include_js = "/assets/bookingzone/js/payment_form.js"

# include custom scss in every website theme (without signing in)
# website_theme_scss = "bookingzone/public/scss/website"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Sales Invoice": "public/js/sales_invoice.js",
    "Purchase Invoice": "public/js/purchase_invoice.js",
    "Expense Receipt": "public/js/expense_receipt.js"
}

# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "bookingzone/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
#	"methods": "bookingzone.utils.jinja_methods",
#	"filters": "bookingzone.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "bookingzone.install.before_install"
after_install = "bookingzone.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "bookingzone.uninstall.before_uninstall"
# after_uninstall = "bookingzone.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/dependencies for other apps
# For example, to set up dependencies for Frappe Cloud
# setup_wizard_requires = "assets/bookingzone/js/setup_wizard.js"
# setup_wizard_stages = "bookingzone.setup.setup_wizard.get_setup_stages"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "bookingzone.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
#	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Sales Invoice": {
        "on_submit": "bookingzone.events.sales_invoice.on_submit",
        "on_cancel": "bookingzone.events.sales_invoice.on_cancel"
    },
    "Purchase Invoice": {
        "on_submit": "bookingzone.events.purchase_invoice.on_submit"
    },
    "Expense Receipt": {
        "after_insert": "bookingzone.events.expense_receipt.after_insert",
        "on_update": "bookingzone.events.expense_receipt.on_update"
    }
}

# Scheduled Tasks
# ---------------

scheduler_events = {
    "all": [
        "bookingzone.tasks.all"
    ],
    "daily": [
        "bookingzone.tasks.daily"
    ],
    "hourly": [
        "bookingzone.tasks.hourly"
    ],
    "weekly": [
        "bookingzone.tasks.weekly"
    ],
    "monthly": [
        "bookingzone.tasks.monthly"
    ],
    "cron": {
        # Sync payment statuses every 15 minutes
        "*/15 * * * *": [
            "bookingzone.tasks.sync_payment_statuses"
        ],
        # Process pending OCR every 5 minutes
        "*/5 * * * *": [
            "bookingzone.tasks.process_pending_ocr"
        ],
        # Daily sales import from POS at 2 AM
        "0 2 * * *": [
            "bookingzone.tasks.import_pos_sales"
        ],
        # Nightly Sage ERP sync at 3 AM
        "0 3 * * *": [
            "bookingzone.tasks.sync_sage_erp"
        ]
    }
}

# Testing
# -------

# before_tests = "bookingzone.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
#	"frappe.desk.doctype.event.event.get_events": "bookingzone.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#	"Task": "bookingzone.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["bookingzone.utils.before_request"]
# after_request = ["bookingzone.utils.after_request"]

# Job Events
# ----------
# before_job = ["bookingzone.utils.before_job"]
# after_job = ["bookingzone.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
#	{
#		"doctype": "{doctype_1}",
#		"filter_by": "{filter_by}",
#		"redact_fields": ["{field_1}", "{field_2}"],
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_2}",
#		"filter_by": "{filter_by}",
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_3}",
#		"strict": False,
#	},
#	{
#		"doctype": "{doctype_4}"
#	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
#	"bookingzone.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
#	"Logging DocType Name": 30  # days to retain logs
# }

# API Whitelist
# -------------
# Expose API methods

api_whitelist = [
    # OCR APIs
    "bookingzone.api.ocr_process_receipt",
    "bookingzone.api.ocr_process_invoice",
    "bookingzone.api.ocr_process_document",
    "bookingzone.api.ocr_status",
    
    # Payment APIs
    "bookingzone.api.payment_create",
    "bookingzone.api.payment_process",
    "bookingzone.api.payment_refund",
    "bookingzone.api.payment_status",
    "bookingzone.api.payment_gateways",
    "bookingzone.api.payment_client_config",
    "bookingzone.api.payment_webhook",
    
    # POS Payment Integration APIs
    "bookingzone.services.pos_payment_integration.process_pos_payment",
    "bookingzone.services.pos_payment_integration.reload_game_card",
    "bookingzone.services.pos_payment_integration.purchase_gift_card",
    "bookingzone.services.pos_payment_integration.open_session",
    "bookingzone.services.pos_payment_integration.close_session",
    "bookingzone.services.pos_payment_integration.get_payment_methods_for_pos",
    
    # Dashboard APIs
    "bookingzone.api.get_payment_dashboard_data",
    "bookingzone.api.get_ocr_dashboard_data",
    "bookingzone.api.get_restaurant_dashboard_data",
    
    # Restaurant APIs
    "bookingzone.api.get_prime_cost_trend",
    "bookingzone.api.generate_prime_cost_report",
    "bookingzone.api.get_recipe_cost",
    "bookingzone.api.update_all_recipe_costs",
    "bookingzone.api.get_par_level_dashboard",
    "bookingzone.api.log_waste_quick",
    
    # Bank Reconciliation APIs
    "bookingzone.api.apply_bank_rules",
    "bookingzone.api.bulk_categorize_transactions"
]

# Website Route Rules
# -------------------

website_route_rules = [
    # Payment page
    {"from_route": "/pay/<payment_id>", "to_route": "payment"},
    
    # Webhook endpoints
    {"from_route": "/api/webhook/payment", "to_route": "bookingzone.api.payment_webhook"},
]

# Fixtures
# --------
# Export fixtures for deployment

fixtures = [
    {
        "dt": "Custom Field",
        "filters": [["module", "=", "BookingZone"]]
    },
    {
        "dt": "Property Setter",
        "filters": [["module", "=", "BookingZone"]]
    },
    {
        "dt": "Payment Gateway Configuration"
    },
    {
        "dt": "Payment Routing Rule"
    }
]
