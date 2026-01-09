import frappe
from frappe import _
from frappe.utils import now_datetime

@frappe.whitelist()
def process_check_out(booking_id, equipment_id, battery_level=100, condition="Good", notes=None):
    """Process equipment check-out to customer"""
    booking = frappe.get_doc("SB Booking", booking_id)
    equipment = frappe.get_doc("SB Equipment", equipment_id)
    
    # Create check-out log
    log = frappe.get_doc({
        "doctype": "SB Check In Out",
        "check_type": "Check-Out",
        "booking": booking_id,
        "equipment": equipment_id,
        "check_time": now_datetime(),
        "processed_by": frappe.session.user,
        "location": booking.location,
        "customer": booking.customer,
        "equipment_condition": condition,
        "battery_level": battery_level,
        "notes": notes
    })
    log.insert(ignore_permissions=True)
    
    # Update equipment status
    equipment.status = "Rented"
    equipment.current_battery_level = battery_level
    equipment.save(ignore_permissions=True)
    
    # Update booking status
    if booking.status == "Confirmed":
        booking.status = "In Progress"
        booking.save(ignore_permissions=True)
    
    return {
        "status": "success",
        "log_id": log.name,
        "message": f"Equipment {equipment_id} checked out successfully"
    }

@frappe.whitelist()
def process_check_in(booking_id, equipment_id, battery_level=None, condition="Good", 
                     damage_reported=False, damage_description=None, notes=None):
    """Process equipment check-in from customer"""
    booking = frappe.get_doc("SB Booking", booking_id)
    equipment = frappe.get_doc("SB Equipment", equipment_id)
    
    # Create check-in log
    log = frappe.get_doc({
        "doctype": "SB Check In Out",
        "check_type": "Check-In",
        "booking": booking_id,
        "equipment": equipment_id,
        "check_time": now_datetime(),
        "processed_by": frappe.session.user,
        "location": booking.location,
        "customer": booking.customer,
        "equipment_condition": condition,
        "battery_level": battery_level,
        "notes": notes,
        "damage_reported": damage_reported,
        "damage_description": damage_description
    })
    log.insert(ignore_permissions=True)
    
    # Update equipment status
    if damage_reported or condition in ["Poor", "Damaged"]:
        equipment.status = "Maintenance"
        
        # Create damage report if damaged
        if damage_reported:
            create_damage_report(equipment_id, booking_id, booking.location, damage_description)
    else:
        equipment.status = "Available"
    
    if battery_level is not None:
        equipment.current_battery_level = battery_level
    
    equipment.save(ignore_permissions=True)
    
    # Check if all items returned
    all_returned = check_all_items_returned(booking_id)
    if all_returned:
        booking.status = "Completed"
        booking.save(ignore_permissions=True)
    
    return {
        "status": "success",
        "log_id": log.name,
        "message": f"Equipment {equipment_id} checked in successfully",
        "booking_completed": all_returned
    }

def check_all_items_returned(booking_id):
    """Check if all equipment items have been returned"""
    booking = frappe.get_doc("SB Booking", booking_id)
    
    for item in booking.items:
        if item.equipment:
            # Check for check-in log
            check_in = frappe.db.exists("SB Check In Out", {
                "booking": booking_id,
                "equipment": item.equipment,
                "check_type": "Check-In"
            })
            if not check_in:
                return False
    
    return True

def create_damage_report(equipment_id, booking_id, location, description):
    """Create a damage report for damaged equipment"""
    report = frappe.get_doc({
        "doctype": "SB Damage Report",
        "equipment": equipment_id,
        "booking": booking_id,
        "location": location,
        "status": "Reported",
        "damage_description": description,
        "reported_date": frappe.utils.today()
    })
    report.insert(ignore_permissions=True)
    return report.name

def update_equipment_status(doc, method):
    """Update equipment status after check-in/out log is created"""
    equipment = frappe.get_doc("SB Equipment", doc.equipment)
    
    if doc.check_type == "Check-Out":
        equipment.status = "Rented"
    elif doc.check_type == "Check-In":
        if doc.damage_reported:
            equipment.status = "Maintenance"
        else:
            equipment.status = "Available"
    
    equipment.save(ignore_permissions=True)

@frappe.whitelist()
def get_pending_check_ins(location=None):
    """Get bookings with pending check-ins for today"""
    from frappe.utils import today
    
    filters = {
        "status": "In Progress",
        "return_date": today()
    }
    
    if location:
        filters["location"] = location
    
    bookings = frappe.get_all(
        "SB Booking",
        filters=filters,
        fields=["name", "customer", "return_date", "location"]
    )
    
    return bookings

@frappe.whitelist()
def get_pending_check_outs(location=None):
    """Get bookings with pending check-outs for today"""
    from frappe.utils import today
    
    filters = {
        "status": "Confirmed",
        "delivery_date": today()
    }
    
    if location:
        filters["location"] = location
    
    bookings = frappe.get_all(
        "SB Booking",
        filters=filters,
        fields=["name", "customer", "delivery_date", "location", "delivery_address"]
    )
    
    return bookings
