/**
 * Bank Reconciliation Page
 * =========================
 * Modern bank reconciliation interface with auto-categorization rules.
 */

frappe.pages['bank-reconciliation'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Bank Reconciliation',
        single_column: true
    });

    // Add bank account selector
    page.add_field({
        fieldname: 'bank_account',
        label: __('Bank Account'),
        fieldtype: 'Link',
        options: 'Bank Account',
        reqd: 1,
        change: function() {
            page.reconciler.load_transactions();
        }
    });

    // Add date range
    page.add_field({
        fieldname: 'from_date',
        label: __('From'),
        fieldtype: 'Date',
        default: frappe.datetime.add_days(frappe.datetime.get_today(), -30),
        change: function() {
            page.reconciler.load_transactions();
        }
    });

    page.add_field({
        fieldname: 'to_date',
        label: __('To'),
        fieldtype: 'Date',
        default: frappe.datetime.get_today(),
        change: function() {
            page.reconciler.load_transactions();
        }
    });

    // Add auto-categorize button
    page.add_button(__('Auto-Categorize'), function() {
        page.reconciler.auto_categorize();
    }, 'btn-primary');

    // Add manage rules button
    page.add_button(__('Manage Rules'), function() {
        frappe.set_route('List', 'Bank Rule');
    });

    // Initialize reconciler
    page.reconciler = new BankReconciler(page);
};

class BankReconciler {
    constructor(page) {
        this.page = page;
        this.wrapper = $(page.body);
        this.transactions = [];
        this.init();
    }

    init() {
        this.render_skeleton();
    }

