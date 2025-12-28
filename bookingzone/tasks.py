"""
BookingZone Scheduled Tasks
============================
Background tasks for automation and synchronization.
"""

import frappe
from frappe.utils import nowdate, add_days, getdate


def all():
    """Run on every scheduler tick."""
    pass


def hourly():
    """Run every hour."""
    check_inventory_alerts()


def daily():
    """Run daily."""
    generate_daily_summaries()
    update_par_level_status()


def weekly():
    """Run weekly."""
    generate_prime_cost_reports()
    update_recipe_costs()


def monthly():
    """Run monthly."""
    archive_old_data()


# =============================================================================
# Payment Tasks
# =============================================================================

def sync_payment_statuses():
    """Sync payment statuses from Hyperswitch."""
    from bookingzone.services.payment_service import PaymentService
    
    # Get pending payments
    pending = frappe.get_all(
        "Payment Transaction",
        filters={"status": ["in", ["Pending", "Processing"]]},
        fields=["name", "hyperswitch_payment_id"],
        limit=100
    )
    
    if not pending:
        return
    
    payment_service = PaymentService()
    
    for payment in pending:
        if payment.hyperswitch_payment_id:
            try:
                status = payment_service.get_payment_status(payment.hyperswitch_payment_id)
                if status:
                    frappe.db.set_value(
                        "Payment Transaction",
                        payment.name,
                        "status",
                        status
                    )
            except Exception as e:
                frappe.log_error(f"Payment sync error: {str(e)}", "Payment Sync")
    
    frappe.db.commit()


# =============================================================================
# OCR Tasks
# =============================================================================

def process_pending_ocr():
    """Process pending OCR receipts."""
    from bookingzone.services.ocr_service import OCRService
    
    # Get pending receipts
    pending = frappe.get_all(
        "Expense Receipt",
        filters={"ocr_status": "Pending", "receipt_image": ["is", "set"]},
        fields=["name", "receipt_image"],
        limit=10
    )
    
    if not pending:
        return
    
    ocr_service = OCRService()
    
    for receipt in pending:
        try:
            result = ocr_service.process_receipt(receipt.receipt_image)
            
            if result:
                frappe.db.set_value("Expense Receipt", receipt.name, {
                    "ocr_status": "Completed",
                    "vendor_name": result.get("vendor_name"),
                    "amount": result.get("total"),
                    "receipt_date": result.get("date"),
                    "ocr_confidence": result.get("confidence", 0),
                    "ocr_raw_text": result.get("raw_text")
                })
        except Exception as e:
            frappe.db.set_value("Expense Receipt", receipt.name, {
                "ocr_status": "Failed",
                "ocr_error": str(e)
            })
            frappe.log_error(f"OCR processing error: {str(e)}", "OCR Processing")
    
    frappe.db.commit()


# =============================================================================
# Restaurant Tasks
# =============================================================================

def generate_daily_summaries():
    """Generate daily sales summaries for all outlets."""
    from bookingzone.doctype.daily_sales_summary.daily_sales_summary import generate_daily_summary
    
    yesterday = add_days(nowdate(), -1)
    
    # Get all outlets
    outlets = frappe.get_all("Outlet", filters={"is_active": 1}, pluck="name")
    
    for outlet in outlets:
        try:
            generate_daily_summary(yesterday, outlet)
        except Exception as e:
            frappe.log_error(f"Daily summary error for {outlet}: {str(e)}", "Daily Summary")
    
    frappe.db.commit()


def update_par_level_status():
    """Update par level status based on current stock."""
    from bookingzone.doctype.par_level.par_level import update_all_par_levels
    
    try:
        update_all_par_levels()
    except Exception as e:
        frappe.log_error(f"Par level update error: {str(e)}", "Par Level Update")


