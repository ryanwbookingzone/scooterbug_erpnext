"""
Par Level DocType Controller
=============================
Manages inventory par levels and automatic reordering.
Restaurant-specific inventory management.
"""

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, nowdate, add_days, getdate


class ParLevel(Document):
    def validate(self):
        self.validate_levels()
        self.update_current_stock()
        self.calculate_usage()
        self.update_stock_status()
    
    def validate_levels(self):
        """Validate that levels are in correct order."""
        if self.min_level and self.par_level:
            if flt(self.min_level) >= flt(self.par_level):
                frappe.throw(_("Minimum level must be less than Par level"))
        
        if self.par_level and self.max_level:
            if flt(self.par_level) >= flt(self.max_level):
                frappe.throw(_("Par level must be less than Maximum level"))
    
    def update_current_stock(self):
        """Get current stock from Bin."""
        if self.item_code and self.warehouse:
            current = frappe.db.get_value(
                "Bin",
                {"item_code": self.item_code, "warehouse": self.warehouse},
                "actual_qty"
            ) or 0
            self.current_stock = current
    
    def calculate_usage(self):
        """Calculate average daily usage based on stock ledger."""
        if not self.item_code or not self.warehouse:
            return
        
        days = self.usage_calculation_days or 30
        from_date = add_days(nowdate(), -days)
        
        # Get total consumption from Stock Ledger
        consumption = frappe.db.sql("""
            SELECT ABS(SUM(actual_qty)) as total
            FROM `tabStock Ledger Entry`
            WHERE item_code = %s
            AND warehouse = %s
            AND posting_date >= %s
            AND actual_qty < 0
        """, (self.item_code, self.warehouse, from_date))[0][0] or 0
        
        self.avg_daily_usage = flt(consumption) / days if days > 0 else 0
        
        # Calculate days of stock
        if self.avg_daily_usage > 0:
            self.days_of_stock = flt(self.current_stock) / self.avg_daily_usage
        else:
            self.days_of_stock = 999  # Essentially infinite
    
    def update_stock_status(self):
        """Update stock status based on current levels."""
        if not self.current_stock:
            self.stock_status = "Critical"
        elif self.current_stock <= self.min_level:
            self.stock_status = "Critical"
        elif self.current_stock < self.par_level:
            self.stock_status = "Low"
        elif self.max_level and self.current_stock > self.max_level:
            self.stock_status = "Overstock"
        else:
            self.stock_status = "OK"
    
    @frappe.whitelist()
    def refresh_stock(self):
        """Refresh current stock and status."""
        self.update_current_stock()
        self.calculate_usage()
        self.update_stock_status()
        self.save()
        
        return {
            "current_stock": self.current_stock,
            "stock_status": self.stock_status,
            "days_of_stock": self.days_of_stock,
            "avg_daily_usage": self.avg_daily_usage
        }
    
    @frappe.whitelist()
    def create_reorder(self):
        """Create Material Request for this item."""
        if self.current_stock >= self.par_level:
            frappe.throw(_("Stock is already at or above par level"))
        
        # Calculate order quantity
        order_qty = self.reorder_qty or (self.par_level - self.current_stock)
        
        # Check max level
        if self.max_level:
            max_order = self.max_level - self.current_stock
            order_qty = min(order_qty, max_order)
        
        # Create Material Request
        mr = frappe.new_doc("Material Request")
        mr.material_request_type = "Purchase"
        mr.schedule_date = add_days(nowdate(), self.lead_time_days or 2)
        mr.par_level = self.name
        
        mr.append("items", {
            "item_code": self.item_code,
            "qty": order_qty,
            "warehouse": self.warehouse,
            "schedule_date": mr.schedule_date
        })
        
        mr.insert()
        
        # Update last reorder date
        self.last_reorder_date = nowdate()
        self.save(ignore_permissions=True)
        
        return {
            "material_request": mr.name,
            "order_qty": order_qty
        }


