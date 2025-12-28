"""
BookingZone API Module
=======================
Exposes REST API endpoints for OCR and Payment services.
"""

import frappe
from frappe import _
import json


# OCR API Endpoints
@frappe.whitelist(allow_guest=False)
def ocr_process_receipt(file_url):
    """
    Process a receipt image using PaddleOCR.
    
    Args:
        file_url: URL or path to the receipt image
        
    Returns:
        Extracted receipt fields
    """
    from bookingzone.services.ocr_service import process_receipt
    return process_receipt(file_url)


@frappe.whitelist(allow_guest=False)
def ocr_process_invoice(file_url):
    """
    Process an invoice image using PaddleOCR.
    
    Args:
        file_url: URL or path to the invoice image
        
    Returns:
        Extracted invoice fields
    """
    from bookingzone.services.ocr_service import process_invoice
    return process_invoice(file_url)


@frappe.whitelist(allow_guest=False)
def ocr_process_document(file_url, document_type="auto"):
    """
    Process a document image using PaddleOCR.
    
    Args:
        file_url: URL or path to the document image
        document_type: Type of document ("receipt", "invoice", or "auto")
        
    Returns:
        Extracted fields
    """
    from bookingzone.services.ocr_service import process_document
    return process_document(file_url, document_type)


@frappe.whitelist(allow_guest=False)
def ocr_status():
    """Get OCR service status."""
    from bookingzone.services.ocr_service import get_ocr_status
    return get_ocr_status()


# Payment API Endpoints
@frappe.whitelist(allow_guest=False)
def payment_create(amount, currency="USD", customer=None, sales_invoice=None, payment_method=None):
    """
    Create a new payment intent.
    
    Args:
        amount: Payment amount
        currency: Currency code
        customer: Customer name
        sales_invoice: Sales Invoice name
        payment_method: Preferred payment method
        
    Returns:
        Payment creation response
    """
    from bookingzone.services.payment_service import create_payment
    return create_payment(
        amount=float(amount),
        currency=currency,
        customer=customer,
        sales_invoice=sales_invoice,
        payment_method=payment_method
    )


@frappe.whitelist(allow_guest=False)
def payment_process(payment_id, payment_method_data):
    """
    Process a payment with payment method details.
    
    Args:
        payment_id: Payment Transaction name
        payment_method_data: Payment method details (JSON string)
        
    Returns:
        Payment processing result
    """
    from bookingzone.services.payment_service import process_payment
    
    if isinstance(payment_method_data, str):
        payment_method_data = json.loads(payment_method_data)
    
    return process_payment(payment_id, payment_method_data)


@frappe.whitelist(allow_guest=False)
def payment_refund(payment_id, amount=None, reason=None):
    """
    Refund a payment.
    
    Args:
        payment_id: Payment Transaction name
        amount: Refund amount (full refund if not specified)
        reason: Refund reason
        
    Returns:
        Refund result
    """
    from bookingzone.services.payment_service import refund_payment
    return refund_payment(
        payment_id,
        amount=float(amount) if amount else None,
        reason=reason
    )


@frappe.whitelist(allow_guest=False)
def payment_status(payment_id):
    """
    Get payment status.
    
    Args:
        payment_id: Payment Transaction name
        
    Returns:
        Payment status details
    """
    from bookingzone.services.payment_service import get_payment_status
    return get_payment_status(payment_id)


@frappe.whitelist(allow_guest=False)
def payment_gateways():
    """List configured payment gateways."""
    from bookingzone.services.payment_service import list_payment_gateways
    return list_payment_gateways()


@frappe.whitelist(allow_guest=False)
def payment_client_config():
    """Get client-side payment configuration."""
    from bookingzone.services.payment_service import get_client_config
    return get_client_config()


