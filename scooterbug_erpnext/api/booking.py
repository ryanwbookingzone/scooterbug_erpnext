import frappe
from frappe import _

@frappe.whitelist()
def get_available_equipment(location, start_date, end_date, equipment_type=None):
    """Get available equipment for a given location and date range"""
    filters = {
        "location": location,
        "status": "Available"
    }
    
    if equipment_type:
        filters["equipment_type"] = equipment_type
    
    # Get all equipment at location
    equipment_list = frappe.get_all(
        "SB Equipment",
        filters=filters,
        fields=["*"]
    )
    
    # Filter out equipment that has bookings during the requested period
    available = []
    for eq in equipment_list:
        # Check for conflicting bookings
        conflicts = frappe.db.sql("""
            SELECT eb.name 
            FROM `tabSB Booking` eb
            JOIN `tabSB Booking Item` bi ON bi.parent = eb.name
            WHERE bi.equipment = %s
            AND eb.status NOT IN ('Cancelled', 'Completed')
            AND eb.delivery_date <= %s
            AND eb.return_date >= %s
        """, (eq.name, end_date, start_date))
        
        if not conflicts:
            available.append(eq)
    
    return available

@frappe.whitelist()
def create_booking(customer, location, start_date, end_date, delivery_date, delivery_time,
                   pickup_date, pickup_time, delivery_address, items, damage_waiver=False,
                   travel_agent=None, notes=None):
    """Create a new equipment booking"""
    
    # Calculate rental days
    from datetime import datetime
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    rental_days = (end - start).days + 1
    
    # Create booking document
    booking = frappe.get_doc({
        "doctype": "SB Booking",
        "customer": customer,
        "location": location,
        "delivery_date": delivery_date,
        "return_date": pickup_date,
        "delivery_address": delivery_address,
        "damage_waiver_accepted": damage_waiver,
        "travel_agent": travel_agent,
        "special_requests": notes,
        "status": "Draft",
        "items": []
    })
    
    # Add items
    equipment_total = 0
    damage_waiver_total = 0
    
    for item in items:
        eq = frappe.get_doc("SB Equipment", item.get("equipment"))
        eq_type = frappe.get_doc("SB Equipment Type", eq.equipment_type)
        daily_rate = eq_type.daily_rate or 0
        dw_rate = eq_type.damage_waiver_rate if damage_waiver else 0
        subtotal = daily_rate * rental_days
        dw_total = dw_rate * rental_days
        
        booking.append("items", {
            "equipment": item.get("equipment"),
            "equipment_type": eq.equipment_type,
            "quantity": 1,
            "daily_rate": daily_rate,
            "subtotal": subtotal,
            "damage_waiver_rate": dw_rate,
            "damage_waiver_total": dw_total,
            "line_total": subtotal + dw_total
        })
        
        equipment_total += subtotal
        damage_waiver_total += dw_total
    
    booking.equipment_total = equipment_total
    booking.damage_waiver_total = damage_waiver_total
    booking.grand_total = equipment_total + damage_waiver_total
    
    booking.insert(ignore_permissions=True)
    
    return {
        "booking_id": booking.name,
        "grand_total": booking.grand_total
    }

@frappe.whitelist()
def confirm_booking(booking_id, payment_reference=None):
    """Confirm a booking and update equipment status"""
    booking = frappe.get_doc("SB Booking", booking_id)
    
    if booking.status != "Draft":
        frappe.throw(_("Booking is not in Draft status"))
    
    # Update equipment status to Reserved
    for item in booking.items:
        if item.equipment:
            frappe.db.set_value("SB Equipment", item.equipment, "status", "Reserved")
    
    booking.status = "Confirmed"
    booking.payment_status = "Paid"
    booking.payment_reference = payment_reference
    booking.save(ignore_permissions=True)
    
    return {"status": "success", "booking_id": booking_id}

@frappe.whitelist()
def cancel_booking(booking_id, reason=None):
    """Cancel a booking and release equipment"""
    booking = frappe.get_doc("SB Booking", booking_id)
    
    if booking.status in ["Completed", "Cancelled"]:
        frappe.throw(_("Booking cannot be cancelled"))
    
    # Release equipment
    for item in booking.items:
        if item.equipment:
            frappe.db.set_value("SB Equipment", item.equipment, "status", "Available")
    
    booking.status = "Cancelled"
    booking.cancellation_reason = reason
    booking.save(ignore_permissions=True)
    
    return {"status": "success", "booking_id": booking_id}

def on_booking_submit(doc, method):
    """Called when booking is submitted"""
    # Update equipment status
    for item in doc.items:
        if item.equipment:
            frappe.db.set_value("SB Equipment", item.equipment, "status", "Reserved")

def on_booking_cancel(doc, method):
    """Called when booking is cancelled"""
    # Release equipment
    for item in doc.items:
        if item.equipment:
            frappe.db.set_value("SB Equipment", item.equipment, "status", "Available")
