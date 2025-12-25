"""
Scheduled tasks for ScooterBug ERPNext
"""
import frappe
from frappe.utils import nowdate, add_days, getdate

def send_booking_reminders():
    """Send reminders for upcoming bookings (1 day before delivery)"""
    tomorrow = add_days(nowdate(), 1)
    
    bookings = frappe.get_all(
        "Equipment Booking",
        filters={
            "delivery_date": tomorrow,
            "booking_status": ["in", ["Confirmed", "Pending"]],
            "docstatus": 1
        },
        fields=["name", "customer_name", "customer_email", "delivery_date", "delivery_time"]
    )
    
    for booking in bookings:
        if booking.customer_email:
            try:
                frappe.sendmail(
                    recipients=[booking.customer_email],
                    subject=f"ScooterBug Booking Reminder - {booking.name}",
                    message=f"""
                    <p>Dear {booking.customer_name},</p>
                    <p>This is a friendly reminder that your equipment rental is scheduled for delivery tomorrow.</p>
                    <p><strong>Booking Details:</strong></p>
                    <ul>
                        <li>Booking ID: {booking.name}</li>
                        <li>Delivery Date: {booking.delivery_date}</li>
                        <li>Delivery Time: {booking.delivery_time or 'As scheduled'}</li>
                    </ul>
                    <p>If you have any questions, please call us at 1-800-726-8284.</p>
                    <p>Thank you for choosing ScooterBug!</p>
                    """
                )
            except Exception as e:
                frappe.log_error(f"Failed to send reminder for {booking.name}: {str(e)}")

def check_overdue_returns():
    """Check for overdue equipment returns and send notifications"""
    today = nowdate()
    
    overdue_bookings = frappe.get_all(
        "Equipment Booking",
        filters={
            "pickup_date": ["<", today],
            "booking_status": "In Progress",
            "docstatus": 1
        },
        fields=["name", "customer_name", "customer_email", "pickup_date"]
    )
    
    for booking in overdue_bookings:
        # Update status to Overdue
        frappe.db.set_value("Equipment Booking", booking.name, "booking_status", "Overdue")
        
        # Send notification email
        if booking.customer_email:
            try:
                frappe.sendmail(
                    recipients=[booking.customer_email],
                    subject=f"ScooterBug - Equipment Return Overdue - {booking.name}",
                    message=f"""
                    <p>Dear {booking.customer_name},</p>
                    <p>Your equipment rental is now overdue for return.</p>
                    <p><strong>Original Return Date:</strong> {booking.pickup_date}</p>
                    <p>Please arrange for equipment return as soon as possible to avoid additional charges.</p>
                    <p>Contact us at 1-800-726-8284 if you need to extend your rental.</p>
                    <p>Thank you,<br>ScooterBug Team</p>
                    """
                )
            except Exception as e:
                frappe.log_error(f"Failed to send overdue notice for {booking.name}: {str(e)}")
    
    frappe.db.commit()

def update_equipment_availability():
    """Update equipment availability based on booking status"""
    # Get all equipment that should be available (no active bookings)
    active_booking_equipment = frappe.get_all(
        "Booking Item",
        filters={
            "parent": ["in", frappe.get_all(
                "Equipment Booking",
                filters={
                    "booking_status": ["in", ["Confirmed", "In Progress"]],
                    "docstatus": 1
                },
                pluck="name"
            ) or ["__none__"]]
        },
        pluck="equipment"
    )
    
    # Update equipment that should be available
    frappe.db.sql("""
        UPDATE `tabEquipment`
        SET status = 'Available', is_available = 1
        WHERE status = 'Rented'
        AND name NOT IN %(active_equipment)s
    """, {"active_equipment": active_booking_equipment or ["__none__"]})
    
    # Update equipment that should be rented
    if active_booking_equipment:
        frappe.db.sql("""
            UPDATE `tabEquipment`
            SET status = 'Rented', is_available = 0
            WHERE name IN %(active_equipment)s
            AND status != 'Maintenance'
        """, {"active_equipment": active_booking_equipment})
    
    frappe.db.commit()
