/**
 * Restaurant Dashboard Page
 * =========================
 * Main dashboard showing key restaurant metrics including:
 * - Today's sales and transactions
 * - Prime cost indicators
 * - Labor metrics
 * - Inventory alerts
 */

frappe.pages['restaurant-dashboard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Restaurant Dashboard',
        single_column: true
    });

    // Add outlet selector
    page.add_field({
        fieldname: 'outlet',
        label: __('Outlet'),
        fieldtype: 'Link',
        options: 'Outlet',
        default: frappe.defaults.get_user_default('outlet'),
        change: function() {
            page.dashboard.refresh();
        }
    });

    // Add date range selector
    page.add_field({
        fieldname: 'date_range',
        label: __('Period'),
        fieldtype: 'Select',
        options: [
            {value: 'today', label: __('Today')},
            {value: 'yesterday', label: __('Yesterday')},
            {value: 'this_week', label: __('This Week')},
            {value: 'last_week', label: __('Last Week')},
            {value: 'this_month', label: __('This Month')},
            {value: 'last_month', label: __('Last Month')}
        ],
        default: 'today',
        change: function() {
            page.dashboard.refresh();
        }
    });

    // Add refresh button
    page.add_button(__('Refresh'), function() {
        page.dashboard.refresh();
    }, 'btn-primary');

    // Initialize dashboard
    page.dashboard = new RestaurantDashboard(page);
};

class RestaurantDashboard {
    constructor(page) {
        this.page = page;
        this.wrapper = $(page.body);
        this.init();
    }

    init() {
        this.render_skeleton();
        this.refresh();
    }

