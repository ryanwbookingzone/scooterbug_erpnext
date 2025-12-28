"""
BookingZone Installation Script
================================
Sets up the BookingZone app after installation.
"""

import frappe
from frappe import _


def after_install():
    """Run after app installation."""
    print("Setting up BookingZone...")
    
    create_roles()
    create_workspaces()
    create_custom_fields()
    create_default_settings()
    setup_payment_gateways()
    
    print("BookingZone setup complete!")


def create_roles():
    """Create custom roles for restaurant management."""
    roles = [
        {
            "role_name": "Restaurant Manager",
            "desk_access": 1,
            "is_custom": 1
        },
        {
            "role_name": "Kitchen Manager",
            "desk_access": 1,
            "is_custom": 1
        },
        {
            "role_name": "Bar Manager",
            "desk_access": 1,
            "is_custom": 1
        },
        {
            "role_name": "Front of House",
            "desk_access": 1,
            "is_custom": 1
        },
        {
            "role_name": "Back of House",
            "desk_access": 1,
            "is_custom": 1
        }
    ]
    
    for role in roles:
        if not frappe.db.exists("Role", role["role_name"]):
            doc = frappe.new_doc("Role")
            doc.update(role)
            doc.insert(ignore_permissions=True)
            print(f"  Created role: {role['role_name']}")


def create_workspaces():
    """Create workspaces for different modules."""
    workspaces = [
        {
            "name": "Restaurant Operations",
            "module": "BookingZone",
            "category": "Modules",
            "icon": "restaurant",
            "label": "Restaurant Operations",
            "shortcuts": [
                {"type": "Page", "link_to": "restaurant-dashboard", "label": "Dashboard"},
                {"type": "DocType", "link_to": "Recipe", "label": "Recipes"},
                {"type": "DocType", "link_to": "Inventory Count", "label": "Inventory Count"},
                {"type": "DocType", "link_to": "Waste Log", "label": "Waste Log"},
                {"type": "DocType", "link_to": "Par Level", "label": "Par Levels"},
                {"type": "Page", "link_to": "prime-cost-dashboard", "label": "Prime Cost"}
            ],
            "links": [
                {
                    "type": "DocType",
                    "link_to": "Recipe",
                    "label": "Recipe",
                    "link_type": "DocType"
                },
                {
                    "type": "DocType",
                    "link_to": "Inventory Count",
                    "label": "Inventory Count",
                    "link_type": "DocType"
                },
                {
                    "type": "DocType",
                    "link_to": "Waste Log",
                    "label": "Waste Log",
                    "link_type": "DocType"
                },
                {
                    "type": "DocType",
                    "link_to": "Par Level",
                    "label": "Par Level",
                    "link_type": "DocType"
                },
                {
                    "type": "DocType",
                    "link_to": "Prime Cost Report",
                    "label": "Prime Cost Report",
                    "link_type": "DocType"
                },
                {
                    "type": "DocType",
                    "link_to": "Daily Sales Summary",
                    "label": "Daily Sales Summary",
                    "link_type": "DocType"
                }
            ]
        },
        {
            "name": "Payments & Banking",
            "module": "BookingZone",
            "category": "Modules",
            "icon": "bank",
            "label": "Payments & Banking",
            "shortcuts": [
                {"type": "Page", "link_to": "bank-reconciliation", "label": "Bank Reconciliation"},
                {"type": "DocType", "link_to": "Payment Transaction", "label": "Payments"},
                {"type": "DocType", "link_to": "Bank Rule", "label": "Bank Rules"},
                {"type": "DocType", "link_to": "Payment Gateway Configuration", "label": "Gateway Config"}
            ],
            "links": [
                {
                    "type": "DocType",
                    "link_to": "Payment Transaction",
                    "label": "Payment Transaction",
                    "link_type": "DocType"
                },
                {
                    "type": "DocType",
                    "link_to": "Bank Rule",
                    "label": "Bank Rule",
                    "link_type": "DocType"
                },
                {
                    "type": "DocType",
                    "link_to": "Payment Gateway Configuration",
                    "label": "Payment Gateway Configuration",
                    "link_type": "DocType"
                }
            ]
        },
        {
            "name": "Expense Management",
            "module": "BookingZone",
            "category": "Modules",
            "icon": "receipt",
            "label": "Expense Management",
            "shortcuts": [
                {"type": "DocType", "link_to": "Expense Receipt", "label": "Receipts"},
            ],
            "links": [
                {
                    "type": "DocType",
                    "link_to": "Expense Receipt",
                    "label": "Expense Receipt",
                    "link_type": "DocType"
                }
            ]
        }
    ]
    
    for workspace in workspaces:
        if not frappe.db.exists("Workspace", workspace["name"]):
            doc = frappe.new_doc("Workspace")
            doc.update(workspace)
            doc.insert(ignore_permissions=True)
            print(f"  Created workspace: {workspace['name']}")