@frappe.whitelist(allow_guest=True)
def payment_webhook():
    """
    Handle payment webhooks from processors.
    This endpoint is called by payment processors to notify of events.
    """
    from bookingzone.doctype.payment_transaction.payment_transaction import process_webhook
    
    payload = frappe.request.get_data(as_text=True)
    signature = frappe.request.headers.get('Stripe-Signature') or \
                frappe.request.headers.get('X-Hyperswitch-Signature') or \
                frappe.request.headers.get('X-Webhook-Signature')
    
    return process_webhook(payload, signature)


# Dashboard API Endpoints
@frappe.whitelist(allow_guest=False)
def get_payment_dashboard_data(from_date=None, to_date=None):
    """
    Get payment dashboard data.
    
    Args:
        from_date: Start date filter
        to_date: End date filter
        
    Returns:
        Dashboard metrics and charts data
    """
    from frappe.utils import getdate, add_days, today
    
    if not from_date:
        from_date = add_days(today(), -30)
    if not to_date:
        to_date = today()
    
    # Total payments
    total_payments = frappe.db.sql("""
        SELECT 
            COUNT(*) as count,
            SUM(amount) as total_amount,
            SUM(CASE WHEN status = 'Succeeded' THEN amount ELSE 0 END) as successful_amount,
            SUM(CASE WHEN status = 'Failed' THEN amount ELSE 0 END) as failed_amount,
            SUM(refund_amount) as refunded_amount
        FROM `tabPayment Transaction`
        WHERE created_at BETWEEN %s AND %s
    """, (from_date, to_date), as_dict=True)[0]
    
    # Payments by processor
    by_processor = frappe.db.sql("""
        SELECT 
            selected_processor as processor,
            COUNT(*) as count,
            SUM(amount) as amount,
            SUM(CASE WHEN status = 'Succeeded' THEN 1 ELSE 0 END) as success_count
        FROM `tabPayment Transaction`
        WHERE created_at BETWEEN %s AND %s
        GROUP BY selected_processor
    """, (from_date, to_date), as_dict=True)
    
    # Payments by status
    by_status = frappe.db.sql("""
        SELECT 
            status,
            COUNT(*) as count,
            SUM(amount) as amount
        FROM `tabPayment Transaction`
        WHERE created_at BETWEEN %s AND %s
        GROUP BY status
    """, (from_date, to_date), as_dict=True)
    
    # Daily trend
    daily_trend = frappe.db.sql("""
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as count,
            SUM(amount) as amount
        FROM `tabPayment Transaction`
        WHERE created_at BETWEEN %s AND %s
        GROUP BY DATE(created_at)
        ORDER BY date
    """, (from_date, to_date), as_dict=True)
    
    return {
        "summary": total_payments,
        "by_processor": by_processor,
        "by_status": by_status,
        "daily_trend": daily_trend
    }


@frappe.whitelist(allow_guest=False)
def get_ocr_dashboard_data(from_date=None, to_date=None):
    """
    Get OCR processing dashboard data.
    
    Args:
        from_date: Start date filter
        to_date: End date filter
        
    Returns:
        OCR metrics and charts data
    """
    from frappe.utils import add_days, today
    
    if not from_date:
        from_date = add_days(today(), -30)
    if not to_date:
        to_date = today()
    
    # Total receipts processed
    total_receipts = frappe.db.sql("""
        SELECT 
            COUNT(*) as count,
            SUM(amount) as total_amount,
            AVG(ocr_confidence) as avg_confidence,
            SUM(CASE WHEN ocr_status = 'Completed' THEN 1 ELSE 0 END) as completed_count,
            SUM(CASE WHEN ocr_status = 'Failed' THEN 1 ELSE 0 END) as failed_count
        FROM `tabExpense Receipt`
        WHERE receipt_date BETWEEN %s AND %s
    """, (from_date, to_date), as_dict=True)[0]
    
    # By OCR engine
    by_engine = frappe.db.sql("""
        SELECT 
            ocr_engine as engine,
            COUNT(*) as count,
            AVG(ocr_confidence) as avg_confidence
        FROM `tabExpense Receipt`
        WHERE receipt_date BETWEEN %s AND %s AND ocr_engine IS NOT NULL
        GROUP BY ocr_engine
    """, (from_date, to_date), as_dict=True)
    
    # By status
    by_status = frappe.db.sql("""
        SELECT 
            status,
            COUNT(*) as count,
            SUM(amount) as amount
        FROM `tabExpense Receipt`
        WHERE receipt_date BETWEEN %s AND %s
        GROUP BY status
    """, (from_date, to_date), as_dict=True)
    
    # Daily trend
    daily_trend = frappe.db.sql("""
        SELECT 
            receipt_date as date,
            COUNT(*) as count,
            SUM(amount) as amount,
            AVG(ocr_confidence) as avg_confidence
        FROM `tabExpense Receipt`
        WHERE receipt_date BETWEEN %s AND %s
        GROUP BY receipt_date
        ORDER BY receipt_date
    """, (from_date, to_date), as_dict=True)
    
    return {
        "summary": total_receipts,
        "by_engine": by_engine,
        "by_status": by_status,
        "daily_trend": daily_trend
    }


