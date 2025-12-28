"""
Inventory Count DocType Controller
===================================
Restaurant-specific inventory counting with variance tracking.
Integrates with ERPNext Stock module for reconciliation.
"""

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, nowdate


class InventoryCount(Document):
    def validate(self):
        self.calculate_totals()
        self.validate_items()
    
    def before_submit(self):
        self.status = "Submitted"
        self.create_stock_reconciliation()
    
    def on_cancel(self):
        self.status = "Cancelled"
        self.cancel_stock_reconciliation()
    
    def calculate_totals(self):
        """Calculate total values and variances."""
        total_counted = 0
        total_system = 0
        
        for item in self.items:
            # Get current stock qty and value
            if item.item_code and self.warehouse:
                system_qty, system_value = self.get_system_stock(
                    item.item_code,
                    self.warehouse
                )
                item.system_qty = system_qty
                item.system_value = system_value
                
                # Calculate counted value
                item_rate = self.get_item_rate(item.item_code)
                item.counted_value = flt(item.counted_qty) * flt(item_rate)
                
                # Calculate variance
                item.variance_qty = flt(item.counted_qty) - flt(item.system_qty)
                item.variance_value = flt(item.counted_value) - flt(item.system_value)
                
                total_counted += flt(item.counted_value)
                total_system += flt(item.system_value)
        
        self.total_counted_value = total_counted
        self.total_system_value = total_system
        self.total_variance = total_counted - total_system
        
        if total_system > 0:
            self.variance_percentage = (self.total_variance / total_system) * 100
        else:
            self.variance_percentage = 0
    
    def get_system_stock(self, item_code, warehouse):
        """Get current system stock quantity and value."""
        bin_data = frappe.db.get_value(
            "Bin",
            {"item_code": item_code, "warehouse": warehouse},
            ["actual_qty", "stock_value"],
            as_dict=True
        )
        
        if bin_data:
            return bin_data.actual_qty or 0, bin_data.stock_value or 0
        return 0, 0
    
    def get_item_rate(self, item_code):
        """Get item valuation rate."""
        return frappe.db.get_value("Item", item_code, "valuation_rate") or 0
    
    def validate_items(self):
        """Validate count items."""
        seen_items = set()
        for item in self.items:
            if item.item_code in seen_items:
                frappe.throw(
                    _("Item {0} appears multiple times").format(item.item_code)
                )
            seen_items.add(item.item_code)
            
            if flt(item.counted_qty) < 0:
                frappe.throw(
                    _("Counted quantity cannot be negative for {0}").format(item.item_code)
                )
    
    def create_stock_reconciliation(self):
        """Create Stock Reconciliation entry from count."""
        if not self.items:
            return
        
        # Only create if there are variances
        items_with_variance = [i for i in self.items if flt(i.variance_qty) != 0]
        if not items_with_variance:
            return
        
        try:
            recon = frappe.new_doc("Stock Reconciliation")
            recon.purpose = "Stock Reconciliation"
            recon.expense_account = frappe.db.get_single_value(
                "Stock Settings", "stock_adjustment_account"
            )
            recon.cost_center = frappe.db.get_single_value(
                "Stock Settings", "default_cost_center"
            )
            
            for item in items_with_variance:
                recon.append("items", {
                    "item_code": item.item_code,
                    "warehouse": self.warehouse,
                    "qty": item.counted_qty,
                    "valuation_rate": self.get_item_rate(item.item_code)
                })
            
            recon.inventory_count = self.name
            recon.insert(ignore_permissions=True)
            recon.submit()
            
            frappe.msgprint(
                _("Stock Reconciliation {0} created").format(recon.name),
                alert=True
            )
            
        except Exception as e:
            frappe.log_error(f"Failed to create Stock Reconciliation: {str(e)}")
            frappe.throw(_("Failed to create Stock Reconciliation: {0}").format(str(e)))
    
    def cancel_stock_reconciliation(self):
        """Cancel linked Stock Reconciliation."""
        recons = frappe.get_all(
            "Stock Reconciliation",
            filters={"inventory_count": self.name, "docstatus": 1},
            pluck="name"
        )
        
        for recon_name in recons:
            try:
                recon = frappe.get_doc("Stock Reconciliation", recon_name)
                recon.cancel()
            except Exception as e:
                frappe.log_error(f"Failed to cancel Stock Reconciliation {recon_name}: {str(e)}")
    
    @frappe.whitelist()
    def load_items_from_warehouse(self):
        """Load all items from the selected warehouse."""
        if not self.warehouse:
            frappe.throw(_("Please select a warehouse first"))
        
        # Get all items with stock in this warehouse
        items = frappe.db.sql("""
            SELECT 
                bin.item_code,
                item.item_name,
                item.stock_uom,
                bin.actual_qty,
                bin.stock_value
            FROM `tabBin` bin
            JOIN `tabItem` item ON bin.item_code = item.name
            WHERE bin.warehouse = %s
            AND bin.actual_qty > 0
            AND item.is_stock_item = 1
            ORDER BY item.item_name
        """, (self.warehouse,), as_dict=True)
        
        self.items = []
        for item in items:
            self.append("items", {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "uom": item.stock_uom,
                "system_qty": item.actual_qty,
                "system_value": item.stock_value,
                "counted_qty": 0  # To be filled by user
            })
        
        return len(items)
    
    @frappe.whitelist()
    def load_items_by_category(self, item_group):
        """Load items from a specific category."""
        if not self.warehouse:
            frappe.throw(_("Please select a warehouse first"))
        
        items = frappe.db.sql("""
            SELECT 
                bin.item_code,
                item.item_name,
                item.stock_uom,
                bin.actual_qty,
                bin.stock_value
            FROM `tabBin` bin
            JOIN `tabItem` item ON bin.item_code = item.name
            WHERE bin.warehouse = %s
            AND item.item_group = %s
            AND item.is_stock_item = 1
            ORDER BY item.item_name
        """, (self.warehouse, item_group), as_dict=True)
        
        for item in items:
            # Check if already in list
            existing = [i for i in self.items if i.item_code == item.item_code]
            if not existing:
                self.append("items", {
                    "item_code": item.item_code,
                    "item_name": item.item_name,
                    "uom": item.stock_uom,
                    "system_qty": item.actual_qty,
                    "system_value": item.stock_value,
                    "counted_qty": 0
                })
        
        return len(items)


