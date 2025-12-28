"""
Prime Cost Report DocType Controller
=====================================
Restaurant prime cost calculation and analysis.
Prime Cost = Food Cost + Labor Cost (typically 60-65% of sales)
"""

import frappe
import json
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, getdate, add_days


class PrimeCostReport(Document):
    def validate(self):
        self.calculate_costs()
    
    def calculate_costs(self):
        """Calculate all cost metrics."""
        # Cost of Goods Sold
        self.cost_of_goods_sold = (
            flt(self.beginning_inventory) + 
            flt(self.purchases) - 
            flt(self.ending_inventory)
        )
        
        # Total Labor Cost
        self.total_labor_cost = (
            flt(self.management_labor) + 
            flt(self.hourly_labor) + 
            flt(self.benefits_taxes)
        )
        
        # Total Prime Cost
        self.total_prime_cost = flt(self.cost_of_goods_sold) + flt(self.total_labor_cost)
        
        # Percentages
        if self.total_sales and flt(self.total_sales) > 0:
            self.food_cost_percentage = (flt(self.cost_of_goods_sold) / flt(self.total_sales)) * 100
            self.labor_cost_percentage = (flt(self.total_labor_cost) / flt(self.total_sales)) * 100
            self.prime_cost_percentage = (flt(self.total_prime_cost) / flt(self.total_sales)) * 100
        else:
            self.food_cost_percentage = 0
            self.labor_cost_percentage = 0
            self.prime_cost_percentage = 0
        
        # Variance from target
        self.variance_from_target = flt(self.prime_cost_percentage) - flt(self.prime_cost_target)
    
    @frappe.whitelist()
    def populate_from_data(self):
        """Populate report from actual data sources."""
        if not self.from_date or not self.to_date or not self.outlet:
            frappe.throw(_("Please set date range and outlet first"))
        
        # Get sales from Daily Sales Summary
        sales_data = frappe.db.sql("""
            SELECT SUM(net_sales) as total_sales
            FROM `tabDaily Sales Summary`
            WHERE outlet = %s
            AND summary_date BETWEEN %s AND %s
        """, (self.outlet, self.from_date, self.to_date), as_dict=True)[0]
        
        self.total_sales = sales_data.total_sales or 0
        
        # Get purchases from Purchase Invoices
        purchases = frappe.db.sql("""
            SELECT SUM(grand_total) as total
            FROM `tabPurchase Invoice`
            WHERE supplier IN (
                SELECT name FROM `tabSupplier` 
                WHERE supplier_group IN ('Food Suppliers', 'Beverage Suppliers')
            )
            AND posting_date BETWEEN %s AND %s
            AND docstatus = 1
        """, (self.from_date, self.to_date))[0][0] or 0
        
        self.purchases = purchases
        
        # Get inventory values from Stock Ledger
        # Beginning inventory (value at start date)
        beginning = self.get_inventory_value(self.from_date)
        self.beginning_inventory = beginning
        
        # Ending inventory (value at end date)
        ending = self.get_inventory_value(add_days(self.to_date, 1))
        self.ending_inventory = ending
        
        # Get labor costs from payroll or time entries
        labor_data = self.get_labor_costs()
        self.management_labor = labor_data.get("management", 0)
        self.hourly_labor = labor_data.get("hourly", 0)
        self.benefits_taxes = labor_data.get("benefits", 0)
        
        # Generate breakdowns
        self.generate_breakdowns()
        
        # Calculate
        self.calculate_costs()
        self.status = "Calculated"
        
        return True
    
    def get_inventory_value(self, as_of_date):
        """Get total inventory value as of a date."""
        # Get food/beverage item groups
        food_groups = frappe.get_all(
            "Item Group",
            filters={"name": ["like", "%Food%"]},
            pluck="name"
        )
        beverage_groups = frappe.get_all(
            "Item Group",
            filters={"name": ["like", "%Beverage%"]},
            pluck="name"
        )
        groups = food_groups + beverage_groups
        
        if not groups:
            groups = ["Products"]  # Fallback
        
        value = frappe.db.sql("""
            SELECT SUM(stock_value) as total
            FROM `tabBin` bin
            JOIN `tabItem` item ON bin.item_code = item.name
            WHERE item.item_group IN %s
        """, (groups,))[0][0] or 0
        
        return value
    
    def get_labor_costs(self):
        """Get labor costs for the period."""
        # Try to get from Salary Slips
        salary_data = frappe.db.sql("""
            SELECT 
                SUM(CASE WHEN emp.employment_type = 'Full-time' THEN ss.gross_pay ELSE 0 END) as management,
                SUM(CASE WHEN emp.employment_type = 'Part-time' THEN ss.gross_pay ELSE 0 END) as hourly
            FROM `tabSalary Slip` ss
            JOIN `tabEmployee` emp ON ss.employee = emp.name
            WHERE ss.start_date >= %s
            AND ss.end_date <= %s
            AND ss.docstatus = 1
        """, (self.from_date, self.to_date), as_dict=True)
        
        if salary_data and salary_data[0]:
            management = salary_data[0].management or 0
            hourly = salary_data[0].hourly or 0
            # Estimate benefits at 20% of gross
            benefits = (management + hourly) * 0.20
            return {
                "management": management,
                "hourly": hourly,
                "benefits": benefits
            }
        
        # Fallback: Get from Daily Sales Summary labor data
        labor_data = frappe.db.sql("""
            SELECT SUM(labor_cost) as total
            FROM `tabDaily Sales Summary`
            WHERE outlet = %s
            AND summary_date BETWEEN %s AND %s
        """, (self.outlet, self.from_date, self.to_date))[0][0] or 0
        
        # Estimate split
        return {
            "management": labor_data * 0.3,
            "hourly": labor_data * 0.55,
            "benefits": labor_data * 0.15
        }
    
    def generate_breakdowns(self):
        """Generate detailed cost breakdowns."""
        # Food cost breakdown by category
        food_breakdown = frappe.db.sql("""
            SELECT 
                item.item_group,
                SUM(pi_item.amount) as total
            FROM `tabPurchase Invoice Item` pi_item
            JOIN `tabPurchase Invoice` pi ON pi_item.parent = pi.name
            JOIN `tabItem` item ON pi_item.item_code = item.name
            WHERE pi.posting_date BETWEEN %s AND %s
            AND pi.docstatus = 1
            GROUP BY item.item_group
            ORDER BY total DESC
            LIMIT 10
        """, (self.from_date, self.to_date), as_dict=True)
        
        self.food_cost_breakdown = json.dumps(food_breakdown, default=str)
        
        # Labor breakdown by department/role
        labor_breakdown = frappe.db.sql("""
            SELECT 
                emp.department,
                COUNT(*) as headcount,
                SUM(ss.gross_pay) as total
            FROM `tabSalary Slip` ss
            JOIN `tabEmployee` emp ON ss.employee = emp.name
            WHERE ss.start_date >= %s
            AND ss.end_date <= %s
            AND ss.docstatus = 1
            GROUP BY emp.department
            ORDER BY total DESC
        """, (self.from_date, self.to_date), as_dict=True)
        
        self.labor_cost_breakdown = json.dumps(labor_breakdown, default=str)


