/**
 * Inventory Count Entry Page
 * ===========================
 * Mobile-optimized inventory counting interface for restaurant staff.
 * Supports barcode scanning, quick entry, and real-time sync.
 */

frappe.pages['inventory-count-entry'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Inventory Count',
        single_column: true
    });

    // Add warehouse selector
    page.add_field({
        fieldname: 'warehouse',
        label: __('Warehouse'),
        fieldtype: 'Link',
        options: 'Warehouse',
        reqd: 1,
        change: function() {
            page.counter.load_items();
        }
    });

    // Add category filter
    page.add_field({
        fieldname: 'item_group',
        label: __('Category'),
        fieldtype: 'Link',
        options: 'Item Group',
        change: function() {
            page.counter.filter_items();
        }
    });

    // Add search
    page.add_field({
        fieldname: 'search',
        label: __('Search'),
        fieldtype: 'Data',
        change: function() {
            page.counter.filter_items();
        }
    });

    // Add save button
    page.add_button(__('Save Count'), function() {
        page.counter.save_count();
    }, 'btn-primary');

    // Initialize counter
    page.counter = new InventoryCounter(page);
};

class InventoryCounter {
    constructor(page) {
        this.page = page;
        this.wrapper = $(page.body);
        this.items = [];
        this.counts = {};
        this.inventory_count_doc = null;
        this.init();
    }

    init() {
        this.render_skeleton();
        this.setup_barcode_scanner();
    }

    render_skeleton() {
        this.wrapper.html(`
            <div class="inventory-counter">
                <!-- Stats Bar -->
                <div class="stats-bar bg-light p-3 mb-3 rounded">
                    <div class="row text-center">
                        <div class="col-4">
                            <h4 class="mb-0" id="items-counted">0</h4>
                            <small class="text-muted">Counted</small>
                        </div>
                        <div class="col-4">
                            <h4 class="mb-0" id="items-remaining">0</h4>
                            <small class="text-muted">Remaining</small>
                        </div>
                        <div class="col-4">
                            <h4 class="mb-0" id="variance-count">0</h4>
                            <small class="text-muted">Variances</small>
                        </div>
                    </div>
                </div>

                <!-- Barcode Scanner -->
                <div class="barcode-scanner mb-3">
                    <div class="input-group">
                        <span class="input-group-text"><i class="fa fa-barcode"></i></span>
                        <input type="text" class="form-control" id="barcode-input" 
                               placeholder="Scan barcode or enter item code..." autofocus>
                    </div>
                </div>

                <!-- Items List -->
                <div class="items-list" id="items-list">
                    <div class="text-center py-5 text-muted">
                        <i class="fa fa-warehouse fa-3x mb-3"></i>
                        <p>Select a warehouse to start counting</p>
                    </div>
                </div>

                <!-- Quick Entry Modal -->
                <div class="modal fade" id="quick-entry-modal" tabindex="-1">
                    <div class="modal-dialog modal-dialog-centered">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title" id="quick-entry-item-name">Item</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="mb-3">
                                    <label class="form-label">Expected Quantity</label>
                                    <input type="text" class="form-control" id="quick-entry-expected" readonly>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Counted Quantity</label>
                                    <input type="number" class="form-control form-control-lg" 
                                           id="quick-entry-counted" min="0" step="0.01">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Notes</label>
                                    <input type="text" class="form-control" id="quick-entry-notes" 
                                           placeholder="Optional notes...">
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="button" class="btn btn-primary" id="quick-entry-save">Save</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <style>
                .inventory-counter .item-card {
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    padding: 12px;
                    margin-bottom: 8px;
                    cursor: pointer;
                    transition: all 0.2s;
                }
                .inventory-counter .item-card:hover {
                    border-color: #5e64ff;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }
                .inventory-counter .item-card.counted {
                    background-color: #d4edda;
                    border-color: #28a745;
                }
                .inventory-counter .item-card.variance {
                    background-color: #fff3cd;
                    border-color: #ffc107;
                }
                .inventory-counter .item-card .item-name {
                    font-weight: 600;
                    font-size: 1rem;
                }
                .inventory-counter .item-card .item-code {
                    font-size: 0.8rem;
                    color: #6c757d;
                }
                .inventory-counter .item-card .count-display {
                    font-size: 1.5rem;
                    font-weight: bold;
                }
                .inventory-counter .quick-count-btns {
                    display: flex;
                    gap: 4px;
                }
                .inventory-counter .quick-count-btns .btn {
                    padding: 4px 12px;
                    font-size: 0.9rem;
                }
                @media (max-width: 768px) {
                    .inventory-counter .item-card {
                        padding: 16px;
                    }
                    .inventory-counter .item-card .count-display {
                        font-size: 1.8rem;
                    }
                }
            </style>
        `);
    }