@frappe.whitelist()
def get_count_summary(count_name):
    """Get summary statistics for an inventory count."""
    count = frappe.get_doc("Inventory Count", count_name)
    
    items_counted = len(count.items)
    items_with_variance = len([i for i in count.items if flt(i.variance_qty) != 0])
    items_over = len([i for i in count.items if flt(i.variance_qty) > 0])
    items_under = len([i for i in count.items if flt(i.variance_qty) < 0])
    
    return {
        "count_date": count.count_date,
        "warehouse": count.warehouse,
        "outlet": count.outlet,
        "status": count.status,
        "items_counted": items_counted,
        "items_with_variance": items_with_variance,
        "items_over": items_over,
        "items_under": items_under,
        "total_counted_value": count.total_counted_value,
        "total_system_value": count.total_system_value,
        "total_variance": count.total_variance,
        "variance_percentage": count.variance_percentage
    }


@frappe.whitelist()
def create_count_from_template(template_name, count_date=None):
    """Create a new inventory count from a saved template."""
    template = frappe.get_doc("Inventory Count", template_name)
    
    new_count = frappe.new_doc("Inventory Count")
    new_count.count_date = count_date or nowdate()
    new_count.outlet = template.outlet
    new_count.warehouse = template.warehouse
    new_count.count_type = template.count_type
    
    for item in template.items:
        new_count.append("items", {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "uom": item.uom,
            "counted_qty": 0
        })
    
    new_count.insert()
    return new_count.name
