# BookingZone Super ERP Enhancement

A comprehensive Frappe app that extends BookingZone ERP with QuickBooks Online and Restaurant365 features, including multi-gateway payments, open-source OCR, and restaurant management capabilities.

## Features

### 🍽️ Restaurant Management (R365-inspired)
- **Recipe Costing**: Track ingredient costs, calculate food cost percentages
- **Inventory Count**: Mobile-optimized inventory counting with barcode scanning
- **Waste Tracking**: Log and analyze food waste by reason
- **Par Level Management**: Automatic reorder alerts based on par levels
- **Prime Cost Dashboard**: Real-time food + labor cost visibility
- **Daily Sales Summary**: Automated sales aggregation from POS

### 💳 Multi-Gateway Payments (Hyperswitch)
- **8 Payment Processors**: Stripe, PayPal, Square, Adyen, Authorize.Net, Braintree, GoCardless, Datacap
- **Intelligent Routing**: Route payments based on amount, type, and location
- **Split Payments**: Support for multiple payment methods per transaction
- **POS Integration**: Seamless integration with existing BookingZone POS

### 📸 Open-Source OCR (PaddleOCR)
- **Receipt Processing**: Automatic extraction of vendor, amount, date
- **Invoice Processing**: Extract line items, totals, tax information
- **97%+ Accuracy**: Using PaddleOCR PP-OCRv4 (latest model)
- **$0/month**: No cloud API costs

### 🏦 Bank Reconciliation
- **Auto-Categorization**: Bank rules for automatic transaction matching
- **Smart Matching**: Suggest matches based on amount and description
- **Bulk Processing**: Process multiple transactions at once

### 📊 Dashboards
- **Restaurant Dashboard**: KPIs, sales trends, inventory alerts
- **Prime Cost Dashboard**: Food cost, labor cost, trend analysis
- **Payment Dashboard**: Transaction volumes, processor performance

## Installation

### Prerequisites
- Frappe Bench v15+
- ERPNext v15+
- Python 3.10+

### Install the App

```bash
# Get the app
bench get-app https://github.com/bookingzone/bookingzone-erp

# Install on your site
bench --site your-site.local install-app bookingzone

# Run migrations
bench --site your-site.local migrate
```

### Install Dependencies

```bash
# PaddleOCR for receipt/invoice processing
pip install paddlepaddle paddleocr

# Payment processing
pip install httpx
```

### Configure Payment Gateways

1. Go to **Payment Gateway Configuration**
2. Enable desired gateways (Stripe, PayPal, Square, etc.)
3. Enter API credentials for each gateway
4. Set up routing rules in **Payment Routing Rule**

### Configure Hyperswitch (Optional)

For multi-gateway orchestration:

1. Sign up at [hyperswitch.io](https://hyperswitch.io)
2. Get your API key
3. Add to site_config.json:
   ```json
   {
     "hyperswitch_api_key": "your-api-key",
     "hyperswitch_base_url": "https://api.hyperswitch.io"
   }
   ```

## DocTypes

### Restaurant Module
| DocType | Description |
|---------|-------------|
| Recipe | Recipe with ingredients and costing |
| Recipe Ingredient | Child table for recipe ingredients |
| Inventory Count | Physical inventory count document |
| Inventory Count Item | Child table for count items |
| Waste Log | Food waste tracking |
| Par Level | Inventory par level settings |
| Prime Cost Report | Weekly prime cost analysis |
| Daily Sales Summary | Aggregated daily sales data |

### Payment Module
| DocType | Description |
|---------|-------------|
| Payment Gateway Configuration | Gateway settings and credentials |
| Payment Transaction | Payment records with processor details |
| Payment Routing Rule | Rules for routing payments |

### Expense Module
| DocType | Description |
|---------|-------------|
| Expense Receipt | OCR-enabled receipt capture |
| Bank Rule | Auto-categorization rules |

## Pages

| Page | Description |
|------|-------------|
| Restaurant Dashboard | Main operations dashboard |
| Prime Cost Dashboard | Food + labor cost analysis |
| Inventory Count Entry | Mobile-optimized counting |
| Recipe Manager | Visual recipe management |
| Bank Reconciliation | Transaction matching interface |

## API Endpoints

### OCR APIs
```python
# Process a receipt
frappe.call('bookingzone.api.ocr_process_receipt', file_url='/path/to/receipt.jpg')

# Process an invoice
frappe.call('bookingzone.api.ocr_process_invoice', file_url='/path/to/invoice.pdf')
```

### Payment APIs
```python
# Create a payment
frappe.call('bookingzone.api.payment_create', 
    amount=10000,  # in cents
    currency='USD',
    customer='CUST-001'
)

# Process POS payment with split
frappe.call('bookingzone.services.pos_payment_integration.process_pos_payment',
    pos_order='POS-ORD-001',
    payments=[
        {'method': 'card', 'amount': 5000},
        {'method': 'gift_card', 'card_number': 'GC-001', 'amount': 2500},
        {'method': 'cash', 'amount': 2500}
    ]
)
```

### Restaurant APIs
```python
# Get dashboard data
frappe.call('bookingzone.api.get_restaurant_dashboard_data',
    outlet='Main Restaurant',
    period='this_week'
)

# Generate prime cost report
frappe.call('bookingzone.api.generate_prime_cost_report',
    outlet='Main Restaurant',
    week_ending_date='2024-12-22'
)
```

## Scheduled Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| generate_daily_summaries | Daily | Create daily sales summaries |
| update_par_level_status | Daily | Update stock status |
| sync_payment_statuses | Every 15 min | Sync payment statuses |
| process_pending_ocr | Every 5 min | Process OCR queue |
| generate_prime_cost_reports | Weekly | Create prime cost reports |
| sync_sage_erp | Daily 3 AM | Sync to Sage ERP |

## Configuration

### Site Config Options

```json
{
  "hyperswitch_api_key": "your-hyperswitch-key",
  "hyperswitch_base_url": "https://api.hyperswitch.io",
  "plaid_client_id": "your-plaid-client-id",
  "plaid_secret": "your-plaid-secret",
  "sage_api_key": "your-sage-api-key"
}
```

## Cost Savings

| Category | Traditional | BookingZone | Annual Savings |
|----------|-------------|-------------|----------------|
| OCR | $1,500/mo (Google) | $0 (PaddleOCR) | $18,000 |
| Payments (at $500K/mo) | $16,000/mo | $12,500/mo | $42,000 |
| **Total** | | | **$60,000/year** |

## License

MIT License

## Support

For support, please contact support@bookingzone.com or visit [BookingZone Help](https://help.bookingzone.com).
