/**
 * BookingZone Payment Form
 * ========================
 * Frontend payment processing with Hyperswitch and multi-processor support.
 * Supports Stripe, PayPal, Square, and other payment methods.
 */

class BookingZonePayment {
    constructor(options = {}) {
        this.options = {
            container: '#payment-form',
            amount: 0,
            currency: 'USD',
            customer: null,
            salesInvoice: null,
            onSuccess: null,
            onError: null,
            ...options
        };
        
        this.paymentId = null;
        this.clientSecret = null;
        this.selectedProcessor = null;
        this.hyperswitchLoaded = false;
        this.stripeLoaded = false;
        
        this.init();
    }
    
    async init() {
        // Load payment configuration
        await this.loadConfig();
        
        // Initialize payment processors
        await this.initializeProcessors();
        
        // Render payment form
        this.render();
    }
    
    async loadConfig() {
        try {
            const response = await frappe.call({
                method: 'bookingzone.services.payment_service.get_client_config'
            });
            
            this.config = response.message || {};
        } catch (error) {
            console.error('Failed to load payment config:', error);
            this.config = {};
        }
    }
    
    async initializeProcessors() {
        // Load Hyperswitch SDK
        if (this.config.hyperswitch_publishable_key) {
            await this.loadScript('https://js.hyperswitch.io/v1/hyperswitch.js');
            this.hyperswitch = window.Hyperswitch(this.config.hyperswitch_publishable_key);
            this.hyperswitchLoaded = true;
        }
        
        // Load Stripe as fallback
        if (this.config.stripe_publishable_key) {
            await this.loadScript('https://js.stripe.com/v3/');
            this.stripe = window.Stripe(this.config.stripe_publishable_key);
            this.stripeLoaded = true;
        }
    }
    