# =============================================================================
# RESTAURANT DASHBOARD APIs
# =============================================================================

@frappe.whitelist(allow_guest=False)
def get_restaurant_dashboard_data(outlet=None, period='today'):
    """
    Get comprehensive restaurant dashboard data.
    
    Args:
        outlet: Outlet name filter
        period: Time period (today, yesterday, this_week, last_week, this_month, last_month)
    
    Returns:
        dict: Dashboard data including KPIs, trends, alerts
    """
    from frappe.utils import getdate, add_days
    
    from_date, to_date = _get_date_range(period)
    compare_from, compare_to = _get_comparison_date_range(period)
    
    # Get sales data
    sales_data = _get_sales_summary(outlet, from_date, to_date)
    compare_data = _get_sales_summary(outlet, compare_from, compare_to)
    
    # Calculate changes
    sales_change = _calculate_change(sales_data.get('net_sales', 0), compare_data.get('net_sales', 0))
    transactions_change = _calculate_change(sales_data.get('transactions', 0), compare_data.get('transactions', 0))
    
    # Get prime cost data
    prime_cost = _get_prime_cost_summary(outlet, from_date, to_date)
    
    # Get sales trend
    sales_trend = _get_sales_trend(outlet, 14)
    
    # Get category breakdown
    category_breakdown = _get_category_breakdown(outlet, from_date, to_date)
    
    # Get inventory alerts
    inventory_alerts = _get_inventory_alerts(outlet)
    
    # Get recent waste
    recent_waste = _get_recent_waste(outlet, 5)
    
    # Get top selling items
    top_items = _get_top_selling_items(outlet, from_date, to_date, 5)
    
    return {
        'net_sales': sales_data.get('net_sales', 0),
        'transactions': sales_data.get('transactions', 0),
        'avg_ticket': sales_data.get('avg_ticket', 0),
        'sales_change': sales_change,
        'transactions_change': transactions_change,
        'prime_cost_pct': prime_cost.get('prime_cost_pct', 0),
        'food_cost_pct': prime_cost.get('food_cost_pct', 0),
        'labor_cost_pct': prime_cost.get('labor_cost_pct', 0),
        'sales_trend': sales_trend,
        'category_breakdown': category_breakdown,
        'inventory_alerts': inventory_alerts,
        'recent_waste': recent_waste,
        'top_items': top_items
    }


def _get_date_range(period):
    """Get from_date and to_date for a period."""
    from frappe.utils import getdate, add_days
    today = getdate()
    
    if period == 'today':
        return today, today
    elif period == 'yesterday':
        yesterday = add_days(today, -1)
        return yesterday, yesterday
    elif period == 'this_week':
        start = add_days(today, -today.weekday())
        return start, today
    elif period == 'last_week':
        this_monday = add_days(today, -today.weekday())
        last_monday = add_days(this_monday, -7)
        last_sunday = add_days(this_monday, -1)
        return last_monday, last_sunday
    elif period == 'this_month':
        start = today.replace(day=1)
        return start, today
    elif period == 'last_month':
        first_of_month = today.replace(day=1)
        last_month_end = add_days(first_of_month, -1)
        last_month_start = last_month_end.replace(day=1)
        return last_month_start, last_month_end
    else:
        return today, today


