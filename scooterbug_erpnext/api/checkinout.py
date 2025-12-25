import frappe
from frappe import _
from frappe.utils import now_datetime

@frappe.whitelist()
def process_check_out(booking_id, equipment_id, battery_level=100, condition="Good", notes=None):
    """Process equipment check-out to customer"""
    booking = frappe.get_doc("Equipment Booking", booking_id)
    equipment = frappe.get_doc("Equipment", equipment_id)
    
    # Create check-out log
    log = frappe.get_doc({
        "doctype": "Check In Out Log",
        "log_type": "Check-Out",
        "booking": booking_id,
        "equipment": equipment_id,
        "timestamp": now_datetime(),
        "processed_by": frappe.session.user,
        "location": booking.location,
        "customer_name": booking.customer_name,
        "equipment_condition": condition,
        "battery_level": battery_level,
        "condition_notes": notes
    })
    log.insert(ignore_permissions=True)
    
    # Update equipment status
    equipment.status = "Rented"
    equipment.current_battery_level = battery_level
    equipment.save(ignore_permissions=True)
    
    # Update booking status
    if booking.booking_status == "Confirmed":
        booking.booking_status = "In Progress"
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
    booking = frappe.get_doc("Equipment Booking", booking_id)
    equipment = frappe.get_doc("Equipment", equipment_id)
    
    # Create check-in log
    log = frappe.get_doc({
        "doctype": "Check In Out Log",
        "log_type": "Check-In",
        "booking": booking_id,
        "equipment": equipment_id,
        "timestamp": now_datetime(),
        "processed_by": frappe.session.user,
        "location": booking.location,
        "customer_name": booking.customer_name,
        "equipment_condition": condition,
        "battery_level": battery_level,
        "condition_notes": notes,
        "damage_reported": damage_reported,
        "damage_description": damage_description
    })
    log.insert(ignore_permissions=True)
    
    # Update equipment status
    if damage_reported or condition in ["Poor", "Damaged"]:
        equipment.status = "Maintenance"
        equipment.condition_notes = damage_description or notes
        
        # Create maintenance task if damaged
        if damage_reported:
            create_maintenance_task(equipment_id, booking.location, damage_description)
    else:
        equipment.status = "Available"
    
    if battery_level is not None:
        equipment.current_battery_level = battery_level
    
    equipment.total_rental_days = (equipment.total_rental_days or 0) + booking.rental_days
    equipment.save(ignore_permissions=True)
    
    # Check if all items returned
    all_returned = check_all_items_returned(booking_id)
    if all_returned:
        booking.booking_status = "Completed"
        booking.save(ignore_permissions=True)
    
    return {
        "status": "success",
        "log_id": log.name,
        "message": f"Equipment {equipment_id} checked in successfully",
        "booking_completed": all_returned
    }

def check_all_items_returned(booking_id):
    """Check if all equipment items have been returned"""
    booking = frappe.get_doc("Equipment Booking", booking_id)
    
    for item in booking.items:
        if item.item_type == "Equipment" and item.equipment:
            # Check for check-in log
            check_in = frappe.db.exists("Check In Out Log", {
                "booking": booking_id,
                "equipment": item.equipment,
                "log_type": "Check-In"
            })
            if not check_in:
                return False
    
    return True

def create_maintenance_task(equipment_id, location, description):
    """Create a maintenance task for damaged equipment"""
    task = frappe.get_doc({
        "doctype": "Maintenance Task",
        "task_type": "General Service",
        "equipment": equipment_id,
        "location": location,
        "status": "Pending",
        "priority": "High",
        "description": f"Damage reported during check-in: {description}"
    })
    task.insert(ignore_permissions=True)
    return task.name

def update_equipment_status(doc, method):
    """Update equipment status after check-in/out log is created"""
    equipment = frappe.get_doc("Equipment", doc.equipment)
    
    if doc.log_type == "Check-Out":
        equipment.status = "Rented"
    elif doc.log_type == "Check-In":
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
        "booking_status": "In Progress",
        "pickup_date": today()
    }
    
    if location:
        filters["location"] = location
    
    bookings = frappe.get_all(
        "Equipment Booking",
        filters=filters,
        fields=["name", "customer_name", "pickup_time", "location"]
    )
    
    return bookings

@frappe.whitelist()
def get_pending_check_outs(location=None):
    """Get bookings with pending check-outs for today"""
    from frappe.utils import today
    
    filters = {
        "booking_status": "Confirmed",
        "delivery_date": today()
    }
    
    if location:
        filters["location"] = location
    
    bookings = frappe.get_all(
        "Equipment Booking",
        filters=filters,
        fields=["name", "customer_name", "delivery_time", "location", "delivery_address"]
    )
    
    return bookings