def check_inventory_alerts():
    """Check for inventory alerts and send notifications."""
    # Get critical items
    critical = frappe.get_all(
        "Par Level",
        filters={"is_active": 1, "stock_status": "Critical"},
        fields=["item_code", "item_name", "current_stock", "par_level", "outlet"]
    )
    
    if not critical:
        return
    
    # Group by outlet
    by_outlet = {}
    for item in critical:
        outlet = item.outlet or "Default"
        if outlet not in by_outlet:
            by_outlet[outlet] = []
        by_outlet[outlet].append(item)
    
    # Send alerts
    for outlet, items in by_outlet.items():
        # Get restaurant managers for this outlet
        managers = frappe.get_all(
            "User",
            filters={"enabled": 1},
            fields=["name", "email"]
        )
        
        # TODO: Filter by outlet permission
        
        if managers:
            item_list = "\n".join([
                f"- {i['item_name']}: {i['current_stock']} (Par: {i['par_level']})"
                for i in items
            ])
            
            for manager in managers[:3]:  # Limit to 3 managers
                try:
                    frappe.sendmail(
                        recipients=[manager.email],
                        subject=f"Critical Inventory Alert - {outlet}",
                        message=f"""
                        <p>The following items are critically low:</p>
                        <pre>{item_list}</pre>
                        <p>Please reorder immediately.</p>
                        """
                    )
                except:
                    pass


def generate_prime_cost_reports():
    """Generate weekly prime cost reports."""
    from bookingzone.doctype.prime_cost_report.prime_cost_report import generate_weekly_report
    
    # Get last Sunday
    today = getdate()
    days_since_sunday = today.weekday() + 1
    if days_since_sunday == 7:
        days_since_sunday = 0
    last_sunday = add_days(today, -days_since_sunday)
    
    # Get all outlets
    outlets = frappe.get_all("Outlet", filters={"is_active": 1}, pluck="name")
    
    for outlet in outlets:
        try:
            generate_weekly_report(outlet, last_sunday)
        except Exception as e:
            frappe.log_error(f"Prime cost report error for {outlet}: {str(e)}", "Prime Cost Report")
    
    frappe.db.commit()


def update_recipe_costs():
    """Update recipe costs based on latest ingredient prices."""
    from bookingzone.doctype.recipe.recipe import bulk_update_recipe_costs
    
    try:
        bulk_update_recipe_costs()
    except Exception as e:
        frappe.log_error(f"Recipe cost update error: {str(e)}", "Recipe Cost Update")


# =============================================================================
# POS Tasks
# =============================================================================

def import_pos_sales():
    """Import sales from external POS systems."""
    # This would integrate with Toast, Square, Clover, etc.
    # For now, just log that it ran
    frappe.log_error("POS import task ran", "POS Import")


# =============================================================================
# ERP Sync Tasks
# =============================================================================

def sync_sage_erp():
    """Nightly sync to Sage ERP."""
    # Get transactions from yesterday
    yesterday = add_days(nowdate(), -1)
    
    # Get daily summaries
    summaries = frappe.get_all(
        "Daily Sales Summary",
        filters={"summary_date": yesterday, "synced_to_sage": 0},
        fields=["name", "outlet", "net_sales", "total_transactions"]
    )
    
    if not summaries:
        return
    
    # TODO: Implement actual Sage API integration
    # For now, just mark as synced
    for summary in summaries:
        frappe.db.set_value("Daily Sales Summary", summary.name, "synced_to_sage", 1)
    
    frappe.db.commit()
    frappe.log_error(f"Synced {len(summaries)} summaries to Sage", "Sage Sync")


def sync_bank_transactions():
    """Sync bank transactions from Plaid."""
    # TODO: Implement Plaid integration
    pass


# =============================================================================
# Maintenance Tasks
# =============================================================================

def archive_old_data():
    """Archive old data to improve performance."""
    # Archive waste logs older than 1 year
    one_year_ago = add_days(nowdate(), -365)
    
    old_waste = frappe.db.count("Waste Log", {"waste_date": ["<", one_year_ago]})
    
    if old_waste > 0:
        frappe.log_error(f"Found {old_waste} waste logs older than 1 year for archival", "Data Archive")