@frappe.whitelist()
def get_par_level_dashboard(outlet=None, warehouse=None):
    """Get dashboard data for par levels."""
    filters = {"is_active": 1}
    if outlet:
        filters["outlet"] = outlet
    if warehouse:
        filters["warehouse"] = warehouse
    
    par_levels = frappe.get_all(
        "Par Level",
        filters=filters,
        fields=[
            "name", "item_code", "item_name", "item_group",
            "warehouse", "outlet", "current_stock", "par_level",
            "min_level", "max_level", "stock_status", "days_of_stock",
            "avg_daily_usage"
        ]
    )
    
    # Refresh stock for each
    for pl in par_levels:
        doc = frappe.get_doc("Par Level", pl.name)
        doc.update_current_stock()
        doc.update_stock_status()
        pl.current_stock = doc.current_stock
        pl.stock_status = doc.stock_status
    
    # Summary statistics
    total = len(par_levels)
    critical = len([p for p in par_levels if p.stock_status == "Critical"])
    low = len([p for p in par_levels if p.stock_status == "Low"])
    ok = len([p for p in par_levels if p.stock_status == "OK"])
    overstock = len([p for p in par_levels if p.stock_status == "Overstock"])
    
    return {
        "summary": {
            "total": total,
            "critical": critical,
            "low": low,
            "ok": ok,
            "overstock": overstock
        },
        "items": par_levels
    }


@frappe.whitelist()
def check_and_create_reorders():
    """Check all par levels and create reorders for items below minimum."""
    par_levels = frappe.get_all(
        "Par Level",
        filters={
            "is_active": 1,
            "auto_reorder": 1
        },
        pluck="name"
    )
    
    reorders_created = []
    
    for pl_name in par_levels:
        pl = frappe.get_doc("Par Level", pl_name)
        pl.update_current_stock()
        
        if pl.current_stock < pl.min_level:
            # Check if there's already a pending MR
            existing = frappe.db.exists(
                "Material Request",
                {
                    "par_level": pl_name,
                    "docstatus": 0
                }
            )
            
            if not existing:
                try:
                    result = pl.create_reorder()
                    reorders_created.append({
                        "item": pl.item_code,
                        "material_request": result["material_request"]
                    })
                except Exception as e:
                    frappe.log_error(f"Failed to create reorder for {pl_name}: {str(e)}")
    
    return {"reorders_created": reorders_created}


@frappe.whitelist()
def calculate_suggested_par_levels(item_code, warehouse, days=30):
    """Calculate suggested par levels based on historical usage."""
    from_date = add_days(nowdate(), -days)
    
    # Get consumption data
    consumption = frappe.db.sql("""
        SELECT 
            DATE(posting_date) as date,
            ABS(SUM(actual_qty)) as qty
        FROM `tabStock Ledger Entry`
        WHERE item_code = %s
        AND warehouse = %s
        AND posting_date >= %s
        AND actual_qty < 0
        GROUP BY DATE(posting_date)
    """, (item_code, warehouse, from_date), as_dict=True)
    
    if not consumption:
        return {
            "avg_daily": 0,
            "max_daily": 0,
            "suggested_min": 0,
            "suggested_par": 0,
            "suggested_max": 0
        }
    
    daily_usage = [c.qty for c in consumption]
    avg_daily = sum(daily_usage) / len(daily_usage) if daily_usage else 0
    max_daily = max(daily_usage) if daily_usage else 0
    
    # Get lead time from item or default
    lead_time = frappe.db.get_value("Item", item_code, "lead_time_days") or 2
    safety_days = 1
    
    suggested_min = avg_daily * (lead_time + safety_days)
    suggested_par = avg_daily * (lead_time + safety_days + 3)  # 3 extra days
    suggested_max = max_daily * (lead_time + safety_days + 7)  # Week buffer
    
    return {
        "avg_daily": round(avg_daily, 2),
        "max_daily": round(max_daily, 2),
        "suggested_min": round(suggested_min, 2),
        "suggested_par": round(suggested_par, 2),
        "suggested_max": round(suggested_max, 2),
        "lead_time_days": lead_time
    }