def create_custom_fields():
    """Create custom fields for integration with existing DocTypes."""
    custom_fields = [
        # Add OCR fields to Purchase Invoice
        {
            "dt": "Purchase Invoice",
            "fieldname": "ocr_processed",
            "fieldtype": "Check",
            "label": "OCR Processed",
            "insert_after": "naming_series",
            "read_only": 1
        },
        {
            "dt": "Purchase Invoice",
            "fieldname": "ocr_confidence",
            "fieldtype": "Percent",
            "label": "OCR Confidence",
            "insert_after": "ocr_processed",
            "read_only": 1
        },
        {
            "dt": "Purchase Invoice",
            "fieldname": "original_receipt",
            "fieldtype": "Attach Image",
            "label": "Original Receipt",
            "insert_after": "ocr_confidence"
        },
        # Add payment fields to Sales Invoice
        {
            "dt": "Sales Invoice",
            "fieldname": "payment_link",
            "fieldtype": "Data",
            "label": "Payment Link",
            "insert_after": "payment_schedule",
            "read_only": 1
        },
        {
            "dt": "Sales Invoice",
            "fieldname": "payment_qr_code",
            "fieldtype": "Attach Image",
            "label": "Payment QR Code",
            "insert_after": "payment_link",
            "read_only": 1
        },
        # Add outlet to POS Order
        {
            "dt": "POS Order",
            "fieldname": "outlet",
            "fieldtype": "Link",
            "label": "Outlet",
            "options": "Outlet",
            "insert_after": "customer"
        },
        # Add recipe link to Menu Item
        {
            "dt": "Menu Item",
            "fieldname": "recipe",
            "fieldtype": "Link",
            "label": "Recipe",
            "options": "Recipe",
            "insert_after": "item_name"
        },
        {
            "dt": "Menu Item",
            "fieldname": "food_cost_percentage",
            "fieldtype": "Percent",
            "label": "Food Cost %",
            "insert_after": "recipe",
            "read_only": 1
        }
    ]
    
    for field in custom_fields:
        # Check if field exists
        existing = frappe.db.exists("Custom Field", {
            "dt": field["dt"],
            "fieldname": field["fieldname"]
        })
        
        if not existing:
            doc = frappe.new_doc("Custom Field")
            doc.update(field)
            doc.module = "BookingZone"
            doc.insert(ignore_permissions=True)
            print(f"  Created custom field: {field['dt']}.{field['fieldname']}")


def create_default_settings():
    """Create default settings for BookingZone."""
    # Create BookingZone Settings doctype if it doesn't exist
    if not frappe.db.exists("DocType", "BookingZone Settings"):
        # Settings will be created via fixtures
        pass
    
    # Set default values
    frappe.db.set_single_value("System Settings", "allow_login_using_mobile_number", 1)
    frappe.db.set_single_value("System Settings", "allow_login_using_user_name", 1)


def setup_payment_gateways():
    """Set up default payment gateway configurations."""
    gateways = [
        {
            "gateway_name": "Stripe",
            "processor_code": "stripe",
            "is_enabled": 0,
            "is_default": 0,
            "supported_currencies": "USD,EUR,GBP,CAD,AUD",
            "supported_payment_methods": "card,apple_pay,google_pay"
        },
        {
            "gateway_name": "PayPal",
            "processor_code": "paypal",
            "is_enabled": 0,
            "is_default": 0,
            "supported_currencies": "USD,EUR,GBP,CAD,AUD",
            "supported_payment_methods": "paypal,venmo"
        },
        {
            "gateway_name": "Square",
            "processor_code": "square",
            "is_enabled": 0,
            "is_default": 0,
            "supported_currencies": "USD,CAD,GBP,AUD,JPY",
            "supported_payment_methods": "card,apple_pay,google_pay,cash_app"
        },
        {
            "gateway_name": "Adyen",
            "processor_code": "adyen",
            "is_enabled": 0,
            "is_default": 0,
            "supported_currencies": "USD,EUR,GBP,CAD,AUD,JPY,CNY",
            "supported_payment_methods": "card,apple_pay,google_pay,klarna,affirm"
        },
        {
            "gateway_name": "GoCardless",
            "processor_code": "gocardless",
            "is_enabled": 0,
            "is_default": 0,
            "supported_currencies": "USD,EUR,GBP,CAD,AUD",
            "supported_payment_methods": "ach,sepa,bacs"
        },
        {
            "gateway_name": "Datacap",
            "processor_code": "datacap",
            "is_enabled": 0,
            "is_default": 0,
            "supported_currencies": "USD",
            "supported_payment_methods": "card,emv,nfc"
        }
    ]
    
    for gateway in gateways:
        if not frappe.db.exists("Payment Gateway Configuration", gateway["gateway_name"]):
            doc = frappe.new_doc("Payment Gateway Configuration")
            doc.update(gateway)
            doc.insert(ignore_permissions=True)
            print(f"  Created payment gateway: {gateway['gateway_name']}")


def before_uninstall():
    """Clean up before uninstalling."""
    print("Cleaning up BookingZone...")
    
    # Remove custom fields
    frappe.db.delete("Custom Field", {"module": "BookingZone"})
    
    # Remove workspaces
    for workspace in ["Restaurant Operations", "Payments & Banking", "Expense Management"]:
        if frappe.db.exists("Workspace", workspace):
            frappe.delete_doc("Workspace", workspace, force=True)
    
    print("BookingZone cleanup complete!")
