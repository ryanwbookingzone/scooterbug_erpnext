"""
Custom permission handlers for ScooterBug ERPNext
"""
import frappe

def equipment_permission(doc, user=None, permission_type=None):
    """
    Custom permission check for Equipment doctype
    - All users can read equipment
    - Only System Manager and ScooterBug Admin can modify
    """
    if not user:
        user = frappe.session.user
    
    # Allow read for everyone
    if permission_type == "read":
        return True
    
    # Check for admin roles for write operations
    user_roles = frappe.get_roles(user)
    admin_roles = ["System Manager", "ScooterBug Admin", "Administrator"]
    
    return bool(set(user_roles) & set(admin_roles))

def booking_permission(doc, user=None, permission_type=None):
    """
    Custom permission check for Equipment Booking doctype
    - Users can read their own bookings
    - Staff can read all bookings
    - Only managers can delete
    """
    if not user:
        user = frappe.session.user
    
    user_roles = frappe.get_roles(user)
    
    # System managers have full access
    if "System Manager" in user_roles or "Administrator" in user_roles:
        return True
    
    # ScooterBug Admin and Staff can read/write all
    if "ScooterBug Admin" in user_roles or "ScooterBug Staff" in user_roles:
        if permission_type != "delete":
            return True
    
    # Regular users can only access their own bookings
    if permission_type == "read":
        if hasattr(doc, "customer_email"):
            user_email = frappe.db.get_value("User", user, "email")
            return doc.customer_email == user_email
    
    return False
