app_name = "scooterbug"
app_title = "ScooterBug"
app_publisher = "BookingZone"
app_description = "Equipment Rental Management System for Theme Parks"
app_email = "ryanw@bookingzone.com"
app_license = "MIT"
app_version = "1.0.0"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/scooterbug/css/scooterbug.css"
# app_include_js = "/assets/scooterbug/js/scooterbug.js"

# include js, css files in header of web template
# web_include_css = "/assets/scooterbug/css/scooterbug.css"
# web_include_js = "/assets/scooterbug/js/scooterbug.js"

# Installation
# ------------

# before_install = "scooterbug_erpnext.install.before_install"
after_install = "scooterbug.install.after_install"

# Fixtures
# --------
fixtures = [
    {"dt": "Custom Field", "filters": [["module", "=", "ScooterBug"]]},
    {"dt": "Property Setter", "filters": [["module", "=", "ScooterBug"]]},
]

# Document Events
# ---------------

doc_events = {
    "Equipment Booking": {
        "on_submit": "scooterbug.api.booking.on_booking_submit",
        "on_cancel": "scooterbug.api.booking.on_booking_cancel",
    },
    "Check In Out Log": {
        "after_insert": "scooterbug.api.checkinout.update_equipment_status",
    },
}

# Scheduled Tasks
# ---------------

scheduler_events = {
    "daily": [
        "scooterbug.tasks.send_booking_reminders",
        "scooterbug.tasks.check_overdue_returns",
    ],
    "hourly": [
        "scooterbug.tasks.update_equipment_availability",
    ],
}

# Permissions
# -----------

has_permission = {
    "Equipment": "scooterbug.permissions.equipment_permission",
    "Equipment Booking": "scooterbug.permissions.booking_permission",
}

# DocType Class
# -------------

# Override standard doctype classes
# override_doctype_class = {
#     "ToDo": "custom_app.overrides.CustomToDo"
# }

# Jinja
# -----

# add methods and filters to jinja environment
# jinja = {
#     "methods": "scooterbug_erpnext.utils.jinja_methods",
#     "filters": "scooterbug_erpnext.utils.jinja_filters"
# }
