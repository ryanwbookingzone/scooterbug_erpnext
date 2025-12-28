"""
Daily Sales Summary DocType Controller
=======================================
Aggregates daily sales data from POS Orders and other sources.
Provides metrics for restaurant management dashboards.
"""

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, getdate, add_days


class DailySalesSummary(Document):
    def validate(self):
        self.calculate_derived_fields()
    
    def calculate_derived_fields(self):
        """Calculate computed fields."""
        # Net sales
        self.net_sales = flt(self.gross_sales) - flt(self.discounts)
        
        # Total revenue
        self.total_revenue = flt(self.net_sales) + flt(self.tax_collected) + flt(self.tips)
        
        # Average ticket size
        if self.total_transactions and self.total_transactions > 0:
            self.avg_ticket_size = flt(self.net_sales) / self.total_transactions
        else:
            self.avg_ticket_size = 0
        
        # Average spend per guest
        if self.guest_count and self.guest_count > 0:
            self.avg_spend_per_guest = flt(self.net_sales) / self.guest_count
        else:
            self.avg_spend_per_guest = 0
        
        # Sales per labor hour
        if self.labor_hours and self.labor_hours > 0:
            self.sales_per_labor_hour = flt(self.net_sales) / self.labor_hours
        else:
            self.sales_per_labor_hour = 0
        
        # Labor cost percentage
        if self.net_sales and self.net_sales > 0:
            self.labor_cost_percentage = (flt(self.labor_cost) / self.net_sales) * 100
        else:
            self.labor_cost_percentage = 0
    
    @frappe.whitelist()
    def populate_from_pos(self):
        """Populate summary from POS Orders for the day."""
        if not self.summary_date or not self.outlet:
            frappe.throw(_("Please set date and outlet first"))
        
        # Get POS Orders for this date and outlet
        pos_data = frappe.db.sql("""
            SELECT 
                COUNT(*) as total_orders,
                SUM(grand_total) as gross_sales,
                SUM(discount_amount) as discounts,
                SUM(total_taxes_and_charges) as tax,
                SUM(CASE WHEN payment_method = 'Cash' THEN paid_amount ELSE 0 END) as cash,
                SUM(CASE WHEN payment_method = 'Card' THEN paid_amount ELSE 0 END) as card,
                SUM(CASE WHEN payment_method = 'Gift Card' THEN paid_amount ELSE 0 END) as gift_card,
                SUM(CASE WHEN payment_method = 'Game Card' THEN paid_amount ELSE 0 END) as game_card,
                SUM(CASE WHEN payment_method = 'Points' THEN paid_amount ELSE 0 END) as points
            FROM `tabPOS Order`
            WHERE DATE(creation) = %s
            AND outlet = %s
            AND docstatus = 1
        """, (self.summary_date, self.outlet), as_dict=True)[0]
        
        if pos_data:
            self.total_transactions = pos_data.total_orders or 0
            self.gross_sales = pos_data.gross_sales or 0
            self.discounts = pos_data.discounts or 0
            self.tax_collected = pos_data.tax or 0
            self.cash_payments = pos_data.cash or 0
            self.card_payments = pos_data.card or 0
            self.gift_card_payments = pos_data.gift_card or 0
            self.game_card_payments = pos_data.game_card or 0
            self.points_payments = pos_data.points or 0
        
        # Get sales by category from POS Order Items
        category_data = frappe.db.sql("""
            SELECT 
                item.item_group,
                SUM(poi.amount) as total
            FROM `tabPOS Order Item` poi
            JOIN `tabPOS Order` po ON poi.parent = po.name
            JOIN `tabItem` item ON poi.item_code = item.name
            WHERE DATE(po.creation) = %s
            AND po.outlet = %s
            AND po.docstatus = 1
            GROUP BY item.item_group
        """, (self.summary_date, self.outlet), as_dict=True)
        
        for cat in category_data:
            group = (cat.item_group or "").lower()
            if "food" in group:
                self.food_sales = flt(self.food_sales) + flt(cat.total)
            elif "beverage" in group or "drink" in group:
                self.beverage_sales = flt(self.beverage_sales) + flt(cat.total)
            elif "merchandise" in group or "retail" in group:
                self.merchandise_sales = flt(self.merchandise_sales) + flt(cat.total)
            elif "entertainment" in group or "game" in group:
                self.entertainment_sales = flt(self.entertainment_sales) + flt(cat.total)
            elif "service" in group:
                self.service_sales = flt(self.service_sales) + flt(cat.total)
            else:
                self.other_sales = flt(self.other_sales) + flt(cat.total)
        
        self.calculate_derived_fields()
        return True


@frappe.whitelist()
def generate_daily_summary(summary_date, outlet):
    """Generate or update daily sales summary."""
    # Check if summary exists
    existing = frappe.db.exists(
        "Daily Sales Summary",
        {"summary_date": summary_date, "outlet": outlet}
    )
    
    if existing:
        summary = frappe.get_doc("Daily Sales Summary", existing)
    else:
        summary = frappe.new_doc("Daily Sales Summary")
        summary.summary_date = summary_date
        summary.outlet = outlet
    
    summary.populate_from_pos()
    summary.save(ignore_permissions=True)
    
    return summary.name


@frappe.whitelist()
def get_sales_trend(outlet, days=30):
    """Get sales trend for the past N days."""
    from_date = add_days(getdate(), -days)
    
    data = frappe.db.sql("""
        SELECT 
            summary_date,
            net_sales,
            total_transactions,
            avg_ticket_size,
            labor_cost_percentage
        FROM `tabDaily Sales Summary`
        WHERE outlet = %s
        AND summary_date >= %s
        ORDER BY summary_date ASC
    """, (outlet, from_date), as_dict=True)
    
    return data


@frappe.whitelist()
def compare_periods(outlet, period1_start, period1_end, period2_start, period2_end):
    """Compare two time periods."""
    def get_period_totals(start, end):
        return frappe.db.sql("""
            SELECT 
                SUM(net_sales) as total_sales,
                SUM(total_transactions) as total_transactions,
                AVG(avg_ticket_size) as avg_ticket,
                SUM(labor_cost) as total_labor,
                AVG(labor_cost_percentage) as avg_labor_pct
            FROM `tabDaily Sales Summary`
            WHERE outlet = %s
            AND summary_date BETWEEN %s AND %s
        """, (outlet, start, end), as_dict=True)[0]
    
    period1 = get_period_totals(period1_start, period1_end)
    period2 = get_period_totals(period2_start, period2_end)
    
    # Calculate changes
    def pct_change(new, old):
        if old and old > 0:
            return ((new or 0) - old) / old * 100
        return 0
    
    return {
        "period1": period1,
        "period2": period2,
        "changes": {
            "sales": pct_change(period2.total_sales, period1.total_sales),
            "transactions": pct_change(period2.total_transactions, period1.total_transactions),
            "avg_ticket": pct_change(period2.avg_ticket, period1.avg_ticket),
            "labor_cost": pct_change(period2.total_labor, period1.total_labor)
        }
    }