    render_skeleton() {
        this.wrapper.html(`
            <div class="restaurant-dashboard">
                <!-- Loading State -->
                <div class="dashboard-loading text-center py-5">
                    <div class="spinner-border text-primary" role="status">
                        <span class="sr-only">Loading...</span>
                    </div>
                    <p class="mt-3 text-muted">Loading dashboard data...</p>
                </div>
                
                <!-- Dashboard Content (hidden initially) -->
                <div class="dashboard-content" style="display: none;">
                    <!-- KPI Cards Row -->
                    <div class="row kpi-cards mb-4">
                        <div class="col-lg-3 col-md-6 mb-3">
                            <div class="card kpi-card sales-card">
                                <div class="card-body">
                                    <div class="kpi-icon"><i class="fa fa-dollar-sign"></i></div>
                                    <div class="kpi-content">
                                        <h6 class="kpi-label">Net Sales</h6>
                                        <h2 class="kpi-value" id="net-sales">$0</h2>
                                        <span class="kpi-change" id="sales-change"></span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="col-lg-3 col-md-6 mb-3">
                            <div class="card kpi-card transactions-card">
                                <div class="card-body">
                                    <div class="kpi-icon"><i class="fa fa-receipt"></i></div>
                                    <div class="kpi-content">
                                        <h6 class="kpi-label">Transactions</h6>
                                        <h2 class="kpi-value" id="transactions">0</h2>
                                        <span class="kpi-change" id="transactions-change"></span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="col-lg-3 col-md-6 mb-3">
                            <div class="card kpi-card prime-cost-card">
                                <div class="card-body">
                                    <div class="kpi-icon"><i class="fa fa-chart-pie"></i></div>
                                    <div class="kpi-content">
                                        <h6 class="kpi-label">Prime Cost</h6>
                                        <h2 class="kpi-value" id="prime-cost">0%</h2>
                                        <span class="kpi-target" id="prime-target">Target: 60%</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="col-lg-3 col-md-6 mb-3">
                            <div class="card kpi-card labor-card">
                                <div class="card-body">
                                    <div class="kpi-icon"><i class="fa fa-users"></i></div>
                                    <div class="kpi-content">
                                        <h6 class="kpi-label">Labor Cost</h6>
                                        <h2 class="kpi-value" id="labor-cost">0%</h2>
                                        <span class="kpi-target" id="labor-target">Target: 30%</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Charts Row -->
                    <div class="row mb-4">
                        <div class="col-lg-8 mb-3">
                            <div class="card">
                                <div class="card-header">
                                    <h5 class="card-title mb-0">Sales Trend</h5>
                                </div>
                                <div class="card-body">
                                    <canvas id="sales-trend-chart" height="300"></canvas>
                                </div>
                            </div>
                        </div>
                        <div class="col-lg-4 mb-3">
                            <div class="card">
                                <div class="card-header">
                                    <h5 class="card-title mb-0">Sales by Category</h5>
                                </div>
                                <div class="card-body">
                                    <canvas id="category-chart" height="300"></canvas>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Alerts and Quick Actions Row -->
                    <div class="row mb-4">
                        <div class="col-lg-6 mb-3">
                            <div class="card">
                                <div class="card-header d-flex justify-content-between align-items-center">
                                    <h5 class="card-title mb-0">Inventory Alerts</h5>
                                    <a href="/app/par-level" class="btn btn-sm btn-outline-primary">View All</a>
                                </div>
                                <div class="card-body">
                                    <div id="inventory-alerts">
                                        <p class="text-muted">No alerts</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="col-lg-6 mb-3">
                            <div class="card">
                                <div class="card-header">
                                    <h5 class="card-title mb-0">Quick Actions</h5>
                                </div>
                                <div class="card-body">
                                    <div class="quick-actions">
                                        <button class="btn btn-outline-primary me-2 mb-2" onclick="frappe.new_doc('Inventory Count')">
                                            <i class="fa fa-clipboard-list"></i> New Inventory Count
                                        </button>
                                        <button class="btn btn-outline-warning me-2 mb-2" onclick="frappe.new_doc('Waste Log')">
                                            <i class="fa fa-trash"></i> Log Waste
                                        </button>
                                        <button class="btn btn-outline-success me-2 mb-2" onclick="frappe.set_route('query-report', 'Prime Cost Report')">
                                            <i class="fa fa-chart-bar"></i> Prime Cost Report
                                        </button>
                                        <button class="btn btn-outline-info me-2 mb-2" onclick="frappe.new_doc('Recipe')">
                                            <i class="fa fa-utensils"></i> New Recipe
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Recent Activity Row -->
                    <div class="row">
                        <div class="col-lg-6 mb-3">
                            <div class="card">
                                <div class="card-header">
                                    <h5 class="card-title mb-0">Recent Waste Logs</h5>
                                </div>
                                <div class="card-body">
                                    <div id="recent-waste" class="table-responsive">
                                        <table class="table table-sm">
                                            <thead>
                                                <tr>
                                                    <th>Item</th>
                                                    <th>Qty</th>
                                                    <th>Value</th>
                                                    <th>Reason</th>
                                                </tr>
                                            </thead>
                                            <tbody id="waste-table-body">
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="col-lg-6 mb-3">
                            <div class="card">
                                <div class="card-header">
                                    <h5 class="card-title mb-0">Top Selling Items</h5>
                                </div>
                                <div class="card-body">
                                    <div id="top-items" class="table-responsive">
                                        <table class="table table-sm">
                                            <thead>
                                                <tr>
                                                    <th>Item</th>
                                                    <th>Qty Sold</th>
                                                    <th>Revenue</th>
                                                </tr>
                                            </thead>
                                            <tbody id="top-items-body">
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `);
    }

    refresh() {
        const outlet = this.page.fields_dict.outlet.get_value();
        const period = this.page.fields_dict.date_range.get_value();
        
        // Show loading
        this.wrapper.find('.dashboard-loading').show();
        this.wrapper.find('.dashboard-content').hide();

        // Fetch dashboard data
        frappe.call({
            method: 'bookingzone.api.get_restaurant_dashboard_data',
            args: {
                outlet: outlet,
                period: period
            },
            callback: (r) => {
                if (r.message) {
                    this.render_data(r.message);
                }
                // Hide loading, show content
                this.wrapper.find('.dashboard-loading').hide();
                this.wrapper.find('.dashboard-content').show();
            },
            error: () => {
                this.wrapper.find('.dashboard-loading').hide();
                this.wrapper.find('.dashboard-content').show();
                frappe.msgprint(__('Error loading dashboard data'));
            }
        });
    }

