"""
Waste Log DocType Controller
=============================
Tracks food and inventory waste with reason codes.
Integrates with Stock module for inventory adjustments.
"""

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, nowdate, now_datetime


class WasteLog(Document):
    def validate(self):
        self.calculate_waste_value()
        self.check_approval_requirement()
    
    def before_submit(self):
        if self.requires_approval and not self.approved_by:
            frappe.throw(_("This waste log requires approval before submission"))
        self.status = "Submitted"
        self.create_stock_entry()
    
    def on_cancel(self):
        self.status = "Cancelled"
        self.cancel_stock_entry()
    
    def calculate_waste_value(self):
        """Calculate the monetary value of wasted items."""
        if self.item_code and self.quantity:
            # Get item valuation rate
            valuation_rate = frappe.db.get_value(
                "Item", self.item_code, "valuation_rate"
            ) or 0
            
            self.waste_value = flt(self.quantity) * flt(valuation_rate)
    
    def check_approval_requirement(self):
        """Check if this waste requires manager approval."""
        # Get threshold from settings
        threshold = frappe.db.get_single_value(
            "BookingZone Settings", "waste_approval_threshold"
        ) or 50  # Default $50
        
        if self.waste_value and self.waste_value >= threshold:
            self.requires_approval = 1
            if self.status == "Draft":
                self.status = "Pending Approval"
    
    def create_stock_entry(self):
        """Create Stock Entry to reduce inventory."""
        try:
            stock_entry = frappe.new_doc("Stock Entry")
            stock_entry.stock_entry_type = "Material Issue"
            stock_entry.purpose = "Material Issue"
            stock_entry.waste_log = self.name
            
            # Get expense account for waste
            expense_account = frappe.db.get_single_value(
                "BookingZone Settings", "waste_expense_account"
            ) or frappe.db.get_single_value(
                "Stock Settings", "stock_adjustment_account"
            )
            
            stock_entry.append("items", {
                "item_code": self.item_code,
                "qty": self.quantity,
                "s_warehouse": self.warehouse,
                "expense_account": expense_account,
                "cost_center": frappe.db.get_single_value(
                    "Stock Settings", "default_cost_center"
                )
            })
            
            stock_entry.insert(ignore_permissions=True)
            stock_entry.submit()
            
            frappe.msgprint(
                _("Stock Entry {0} created for waste").format(stock_entry.name),
                alert=True
            )
            
        except Exception as e:
            frappe.log_error(f"Failed to create Stock Entry for waste: {str(e)}")
            frappe.throw(_("Failed to create Stock Entry: {0}").format(str(e)))
    
    def cancel_stock_entry(self):
        """Cancel linked Stock Entry."""
        entries = frappe.get_all(
            "Stock Entry",
            filters={"waste_log": self.name, "docstatus": 1},
            pluck="name"
        )
        
        for entry_name in entries:
            try:
                entry = frappe.get_doc("Stock Entry", entry_name)
                entry.cancel()
            except Exception as e:
                frappe.log_error(f"Failed to cancel Stock Entry {entry_name}: {str(e)}")
    
    @frappe.whitelist()
    def approve(self):
        """Approve the waste log."""
        if not frappe.has_permission("Waste Log", "submit"):
            frappe.throw(_("You don't have permission to approve waste logs"))
        
        self.approved_by = frappe.session.user
        self.approval_date = now_datetime()
        self.status = "Approved"
        self.save(ignore_permissions=True)
        
        return {"status": "Approved", "approved_by": self.approved_by}


@frappe.whitelist()
def get_waste_summary(from_date=None, to_date=None, outlet=None):
    """Get waste summary statistics."""
    filters = {"docstatus": 1}
    
    if from_date:
        filters["waste_date"] = [">=", from_date]
    if to_date:
        filters["waste_date"] = ["<=", to_date]
    if outlet:
        filters["outlet"] = outlet
    
    # Get waste by reason
    waste_by_reason = frappe.db.sql("""
        SELECT 
            waste_reason,
            COUNT(*) as count,
            SUM(waste_value) as total_value
        FROM `tabWaste Log`
        WHERE docstatus = 1
        {date_filter}
        {outlet_filter}
        GROUP BY waste_reason
        ORDER BY total_value DESC
    """.format(
        date_filter=f"AND waste_date >= '{from_date}'" if from_date else "",
        outlet_filter=f"AND outlet = '{outlet}'" if outlet else ""
    ), as_dict=True)
    
    # Get waste by category
    waste_by_category = frappe.db.sql("""
        SELECT 
            waste_category,
            COUNT(*) as count,
            SUM(waste_value) as total_value
        FROM `tabWaste Log`
        WHERE docstatus = 1
        {date_filter}
        {outlet_filter}
        GROUP BY waste_category
        ORDER BY total_value DESC
    """.format(
        date_filter=f"AND waste_date >= '{from_date}'" if from_date else "",
        outlet_filter=f"AND outlet = '{outlet}'" if outlet else ""
    ), as_dict=True)
    
    # Get top wasted items
    top_items = frappe.db.sql("""
        SELECT 
            item_code,
            item_name,
            SUM(quantity) as total_qty,
            SUM(waste_value) as total_value
        FROM `tabWaste Log`
        WHERE docstatus = 1
        {date_filter}
        {outlet_filter}
        GROUP BY item_code, item_name
        ORDER BY total_value DESC
        LIMIT 10
    """.format(
        date_filter=f"AND waste_date >= '{from_date}'" if from_date else "",
        outlet_filter=f"AND outlet = '{outlet}'" if outlet else ""
    ), as_dict=True)
    
    # Get total waste value
    total = frappe.db.sql("""
        SELECT 
            COUNT(*) as total_entries,
            SUM(waste_value) as total_value
        FROM `tabWaste Log`
        WHERE docstatus = 1
        {date_filter}
        {outlet_filter}
    """.format(
        date_filter=f"AND waste_date >= '{from_date}'" if from_date else "",
        outlet_filter=f"AND outlet = '{outlet}'" if outlet else ""
    ), as_dict=True)[0]
    
    return {
        "total_entries": total.total_entries or 0,
        "total_value": total.total_value or 0,
        "by_reason": waste_by_reason,
        "by_category": waste_by_category,
        "top_items": top_items
    }


@frappe.whitelist()
def quick_log_waste(item_code, quantity, waste_reason, outlet=None, warehouse=None):
    """Quick API to log waste from mobile/POS."""
    waste = frappe.new_doc("Waste Log")
    waste.item_code = item_code
    waste.quantity = flt(quantity)
    waste.waste_reason = waste_reason
    waste.outlet = outlet
    waste.warehouse = warehouse or frappe.db.get_single_value(
        "Stock Settings", "default_warehouse"
    )
    waste.waste_date = now_datetime()
    waste.insert()
    
    # Auto-submit if below threshold
    if not waste.requires_approval:
        waste.submit()
    
    return {
        "name": waste.name,
        "status": waste.status,
        "waste_value": waste.waste_value
    }