    render_skeleton() {
        this.wrapper.html(`
            <div class="bank-reconciler">
                <!-- Summary Bar -->
                <div class="summary-bar bg-light p-3 mb-4 rounded">
                    <div class="row text-center">
                        <div class="col-md-3 col-6 mb-2">
                            <h5 class="mb-0 text-success" id="total-deposits">$0</h5>
                            <small class="text-muted">Deposits</small>
                        </div>
                        <div class="col-md-3 col-6 mb-2">
                            <h5 class="mb-0 text-danger" id="total-withdrawals">$0</h5>
                            <small class="text-muted">Withdrawals</small>
                        </div>
                        <div class="col-md-3 col-6 mb-2">
                            <h5 class="mb-0 text-warning" id="unreconciled-count">0</h5>
                            <small class="text-muted">Unreconciled</small>
                        </div>
                        <div class="col-md-3 col-6 mb-2">
                            <h5 class="mb-0 text-info" id="auto-matched">0</h5>
                            <small class="text-muted">Auto-Matched</small>
                        </div>
                    </div>
                </div>

                <!-- Filter Tabs -->
                <ul class="nav nav-tabs mb-3" id="transaction-tabs">
                    <li class="nav-item">
                        <a class="nav-link active" data-filter="all" href="#">All</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" data-filter="unreconciled" href="#">Unreconciled</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" data-filter="reconciled" href="#">Reconciled</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" data-filter="deposits" href="#">Deposits</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" data-filter="withdrawals" href="#">Withdrawals</a>
                    </li>
                </ul>

                <!-- Transactions List -->
                <div class="transactions-list" id="transactions-list">
                    <div class="text-center py-5 text-muted">
                        <i class="fa fa-university fa-3x mb-3"></i>
                        <p>Select a bank account to view transactions</p>
                    </div>
                </div>

                <!-- Match Modal -->
                <div class="modal fade" id="match-modal" tabindex="-1">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">Match Transaction</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="transaction-details mb-4 p-3 bg-light rounded">
                                    <div class="row">
                                        <div class="col-md-6">
                                            <strong>Date:</strong> <span id="match-date"></span><br>
                                            <strong>Description:</strong> <span id="match-description"></span>
                                        </div>
                                        <div class="col-md-6 text-end">
                                            <strong>Amount:</strong> <span id="match-amount" class="h4"></span>
                                        </div>
                                    </div>
                                </div>

                                <ul class="nav nav-tabs mb-3">
                                    <li class="nav-item">
                                        <a class="nav-link active" data-bs-toggle="tab" href="#match-existing">Match Existing</a>
                                    </li>
                                    <li class="nav-item">
                                        <a class="nav-link" data-bs-toggle="tab" href="#create-new">Create New</a>
                                    </li>
                                    <li class="nav-item">
                                        <a class="nav-link" data-bs-toggle="tab" href="#create-rule">Create Rule</a>
                                    </li>
                                </ul>

                                <div class="tab-content">
                                    <div class="tab-pane fade show active" id="match-existing">
                                        <div class="mb-3">
                                            <input type="text" class="form-control" id="match-search" 
                                                   placeholder="Search invoices, payments, expenses...">
                                        </div>
                                        <div id="match-suggestions" class="list-group">
                                            <!-- Suggestions will be loaded here -->
                                        </div>
                                    </div>
                                    <div class="tab-pane fade" id="create-new">
                                        <div class="row">
                                            <div class="col-md-6 mb-3">
                                                <label class="form-label">Document Type</label>
                                                <select class="form-select" id="new-doc-type">
                                                    <option value="Payment Entry">Payment Entry</option>
                                                    <option value="Journal Entry">Journal Entry</option>
                                                    <option value="Expense Receipt">Expense Receipt</option>
                                                </select>
                                            </div>
                                            <div class="col-md-6 mb-3">
                                                <label class="form-label">Party Type</label>
                                                <select class="form-select" id="new-party-type">
                                                    <option value="">Select...</option>
                                                    <option value="Customer">Customer</option>
                                                    <option value="Supplier">Supplier</option>
                                                    <option value="Employee">Employee</option>
                                                </select>
                                            </div>
                                        </div>
                                        <div class="mb-3">
                                            <label class="form-label">Party</label>
                                            <input type="text" class="form-control" id="new-party">
                                        </div>
                                        <div class="mb-3">
                                            <label class="form-label">Account</label>
                                            <input type="text" class="form-control" id="new-account">
                                        </div>
                                    </div>
                                    <div class="tab-pane fade" id="create-rule">
                                        <div class="mb-3">
                                            <label class="form-label">Rule Name</label>
                                            <input type="text" class="form-control" id="rule-name">
                                        </div>
                                        <div class="mb-3">
                                            <label class="form-label">Match Pattern</label>
                                            <input type="text" class="form-control" id="rule-pattern" 
                                                   placeholder="Text to match in description">
                                        </div>
                                        <div class="mb-3">
                                            <label class="form-label">Assign to Account</label>
                                            <input type="text" class="form-control" id="rule-account">
                                        </div>
                                        <div class="form-check mb-3">
                                            <input type="checkbox" class="form-check-input" id="rule-auto-reconcile">
                                            <label class="form-check-label">Auto-reconcile matching transactions</label>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="button" class="btn btn-primary" id="match-save">Save Match</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <style>
                .bank-reconciler .transaction-row {
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    padding: 12px 16px;
                    margin-bottom: 8px;
                    cursor: pointer;
                    transition: all 0.2s;
                }
                .bank-reconciler .transaction-row:hover {
                    border-color: #5e64ff;
                    background-color: #f8f9fa;
                }
                .bank-reconciler .transaction-row.reconciled {
                    background-color: #d4edda;
                    border-color: #28a745;
                }
                .bank-reconciler .transaction-row.suggested {
                    background-color: #fff3cd;
                    border-color: #ffc107;
                }
                .bank-reconciler .transaction-row .amount {
                    font-size: 1.1rem;
                    font-weight: 600;
                }
                .bank-reconciler .transaction-row .amount.deposit {
                    color: #28a745;
                }
                .bank-reconciler .transaction-row .amount.withdrawal {
                    color: #dc3545;
                }
                .bank-reconciler .match-suggestion {
                    cursor: pointer;
                }
                .bank-reconciler .match-suggestion:hover {
                    background-color: #f8f9fa;
                }
            </style>
        `);

        // Setup tab clicks
        this.wrapper.find('#transaction-tabs a').on('click', (e) => {
            e.preventDefault();
            this.wrapper.find('#transaction-tabs a').removeClass('active');
            $(e.target).addClass('active');
            this.currentFilter = $(e.target).data('filter');
            this.render_transactions();
        });

        this.currentFilter = 'all';
    }