    render_data(data) {
        // Update KPI cards
        $('#net-sales').text(format_currency(data.net_sales || 0));
        $('#transactions').text(data.transactions || 0);
        $('#prime-cost').text((data.prime_cost_pct || 0).toFixed(1) + '%');
        $('#labor-cost').text((data.labor_cost_pct || 0).toFixed(1) + '%');

        // Update change indicators
        this.render_change('#sales-change', data.sales_change);
        this.render_change('#transactions-change', data.transactions_change);

        // Color code prime cost
        const primeCostEl = $('#prime-cost');
        primeCostEl.removeClass('text-success text-warning text-danger');
        if (data.prime_cost_pct <= 60) {
            primeCostEl.addClass('text-success');
        } else if (data.prime_cost_pct <= 65) {
            primeCostEl.addClass('text-warning');
        } else {
            primeCostEl.addClass('text-danger');
        }

        // Render charts
        this.render_sales_trend_chart(data.sales_trend || []);
        this.render_category_chart(data.category_breakdown || {});

        // Render inventory alerts
        this.render_inventory_alerts(data.inventory_alerts || []);

        // Render recent waste
        this.render_waste_table(data.recent_waste || []);

        // Render top items
        this.render_top_items(data.top_items || []);
    }

    render_change(selector, change) {
        const el = $(selector);
        if (change === undefined || change === null) {
            el.text('');
            return;
        }
        
        const icon = change >= 0 ? 'fa-arrow-up' : 'fa-arrow-down';
        const colorClass = change >= 0 ? 'text-success' : 'text-danger';
        el.html(`<i class="fa ${icon}"></i> ${Math.abs(change).toFixed(1)}%`);
        el.removeClass('text-success text-danger').addClass(colorClass);
    }

    render_sales_trend_chart(data) {
        const ctx = document.getElementById('sales-trend-chart');
        if (!ctx) return;

        // Destroy existing chart
        if (this.salesChart) {
            this.salesChart.destroy();
        }

        this.salesChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.map(d => d.date),
                datasets: [{
                    label: 'Net Sales',
                    data: data.map(d => d.net_sales),
                    borderColor: '#5e64ff',
                    backgroundColor: 'rgba(94, 100, 255, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return '$' + value.toLocaleString();
                            }
                        }
                    }
                }
            }
        });
    }

    render_category_chart(data) {
        const ctx = document.getElementById('category-chart');
        if (!ctx) return;

        // Destroy existing chart
        if (this.categoryChart) {
            this.categoryChart.destroy();
        }

        const labels = Object.keys(data);
        const values = Object.values(data);
        const colors = ['#5e64ff', '#ff6b6b', '#4ecdc4', '#ffe66d', '#95e1d3', '#f38181'];

        this.categoryChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors.slice(0, labels.length)
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    render_inventory_alerts(alerts) {
        const container = $('#inventory-alerts');
        
        if (!alerts.length) {
            container.html('<p class="text-muted">No inventory alerts</p>');
            return;
        }

        let html = '<ul class="list-group list-group-flush">';
        alerts.forEach(alert => {
            const badgeClass = alert.status === 'Critical' ? 'bg-danger' : 'bg-warning';
            html += `
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${alert.item_name}</strong>
                        <br><small class="text-muted">Current: ${alert.current_stock} | Par: ${alert.par_level}</small>
                    </div>
                    <span class="badge ${badgeClass}">${alert.status}</span>
                </li>
            `;
        });
        html += '</ul>';
        container.html(html);
    }

    render_waste_table(waste) {
        const tbody = $('#waste-table-body');
        
        if (!waste.length) {
            tbody.html('<tr><td colspan="4" class="text-muted">No recent waste logs</td></tr>');
            return;
        }

        let html = '';
        waste.forEach(w => {
            html += `
                <tr>
                    <td>${w.item_name}</td>
                    <td>${w.quantity}</td>
                    <td>${format_currency(w.waste_value)}</td>
                    <td><span class="badge bg-secondary">${w.waste_reason}</span></td>
                </tr>
            `;
        });
        tbody.html(html);
    }

    render_top_items(items) {
        const tbody = $('#top-items-body');
        
        if (!items.length) {
            tbody.html('<tr><td colspan="3" class="text-muted">No sales data</td></tr>');
            return;
        }

        let html = '';
        items.forEach(item => {
            html += `
                <tr>
                    <td>${item.item_name}</td>
                    <td>${item.qty}</td>
                    <td>${format_currency(item.revenue)}</td>
                </tr>
            `;
        });
        tbody.html(html);
    }
}