    loadScript(src) {
        return new Promise((resolve, reject) => {
            if (document.querySelector(`script[src="${src}"]`)) {
                resolve();
                return;
            }
            
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }
    
    render() {
        const container = document.querySelector(this.options.container);
        if (!container) return;
        
        container.innerHTML = `
            <div class="bookingzone-payment">
                <div class="payment-header">
                    <h3>Payment Details</h3>
                    <div class="payment-amount">
                        <span class="currency">${this.options.currency}</span>
                        <span class="amount">${this.formatAmount(this.options.amount)}</span>
                    </div>
                </div>
                
                <div class="payment-methods">
                    <div class="method-tabs">
                        <button class="method-tab active" data-method="card">
                            <i class="fa fa-credit-card"></i> Card
                        </button>
                        <button class="method-tab" data-method="bank">
                            <i class="fa fa-university"></i> Bank
                        </button>
                        <button class="method-tab" data-method="paypal">
                            <i class="fa fa-paypal"></i> PayPal
                        </button>
                    </div>
                    
                    <div class="method-content">
                        <div class="method-panel active" id="card-panel">
                            <div id="card-element"></div>
                            <div id="card-errors" class="error-message"></div>
                        </div>
                        
                        <div class="method-panel" id="bank-panel">
                            <div class="form-group">
                                <label>Account Holder Name</label>
                                <input type="text" id="account-holder" class="form-control" />
                            </div>
                            <div class="form-group">
                                <label>Routing Number</label>
                                <input type="text" id="routing-number" class="form-control" maxlength="9" />
                            </div>
                            <div class="form-group">
                                <label>Account Number</label>
                                <input type="text" id="account-number" class="form-control" />
                            </div>
                        </div>
                        
                        <div class="method-panel" id="paypal-panel">
                            <div id="paypal-button"></div>
                        </div>
                    </div>
                </div>
                
                <div class="payment-actions">
                    <button id="pay-button" class="btn btn-primary btn-lg">
                        Pay ${this.options.currency} ${this.formatAmount(this.options.amount)}
                    </button>
                </div>
                
                <div class="payment-security">
                    <i class="fa fa-lock"></i>
                    <span>Secured by Hyperswitch • PCI DSS Compliant</span>
                </div>
            </div>
        `;
        
        this.attachStyles();
        this.attachEventListeners();
        this.mountCardElement();
    }
    
    attachStyles() {
        if (document.getElementById('bookingzone-payment-styles')) return;
        
        const styles = document.createElement('style');
        styles.id = 'bookingzone-payment-styles';
        styles.textContent = `
            .bookingzone-payment {
                max-width: 500px;
                margin: 0 auto;
                padding: 24px;
                background: #fff;
                border-radius: 12px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            }
            
            .payment-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 24px;
                padding-bottom: 16px;
                border-bottom: 1px solid #eee;
            }
            
            .payment-header h3 {
                margin: 0;
                font-size: 18px;
                font-weight: 600;
            }
            
            .payment-amount {
                font-size: 24px;
                font-weight: 700;
                color: #2563eb;
            }
            
            .payment-amount .currency {
                font-size: 14px;
                margin-right: 4px;
            }
            
            .method-tabs {
                display: flex;
                gap: 8px;
                margin-bottom: 20px;
            }
            
            .method-tab {
                flex: 1;
                padding: 12px;
                border: 2px solid #e5e7eb;
                border-radius: 8px;
                background: #fff;
                cursor: pointer;
                transition: all 0.2s;
                font-size: 14px;
            }
            
            .method-tab:hover {
                border-color: #2563eb;
            }
            
            .method-tab.active {
                border-color: #2563eb;
                background: #eff6ff;
                color: #2563eb;
            }
            
            .method-tab i {
                margin-right: 6px;
            }
            
            .method-panel {
                display: none;
            }
            
            .method-panel.active {
                display: block;
            }
            
            #card-element {
                padding: 16px;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                background: #f9fafb;
            }
            
            .form-group {
                margin-bottom: 16px;
            }
            
            .form-group label {
                display: block;
                margin-bottom: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            
            .form-control {
                width: 100%;
                padding: 12px;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                font-size: 16px;
            }
            
            .form-control:focus {
                outline: none;
                border-color: #2563eb;
                box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
            }
            
            .error-message {
                color: #dc2626;
                font-size: 14px;
                margin-top: 8px;
            }
            
            .payment-actions {
                margin-top: 24px;
            }
            
            #pay-button {
                width: 100%;
                padding: 16px;
                font-size: 16px;
                font-weight: 600;
                border-radius: 8px;
                background: #2563eb;
                color: #fff;
                border: none;
                cursor: pointer;
                transition: background 0.2s;
            }
            
            #pay-button:hover {
                background: #1d4ed8;
            }
            
            #pay-button:disabled {
                background: #9ca3af;
                cursor: not-allowed;
            }
            
            .payment-security {
                margin-top: 16px;
                text-align: center;
                font-size: 12px;
                color: #6b7280;
            }
            
            .payment-security i {
                margin-right: 4px;
                color: #10b981;
            }
            
            .processing {
                position: relative;
            }
            
            .processing::after {
                content: '';
                position: absolute;
                top: 50%;
                left: 50%;
                width: 20px;
                height: 20px;
                margin: -10px 0 0 -10px;
                border: 2px solid #fff;
                border-top-color: transparent;
                border-radius: 50%;
                animation: spin 0.8s linear infinite;
            }
            
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
        `;
        document.head.appendChild(styles);
    }
    
    attachEventListeners() {
        // Method tab switching
        document.querySelectorAll('.method-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.method-tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.method-panel').forEach(p => p.classList.remove('active'));
                
                tab.classList.add('active');
                const method = tab.dataset.method;
                document.getElementById(`${method}-panel`).classList.add('active');
            });
        });
        
        // Pay button
        document.getElementById('pay-button').addEventListener('click', () => this.processPayment());
    }
    
    async mountCardElement() {
        if (this.hyperswitchLoaded) {
            const elements = this.hyperswitch.elements();
            this.cardElement = elements.create('card', {
                style: {
                    base: {
                        fontSize: '16px',
                        color: '#1f2937',
                        '::placeholder': { color: '#9ca3af' }
                    }
                }
            });
            this.cardElement.mount('#card-element');
            
            this.cardElement.on('change', (event) => {
                const errorElement = document.getElementById('card-errors');
                errorElement.textContent = event.error ? event.error.message : '';
            });
        } else if (this.stripeLoaded) {
            const elements = this.stripe.elements();
            this.cardElement = elements.create('card', {
                style: {
                    base: {
                        fontSize: '16px',
                        color: '#1f2937',
                        '::placeholder': { color: '#9ca3af' }
                    }
                }
            });
            this.cardElement.mount('#card-element');
            
            this.cardElement.on('change', (event) => {
                const errorElement = document.getElementById('card-errors');
                errorElement.textContent = event.error ? event.error.message : '';
            });
        }
    }
    
    async processPayment() {
        const payButton = document.getElementById('pay-button');
        payButton.disabled = true;
        payButton.classList.add('processing');
        payButton.textContent = 'Processing...';
        
        try {
            // Create payment on server
            const createResponse = await frappe.call({
                method: 'bookingzone.services.payment_service.create_payment',
                args: {
                    amount: this.options.amount,
                    currency: this.options.currency,
                    customer: this.options.customer,
                    sales_invoice: this.options.salesInvoice
                }
            });
            
            if (!createResponse.message.success) {
                throw new Error(createResponse.message.error || 'Failed to create payment');
            }
            
            this.paymentId = createResponse.message.payment_id;
            this.clientSecret = createResponse.message.client_secret;
            
            // Process with Hyperswitch or Stripe
            let result;
            
            if (this.hyperswitchLoaded && this.clientSecret) {
                result = await this.hyperswitch.confirmPayment({
                    elements: this.cardElement,
                    clientSecret: this.clientSecret,
                    confirmParams: {
                        return_url: window.location.href
                    }
                });
            } else if (this.stripeLoaded) {
                // Get payment method data
                const { paymentMethod, error } = await this.stripe.createPaymentMethod({
                    type: 'card',
                    card: this.cardElement
                });
                
                if (error) {
                    throw new Error(error.message);
                }
                
                // Process on server
                const processResponse = await frappe.call({
                    method: 'bookingzone.services.payment_service.process_payment',
                    args: {
                        payment_id: this.paymentId,
                        payment_method_data: JSON.stringify({
                            type: 'card',
                            payment_method_id: paymentMethod.id
                        })
                    }
                });
                
                result = processResponse.message;
            }
            
            if (result.success || result.status === 'Succeeded') {
                this.handleSuccess(result);
            } else {
                throw new Error(result.error || 'Payment failed');
            }
            
        } catch (error) {
            this.handleError(error);
        } finally {
            payButton.disabled = false;
            payButton.classList.remove('processing');
            payButton.textContent = `Pay ${this.options.currency} ${this.formatAmount(this.options.amount)}`;
        }
    }
    
    handleSuccess(result) {
        const container = document.querySelector(this.options.container);
        container.innerHTML = `
            <div class="payment-success">
                <div class="success-icon">
                    <i class="fa fa-check-circle" style="font-size: 64px; color: #10b981;"></i>
                </div>
                <h2>Payment Successful!</h2>
                <p>Transaction ID: ${result.transaction_id || this.paymentId}</p>
                <p>Amount: ${this.options.currency} ${this.formatAmount(this.options.amount)}</p>
            </div>
        `;
        
        if (this.options.onSuccess) {
            this.options.onSuccess(result);
        }
        
        frappe.show_alert({
            message: 'Payment processed successfully!',
            indicator: 'green'
        });
    }
    
    handleError(error) {
        document.getElementById('card-errors').textContent = error.message;
        
        if (this.options.onError) {
            this.options.onError(error);
        }
        
        frappe.show_alert({
            message: error.message || 'Payment failed',
            indicator: 'red'
        });
    }
    
    formatAmount(amount) {
        return parseFloat(amount).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    }
}

// Export for use in Frappe
window.BookingZonePayment = BookingZonePayment;

// Frappe integration
frappe.provide('bookingzone.payment');

bookingzone.payment.create = function(options) {
    return new BookingZonePayment(options);
};

bookingzone.payment.payInvoice = async function(salesInvoice) {
    const invoice = await frappe.db.get_doc('Sales Invoice', salesInvoice);
    
    frappe.prompt({
        fieldname: 'payment_container',
        fieldtype: 'HTML',
        options: '<div id="invoice-payment-form"></div>'
    }, () => {}, 'Pay Invoice', 'Pay');
    
    setTimeout(() => {
        new BookingZonePayment({
            container: '#invoice-payment-form',
            amount: invoice.outstanding_amount,
            currency: invoice.currency,
            customer: invoice.customer,
            salesInvoice: salesInvoice,
            onSuccess: () => {
                frappe.set_route('Form', 'Sales Invoice', salesInvoice);
                location.reload();
            }
        });
    }, 100);
};