@frappe.whitelist()
def get_prime_cost_trend(outlet, periods=12):
    """Get prime cost trend for the past N periods."""
    reports = frappe.get_all(
        "Prime Cost Report",
        filters={"outlet": outlet, "status": ["!=", "Draft"]},
        fields=[
            "report_date", "from_date", "to_date",
            "total_sales", "food_cost_percentage",
            "labor_cost_percentage", "prime_cost_percentage"
        ],
        order_by="report_date desc",
        limit=periods
    )
    
    return list(reversed(reports))


@frappe.whitelist()
def compare_outlets(from_date, to_date):
    """Compare prime costs across all outlets."""
    outlets = frappe.get_all("Outlet", pluck="name")
    
    comparison = []
    for outlet in outlets:
        report = frappe.db.sql("""
            SELECT 
                outlet,
                SUM(total_sales) as sales,
                AVG(food_cost_percentage) as food_pct,
                AVG(labor_cost_percentage) as labor_pct,
                AVG(prime_cost_percentage) as prime_pct
            FROM `tabPrime Cost Report`
            WHERE outlet = %s
            AND from_date >= %s
            AND to_date <= %s
            AND status != 'Draft'
            GROUP BY outlet
        """, (outlet, from_date, to_date), as_dict=True)
        
        if report:
            comparison.append(report[0])
    
    return comparison


@frappe.whitelist()
def generate_weekly_report(outlet, week_ending_date):
    """Generate a weekly prime cost report."""
    week_end = getdate(week_ending_date)
    week_start = add_days(week_end, -6)
    
    # Check if report exists
    existing = frappe.db.exists(
        "Prime Cost Report",
        {
            "outlet": outlet,
            "from_date": week_start,
            "to_date": week_end
        }
    )
    
    if existing:
        report = frappe.get_doc("Prime Cost Report", existing)
    else:
        report = frappe.new_doc("Prime Cost Report")
        report.outlet = outlet
        report.period_type = "Weekly"
        report.from_date = week_start
        report.to_date = week_end
        report.report_date = week_end
    
    report.populate_from_data()
    report.save(ignore_permissions=True)
    
    return report.name