def _get_comparison_date_range(period):
    """Get comparison date range (previous period)."""
    from frappe.utils import add_days
    from_date, to_date = _get_date_range(period)
    days = (to_date - from_date).days + 1
    compare_to = add_days(from_date, -1)
    compare_from = add_days(compare_to, -(days - 1))
    return compare_from, compare_to


def _calculate_change(current, previous):
    """Calculate percentage change."""
    if not previous or previous == 0:
        return 0
    return ((current - previous) / previous) * 100


def _get_sales_summary(outlet, from_date, to_date):
    """Get sales summary."""
    data = frappe.db.sql("""
        SELECT 
            SUM(net_sales) as net_sales,
            SUM(total_transactions) as transactions,
            AVG(avg_ticket_size) as avg_ticket
        FROM `tabDaily Sales Summary`
        WHERE summary_date BETWEEN %s AND %s
        {outlet_filter}
    """.format(
        outlet_filter=f"AND outlet = '{outlet}'" if outlet else ""
    ), (from_date, to_date), as_dict=True)
    
    if data and data[0].net_sales:
        return data[0]
    return {'net_sales': 0, 'transactions': 0, 'avg_ticket': 0}


def _get_prime_cost_summary(outlet, from_date, to_date):
    """Get prime cost metrics."""
    data = frappe.db.sql("""
        SELECT 
            AVG(prime_cost_percentage) as prime_cost_pct,
            AVG(food_cost_percentage) as food_cost_pct,
            AVG(labor_cost_percentage) as labor_cost_pct
        FROM `tabPrime Cost Report`
        WHERE from_date >= %s AND to_date <= %s
        AND status != 'Draft'
        {outlet_filter}
    """.format(
        outlet_filter=f"AND outlet = '{outlet}'" if outlet else ""
    ), (from_date, to_date), as_dict=True)
    
    if data and data[0].prime_cost_pct:
        return data[0]
    return {'prime_cost_pct': 0, 'food_cost_pct': 0, 'labor_cost_pct': 0}


def _get_sales_trend(outlet, days):
    """Get daily sales trend."""
    from frappe.utils import getdate, add_days
    from_date = add_days(getdate(), -days)
    
    data = frappe.db.sql("""
        SELECT 
            summary_date as date,
            net_sales
        FROM `tabDaily Sales Summary`
        WHERE summary_date >= %s
        {outlet_filter}
        ORDER BY summary_date ASC
    """.format(
        outlet_filter=f"AND outlet = '{outlet}'" if outlet else ""
    ), (from_date,), as_dict=True)
    
    return data


def _get_category_breakdown(outlet, from_date, to_date):
    """Get sales breakdown by category."""
    data = frappe.db.sql("""
        SELECT 
            SUM(food_sales) as Food,
            SUM(beverage_sales) as Beverage,
            SUM(merchandise_sales) as Merchandise,
            SUM(entertainment_sales) as Entertainment,
            SUM(service_sales) as Services,
            SUM(other_sales) as Other
        FROM `tabDaily Sales Summary`
        WHERE summary_date BETWEEN %s AND %s
        {outlet_filter}
    """.format(
        outlet_filter=f"AND outlet = '{outlet}'" if outlet else ""
    ), (from_date, to_date), as_dict=True)
    
    if data and data[0]:
        return {k: v for k, v in data[0].items() if v and v > 0}
    return {}


def _get_inventory_alerts(outlet, limit=10):
    """Get inventory items below par level."""
    filters = {'is_active': 1, 'stock_status': ['in', ['Critical', 'Low']]}
    if outlet:
        filters['outlet'] = outlet
    
    try:
        alerts = frappe.get_all(
            'Par Level',
            filters=filters,
            fields=['item_code', 'item_name', 'current_stock', 'par_level', 'stock_status'],
            order_by='stock_status desc, current_stock asc',
            limit=limit
        )
        return alerts
    except:
        return []