    load_transactions() {
        const bankAccount = this.page.fields_dict.bank_account.get_value();
        const fromDate = this.page.fields_dict.from_date.get_value();
        const toDate = this.page.fields_dict.to_date.get_value();

        if (!bankAccount) return;

        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Bank Transaction',
                filters: {
                    bank_account: bankAccount,
                    date: ['between', [fromDate, toDate]]
                },
                fields: [
                    'name', 'date', 'description', 'deposit', 'withdrawal',
                    'unallocated_amount', 'status', 'party_type', 'party',
                    'reference_number'
                ],
                order_by: 'date desc',
                limit_page_length: 0
            },
            callback: (r) => {
                if (r.message) {
                    this.transactions = r.message;
                    this.render_transactions();
                    this.update_summary();
                }
            }
        });
    }

    render_transactions() {
        const container = $('#transactions-list');
        let filtered = this.transactions;

        // Apply filter
        switch (this.currentFilter) {
            case 'unreconciled':
                filtered = filtered.filter(t => t.status !== 'Reconciled');
                break;
            case 'reconciled':
                filtered = filtered.filter(t => t.status === 'Reconciled');
                break;
            case 'deposits':
                filtered = filtered.filter(t => t.deposit > 0);
                break;
            case 'withdrawals':
                filtered = filtered.filter(t => t.withdrawal > 0);
                break;
        }

        if (!filtered.length) {
            container.html(`
                <div class="text-center py-5 text-muted">
                    <i class="fa fa-check-circle fa-3x mb-3"></i>
                    <p>No transactions found</p>
                </div>
            `);
            return;
        }

        let html = '';
        filtered.forEach(txn => {
            const isDeposit = txn.deposit > 0;
            const amount = isDeposit ? txn.deposit : txn.withdrawal;
            const isReconciled = txn.status === 'Reconciled';
            const hasSuggestion = txn.unallocated_amount === 0 && !isReconciled;

            let rowClass = 'transaction-row';
            if (isReconciled) rowClass += ' reconciled';
            else if (hasSuggestion) rowClass += ' suggested';

            html += `
                <div class="${rowClass}" data-name="${txn.name}" onclick="page.reconciler.open_match_modal('${txn.name}')">
                    <div class="row align-items-center">
                        <div class="col-md-2 col-4">
                            <div class="text-muted small">${txn.date}</div>
                            <div class="small">${txn.reference_number || ''}</div>
                        </div>
                        <div class="col-md-6 col-8">
                            <div class="fw-bold">${txn.description || 'No description'}</div>
                            ${txn.party ? `<div class="small text-muted">${txn.party_type}: ${txn.party}</div>` : ''}
                        </div>
                        <div class="col-md-2 col-6 text-end">
                            <div class="amount ${isDeposit ? 'deposit' : 'withdrawal'}">
                                ${isDeposit ? '+' : '-'}${format_currency(amount)}
                            </div>
                        </div>
                        <div class="col-md-2 col-6 text-end">
                            ${isReconciled 
                                ? '<span class="badge bg-success">Reconciled</span>'
                                : hasSuggestion 
                                    ? '<span class="badge bg-warning">Suggested</span>'
                                    : '<span class="badge bg-secondary">Pending</span>'
                            }
                        </div>
                    </div>
                </div>
            `;
        });

        container.html(html);
    }

    update_summary() {
        const deposits = this.transactions.reduce((sum, t) => sum + (t.deposit || 0), 0);
        const withdrawals = this.transactions.reduce((sum, t) => sum + (t.withdrawal || 0), 0);
        const unreconciled = this.transactions.filter(t => t.status !== 'Reconciled').length;
        const autoMatched = this.transactions.filter(t => t.unallocated_amount === 0 && t.status !== 'Reconciled').length;

        $('#total-deposits').text(format_currency(deposits));
        $('#total-withdrawals').text(format_currency(withdrawals));
        $('#unreconciled-count').text(unreconciled);
        $('#auto-matched').text(autoMatched);
    }

    open_match_modal(transactionName) {
        const txn = this.transactions.find(t => t.name === transactionName);
        if (!txn) return;

        this.currentTransaction = txn;

        const isDeposit = txn.deposit > 0;
        const amount = isDeposit ? txn.deposit : txn.withdrawal;

        $('#match-date').text(txn.date);
        $('#match-description').text(txn.description || 'No description');
        $('#match-amount').text((isDeposit ? '+' : '-') + format_currency(amount));
        $('#match-amount').removeClass('text-success text-danger').addClass(isDeposit ? 'text-success' : 'text-danger');

        // Pre-fill rule pattern
        $('#rule-pattern').val(txn.description ? txn.description.substring(0, 30) : '');

        // Load suggestions
        this.load_match_suggestions(txn);

        const modal = new bootstrap.Modal(document.getElementById('match-modal'));
        modal.show();
    }

    load_match_suggestions(txn) {
        const container = $('#match-suggestions');
        const isDeposit = txn.deposit > 0;
        const amount = isDeposit ? txn.deposit : txn.withdrawal;

        // Search for matching documents
        const doctype = isDeposit ? 'Sales Invoice' : 'Purchase Invoice';
        
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: doctype,
                filters: {
                    outstanding_amount: ['>', 0],
                    grand_total: ['between', [amount * 0.95, amount * 1.05]]
                },
                fields: ['name', 'grand_total', 'outstanding_amount', 'customer', 'supplier', 'posting_date'],
                limit: 10
            },
            callback: (r) => {
                if (r.message && r.message.length) {
                    let html = '';
                    r.message.forEach(doc => {
                        const party = doc.customer || doc.supplier;
                        html += `
                            <a href="#" class="list-group-item list-group-item-action match-suggestion" 
                               data-doctype="${doctype}" data-name="${doc.name}">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <strong>${doc.name}</strong>
                                        <br><small class="text-muted">${party} | ${doc.posting_date}</small>
                                    </div>
                                    <div class="text-end">
                                        <div>${format_currency(doc.grand_total)}</div>
                                        <small class="text-muted">Outstanding: ${format_currency(doc.outstanding_amount)}</small>
                                    </div>
                                </div>
                            </a>
                        `;
                    });
                    container.html(html);

                    // Setup click handlers
                    container.find('.match-suggestion').on('click', (e) => {
                        e.preventDefault();
                        const doctype = $(e.currentTarget).data('doctype');
                        const name = $(e.currentTarget).data('name');
                        this.match_to_document(doctype, name);
                    });
                } else {
                    container.html('<div class="text-muted text-center py-3">No matching documents found</div>');
                }
            }
        });
    }

    match_to_document(doctype, name) {
        frappe.call({
            method: 'erpnext.accounts.doctype.bank_transaction.bank_transaction.reconcile_vouchers',
            args: {
                bank_transaction_name: this.currentTransaction.name,
                vouchers: JSON.stringify([{
                    payment_doctype: doctype,
                    payment_name: name,
                    amount: this.currentTransaction.deposit || this.currentTransaction.withdrawal
                }])
            },
            callback: (r) => {
                bootstrap.Modal.getInstance(document.getElementById('match-modal')).hide();
                frappe.show_alert({message: __('Transaction matched successfully'), indicator: 'green'});
                this.load_transactions();
            }
        });
    }

    auto_categorize() {
        const bankAccount = this.page.fields_dict.bank_account.get_value();
        const fromDate = this.page.fields_dict.from_date.get_value();
        const toDate = this.page.fields_dict.to_date.get_value();

        if (!bankAccount) {
            frappe.msgprint(__('Please select a bank account'));
            return;
        }

        frappe.call({
            method: 'bookingzone.api.bulk_categorize_transactions',
            args: {
                bank_account: bankAccount,
                from_date: fromDate,
                to_date: toDate
            },
            callback: (r) => {
                if (r.message) {
                    frappe.msgprint({
                        title: __('Auto-Categorization Complete'),
                        message: __('Processed {0} transactions, matched {1}', 
                            [r.message.processed, r.message.matched]),
                        indicator: 'green'
                    });
                    this.load_transactions();
                }
            }
        });
    }
}