    setup_barcode_scanner() {
        const barcodeInput = $('#barcode-input');
        
        barcodeInput.on('keypress', (e) => {
            if (e.which === 13) {
                const barcode = barcodeInput.val().trim();
                if (barcode) {
                    this.handle_barcode(barcode);
                    barcodeInput.val('');
                }
            }
        });

        // Quick entry modal save
        $('#quick-entry-save').on('click', () => {
            this.save_quick_entry();
        });

        // Enter key in quick entry
        $('#quick-entry-counted').on('keypress', (e) => {
            if (e.which === 13) {
                this.save_quick_entry();
            }
        });
    }

    load_items() {
        const warehouse = this.page.fields_dict.warehouse.get_value();
        if (!warehouse) return;

        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Bin',
                filters: {
                    warehouse: warehouse
                },
                fields: ['item_code', 'actual_qty', 'stock_value'],
                limit_page_length: 0
            },
            callback: (r) => {
                if (r.message) {
                    this.items = r.message;
                    this.load_item_details();
                }
            }
        });
    }

    load_item_details() {
        const itemCodes = this.items.map(i => i.item_code);
        
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Item',
                filters: {
                    name: ['in', itemCodes]
                },
                fields: ['name', 'item_name', 'item_group', 'stock_uom', 'barcode'],
                limit_page_length: 0
            },
            callback: (r) => {
                if (r.message) {
                    // Merge item details
                    const itemDetails = {};
                    r.message.forEach(item => {
                        itemDetails[item.name] = item;
                    });

                    this.items = this.items.map(bin => ({
                        ...bin,
                        ...itemDetails[bin.item_code]
                    }));

                    this.render_items();
                }
            }
        });
    }

    render_items() {
        const container = $('#items-list');
        const itemGroup = this.page.fields_dict.item_group.get_value();
        const search = (this.page.fields_dict.search.get_value() || '').toLowerCase();

        let filteredItems = this.items;

        // Filter by item group
        if (itemGroup) {
            filteredItems = filteredItems.filter(i => i.item_group === itemGroup);
        }

        // Filter by search
        if (search) {
            filteredItems = filteredItems.filter(i => 
                (i.item_name || '').toLowerCase().includes(search) ||
                (i.item_code || '').toLowerCase().includes(search) ||
                (i.barcode || '').toLowerCase().includes(search)
            );
        }

        if (!filteredItems.length) {
            container.html(`
                <div class="text-center py-5 text-muted">
                    <i class="fa fa-search fa-3x mb-3"></i>
                    <p>No items found</p>
                </div>
            `);
            return;
        }

        let html = '';
        filteredItems.forEach(item => {
            const counted = this.counts[item.item_code];
            const hasCount = counted !== undefined;
            const variance = hasCount ? counted - item.actual_qty : 0;
            const hasVariance = hasCount && Math.abs(variance) > 0.01;

            let cardClass = 'item-card';
            if (hasCount) cardClass += ' counted';
            if (hasVariance) cardClass += ' variance';

            html += `
                <div class="${cardClass}" data-item="${item.item_code}" onclick="page.counter.open_quick_entry('${item.item_code}')">
                    <div class="row align-items-center">
                        <div class="col-7">
                            <div class="item-name">${item.item_name || item.item_code}</div>
                            <div class="item-code">${item.item_code} | ${item.stock_uom}</div>
                            <div class="text-muted small">Expected: ${item.actual_qty}</div>
                        </div>
                        <div class="col-5 text-end">
                            <div class="count-display ${hasVariance ? 'text-warning' : ''}">${hasCount ? counted : '-'}</div>
                            ${hasVariance ? `<small class="text-warning">Var: ${variance > 0 ? '+' : ''}${variance.toFixed(2)}</small>` : ''}
                        </div>
                    </div>
                </div>
            `;
        });

        container.html(html);
        this.update_stats();
    }

    filter_items() {
        this.render_items();
    }

    handle_barcode(barcode) {
        // Find item by barcode or item_code
        const item = this.items.find(i => 
            i.barcode === barcode || i.item_code === barcode
        );

        if (item) {
            this.open_quick_entry(item.item_code);
        } else {
            frappe.msgprint(__('Item not found: {0}', [barcode]));
        }
    }

    open_quick_entry(itemCode) {
        const item = this.items.find(i => i.item_code === itemCode);
        if (!item) return;

        this.currentItem = item;

        $('#quick-entry-item-name').text(item.item_name || item.item_code);
        $('#quick-entry-expected').val(`${item.actual_qty} ${item.stock_uom}`);
        $('#quick-entry-counted').val(this.counts[itemCode] || '');
        $('#quick-entry-notes').val('');

        const modal = new bootstrap.Modal(document.getElementById('quick-entry-modal'));
        modal.show();

        // Focus on count input
        setTimeout(() => {
            $('#quick-entry-counted').focus().select();
        }, 300);
    }

    save_quick_entry() {
        const counted = parseFloat($('#quick-entry-counted').val());
        
        if (isNaN(counted) || counted < 0) {
            frappe.msgprint(__('Please enter a valid quantity'));
            return;
        }

        this.counts[this.currentItem.item_code] = counted;
        
        // Close modal
        bootstrap.Modal.getInstance(document.getElementById('quick-entry-modal')).hide();
        
        // Re-render items
        this.render_items();
        
        // Show confirmation
        frappe.show_alert({
            message: __('Count saved for {0}', [this.currentItem.item_name]),
            indicator: 'green'
        }, 2);
    }

    update_stats() {
        const counted = Object.keys(this.counts).length;
        const total = this.items.length;
        const remaining = total - counted;
        
        let variances = 0;
        Object.keys(this.counts).forEach(itemCode => {
            const item = this.items.find(i => i.item_code === itemCode);
            if (item && Math.abs(this.counts[itemCode] - item.actual_qty) > 0.01) {
                variances++;
            }
        });

        $('#items-counted').text(counted);
        $('#items-remaining').text(remaining);
        $('#variance-count').text(variances);
    }

    save_count() {
        const warehouse = this.page.fields_dict.warehouse.get_value();
        
        if (!warehouse) {
            frappe.msgprint(__('Please select a warehouse'));
            return;
        }

        if (Object.keys(this.counts).length === 0) {
            frappe.msgprint(__('No items have been counted'));
            return;
        }

        // Prepare items for saving
        const items = Object.keys(this.counts).map(itemCode => {
            const item = this.items.find(i => i.item_code === itemCode);
            return {
                item_code: itemCode,
                item_name: item ? item.item_name : itemCode,
                expected_qty: item ? item.actual_qty : 0,
                counted_qty: this.counts[itemCode],
                variance: this.counts[itemCode] - (item ? item.actual_qty : 0),
                uom: item ? item.stock_uom : 'Nos'
            };
        });

        frappe.call({
            method: 'frappe.client.insert',
            args: {
                doc: {
                    doctype: 'Inventory Count',
                    warehouse: warehouse,
                    count_date: frappe.datetime.get_today(),
                    count_type: 'Full Count',
                    items: items
                }
            },
            callback: (r) => {
                if (r.message) {
                    frappe.msgprint({
                        title: __('Success'),
                        message: __('Inventory count saved: {0}', [r.message.name]),
                        indicator: 'green'
                    });
                    
                    // Reset counts
                    this.counts = {};
                    this.render_items();
                    
                    // Open the saved document
                    frappe.set_route('Form', 'Inventory Count', r.message.name);
                }
            }
        });
    }
}