def _get_recent_waste(outlet, limit=5):
    """Get recent waste logs."""
    filters = {'docstatus': ['in', [0, 1]]}
    if outlet:
        filters['outlet'] = outlet
    
    try:
        waste = frappe.get_all(
            'Waste Log',
            filters=filters,
            fields=['item_code', 'item_name', 'quantity', 'waste_value', 'waste_reason', 'waste_date'],
            order_by='waste_date desc',
            limit=limit
        )
        return waste
    except:
        return []


def _get_top_selling_items(outlet, from_date, to_date, limit=5):
    """Get top selling items."""
    try:
        data = frappe.db.sql("""
            SELECT 
                poi.item_code,
                poi.item_name,
                SUM(poi.qty) as qty,
                SUM(poi.amount) as revenue
            FROM `tabPOS Order Item` poi
            JOIN `tabPOS Order` po ON poi.parent = po.name
            WHERE DATE(po.creation) BETWEEN %s AND %s
            AND po.docstatus = 1
            {outlet_filter}
            GROUP BY poi.item_code, poi.item_name
            ORDER BY revenue DESC
            LIMIT %s
        """.format(
            outlet_filter=f"AND po.outlet = '{outlet}'" if outlet else ""
        ), (from_date, to_date, limit), as_dict=True)
        return data
    except:
        return []


# =============================================================================
# BANK RECONCILIATION APIs
# =============================================================================

@frappe.whitelist(allow_guest=False)
def apply_bank_rules(bank_transaction):
    """Apply bank rules to a transaction."""
    from bookingzone.doctype.bank_rule.bank_rule import apply_rules_to_transaction
    return apply_rules_to_transaction(bank_transaction)


@frappe.whitelist(allow_guest=False)
def bulk_categorize_transactions(bank_account=None, from_date=None, to_date=None):
    """Apply bank rules to multiple transactions."""
    from bookingzone.doctype.bank_rule.bank_rule import bulk_apply_rules
    return bulk_apply_rules(bank_account, from_date, to_date)


# =============================================================================
# INVENTORY APIs
# =============================================================================

@frappe.whitelist(allow_guest=False)
def get_par_level_dashboard(outlet=None, warehouse=None):
    """Get par level dashboard data."""
    from bookingzone.doctype.par_level.par_level import get_par_level_dashboard as get_dashboard
    return get_dashboard(outlet, warehouse)


@frappe.whitelist(allow_guest=False)
def log_waste_quick(item_code, quantity, waste_reason, outlet=None):
    """Quick API to log waste."""
    from bookingzone.doctype.waste_log.waste_log import quick_log_waste
    return quick_log_waste(item_code, quantity, waste_reason, outlet)


# =============================================================================
# RECIPE APIs
# =============================================================================

@frappe.whitelist(allow_guest=False)
def get_recipe_cost(recipe_name):
    """Get detailed recipe cost breakdown."""
    from bookingzone.doctype.recipe.recipe import get_recipe_cost_breakdown
    return get_recipe_cost_breakdown(recipe_name)


@frappe.whitelist(allow_guest=False)
def update_all_recipe_costs():
    """Recalculate costs for all active recipes."""
    from bookingzone.doctype.recipe.recipe import bulk_update_recipe_costs
    return bulk_update_recipe_costs()


# =============================================================================
# PRIME COST APIs
# =============================================================================

@frappe.whitelist(allow_guest=False)
def get_prime_cost_trend(outlet, periods=12):
    """Get prime cost trend."""
    from bookingzone.doctype.prime_cost_report.prime_cost_report import get_prime_cost_trend as get_trend
    return get_trend(outlet, periods)


@frappe.whitelist(allow_guest=False)
def generate_prime_cost_report(outlet, week_ending_date):
    """Generate weekly prime cost report."""
    from bookingzone.doctype.prime_cost_report.prime_cost_report import generate_weekly_report
    return generate_weekly_report(outlet, week_ending_date)
