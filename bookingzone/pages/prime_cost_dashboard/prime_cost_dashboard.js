/**
 * Prime Cost Dashboard Page
 * ==========================
 * Displays prime cost metrics (Food Cost + Labor Cost) with trends and analysis.
 */

frappe.pages['prime-cost-dashboard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Prime Cost Dashboard',
        single_column: true
    });

    // Add outlet selector
    page.add_field({
        fieldname: 'outlet',
        label: __('Outlet'),
        fieldtype: 'Link',
        options: 'Outlet',
        change: function() {
            page.dashboard.refresh();
        }
    });

    // Add period selector
    page.add_field({
        fieldname: 'periods',
        label: __('Periods'),
        fieldtype: 'Select',
        options: [
            {value: '4', label: __('Last 4 Weeks')},
            {value: '8', label: __('Last 8 Weeks')},
            {value: '12', label: __('Last 12 Weeks')},
            {value: '26', label: __('Last 6 Months')},
            {value: '52', label: __('Last Year')}
        ],
        default: '12',
        change: function() {
            page.dashboard.refresh();
        }
    });

    // Add generate report button
    page.add_button(__('Generate Weekly Report'), function() {
        page.dashboard.generate_report();
    }, 'btn-primary');

    // Initialize dashboard
    page.dashboard = new PrimeCostDashboard(page);
};

class PrimeCostDashboard {
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
            <div class="prime-cost-dashboard">
                <!-- Loading State -->
                <div class="dashboard-loading text-center py-5">
                    <div class="spinner-border text-primary" role="status">
                        <span class="sr-only">Loading...</span>
                    </div>
                    <p class="mt-3 text-muted">Loading prime cost data...</p>
                </div>
                
                <!-- Dashboard Content -->
                <div class="dashboard-content" style="display: none;">
                    <!-- Summary Cards -->
                    <div class="row mb-4">
                        <div class="col-lg-3 col-md-6 mb-3">
                            <div class="card bg-primary text-white">
                                <div class="card-body">
                                    <h6 class="card-subtitle mb-2 opacity-75">Total Sales</h6>
                                    <h2 class="card-title mb-0" id="total-sales">$0</h2>
                                </div>
                            </div>
                        </div>
                        <div class="col-lg-3 col-md-6 mb-3">
                            <div class="card" id="food-cost-card">
                                <div class="card-body">
                                    <h6 class="card-subtitle mb-2 text-muted">Food Cost</h6>
                                    <h2 class="card-title mb-0" id="food-cost-pct">0%</h2>
                                    <small class="text-muted">Target: 30%</small>
                                </div>
                            </div>
                        </div>
                        <div class="col-lg-3 col-md-6 mb-3">
                            <div class="card" id="labor-cost-card">
                                <div class="card-body">
                                    <h6 class="card-subtitle mb-2 text-muted">Labor Cost</h6>
                                    <h2 class="card-title mb-0" id="labor-cost-pct">0%</h2>
                                    <small class="text-muted">Target: 30%</small>
                                </div>
                            </div>
                        </div>
                        <div class="col-lg-3 col-md-6 mb-3">
                            <div class="card" id="prime-cost-card">
                                <div class="card-body">
                                    <h6 class="card-subtitle mb-2 text-muted">Prime Cost</h6>
                                    <h2 class="card-title mb-0" id="prime-cost-pct">0%</h2>
                                    <small class="text-muted">Target: 60%</small>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Prime Cost Trend Chart -->
                    <div class="row mb-4">
                        <div class="col-12">
                            <div class="card">
                                <div class="card-header">
                                    <h5 class="card-title mb-0">Prime Cost Trend</h5>
                                </div>
                                <div class="card-body">
                                    <canvas id="prime-cost-trend-chart" height="300"></canvas>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Breakdown Charts -->
                    <div class="row mb-4">
                        <div class="col-lg-6 mb-3">
                            <div class="card">
                                <div class="card-header">
                                    <h5 class="card-title mb-0">Cost Breakdown</h5>
                                </div>
                                <div class="card-body">
                                    <canvas id="cost-breakdown-chart" height="250"></canvas>
                                </div>
                            </div>
                        </div>
                        <div class="col-lg-6 mb-3">
                            <div class="card">
                                <div class="card-header">
                                    <h5 class="card-title mb-0">Food vs Labor Trend</h5>
                                </div>
                                <div class="card-body">
                                    <canvas id="food-labor-chart" height="250"></canvas>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Recent Reports Table -->
                    <div class="row">
                        <div class="col-12">
                            <div class="card">
                                <div class="card-header d-flex justify-content-between align-items-center">
                                    <h5 class="card-title mb-0">Recent Prime Cost Reports</h5>
                                    <a href="/app/prime-cost-report" class="btn btn-sm btn-outline-primary">View All</a>
                                </div>
                                <div class="card-body">
                                    <div class="table-responsive">
                                        <table class="table table-hover">
                                            <thead>
                                                <tr>
                                                    <th>Period</th>
                                                    <th>Sales</th>
                                                    <th>Food Cost</th>
                                                    <th>Labor Cost</th>
                                                    <th>Prime Cost</th>
                                                    <th>Status</th>
                                                </tr>
                                            </thead>
                                            <tbody id="reports-table-body">
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
        const periods = this.page.fields_dict.periods.get_value() || 12;
        
        this.wrapper.find('.dashboard-loading').show();
        this.wrapper.find('.dashboard-content').hide();

        frappe.call({
            method: 'bookingzone.api.get_prime_cost_trend',
            args: {
                outlet: outlet,
                periods: parseInt(periods)
            },
            callback: (r) => {
                if (r.message) {
                    this.render_data(r.message);
                }
                this.wrapper.find('.dashboard-loading').hide();
                this.wrapper.find('.dashboard-content').show();
            },
            error: () => {
                this.wrapper.find('.dashboard-loading').hide();
                this.wrapper.find('.dashboard-content').show();
                frappe.msgprint(__('Error loading prime cost data'));
            }
        });
    }

    render_data(data) {
        if (!data || !data.length) {
            this.render_empty_state();
            return;
        }

        // Calculate averages from trend data
        const avgFoodCost = data.reduce((sum, d) => sum + (d.food_cost_percentage || 0), 0) / data.length;
        const avgLaborCost = data.reduce((sum, d) => sum + (d.labor_cost_percentage || 0), 0) / data.length;
        const avgPrimeCost = data.reduce((sum, d) => sum + (d.prime_cost_percentage || 0), 0) / data.length;
        const totalSales = data.reduce((sum, d) => sum + (d.total_sales || 0), 0);

        // Update summary cards
        $('#total-sales').text(format_currency(totalSales));
        $('#food-cost-pct').text(avgFoodCost.toFixed(1) + '%');
        $('#labor-cost-pct').text(avgLaborCost.toFixed(1) + '%');
        $('#prime-cost-pct').text(avgPrimeCost.toFixed(1) + '%');

        // Color code cards based on targets
        this.colorCodeCard('#food-cost-card', avgFoodCost, 30, 35);
        this.colorCodeCard('#labor-cost-card', avgLaborCost, 30, 35);
        this.colorCodeCard('#prime-cost-card', avgPrimeCost, 60, 65);

        // Render charts
        this.render_trend_chart(data);
        this.render_breakdown_chart(avgFoodCost, avgLaborCost);
        this.render_food_labor_chart(data);

        // Render reports table
        this.render_reports_table(data);
    }

    colorCodeCard(selector, value, goodThreshold, warningThreshold) {
        const card = $(selector);
        card.removeClass('border-success border-warning border-danger');
        
        if (value <= goodThreshold) {
            card.addClass('border-success');
            card.find('.card-title').addClass('text-success');
        } else if (value <= warningThreshold) {
            card.addClass('border-warning');
            card.find('.card-title').addClass('text-warning');
        } else {
            card.addClass('border-danger');
            card.find('.card-title').addClass('text-danger');
        }
    }

    render_trend_chart(data) {
        const ctx = document.getElementById('prime-cost-trend-chart');
        if (!ctx) return;

        if (this.trendChart) {
            this.trendChart.destroy();
        }

        this.trendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.map(d => d.report_date),
                datasets: [{
                    label: 'Prime Cost %',
                    data: data.map(d => d.prime_cost_percentage),
                    borderColor: '#5e64ff',
                    backgroundColor: 'rgba(94, 100, 255, 0.1)',
                    fill: true,
                    tension: 0.4
                }, {
                    label: 'Target (60%)',
                    data: data.map(() => 60),
                    borderColor: '#ff6b6b',
                    borderDash: [5, 5],
                    fill: false,
                    pointRadius: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                }
            }
        });
    }

    render_breakdown_chart(foodCost, laborCost) {
        const ctx = document.getElementById('cost-breakdown-chart');
        if (!ctx) return;

        if (this.breakdownChart) {
            this.breakdownChart.destroy();
        }

        const remaining = 100 - foodCost - laborCost;

        this.breakdownChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Food Cost', 'Labor Cost', 'Other/Profit'],
                datasets: [{
                    data: [foodCost, laborCost, remaining > 0 ? remaining : 0],
                    backgroundColor: ['#ff6b6b', '#4ecdc4', '#95e1d3']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.label + ': ' + context.raw.toFixed(1) + '%';
                            }
                        }
                    }
                }
            }
        });
    }

    render_food_labor_chart(data) {
        const ctx = document.getElementById('food-labor-chart');
        if (!ctx) return;

        if (this.foodLaborChart) {
            this.foodLaborChart.destroy();
        }

        this.foodLaborChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(d => d.report_date),
                datasets: [{
                    label: 'Food Cost %',
                    data: data.map(d => d.food_cost_percentage),
                    backgroundColor: '#ff6b6b'
                }, {
                    label: 'Labor Cost %',
                    data: data.map(d => d.labor_cost_percentage),
                    backgroundColor: '#4ecdc4'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        stacked: true
                    },
                    y: {
                        stacked: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                }
            }
        });
    }

    render_reports_table(data) {
        const tbody = $('#reports-table-body');
        
        if (!data.length) {
            tbody.html('<tr><td colspan="6" class="text-muted text-center">No reports available</td></tr>');
            return;
        }

        let html = '';
        data.slice(0, 10).forEach(report => {
            const primeCostClass = report.prime_cost_percentage <= 60 ? 'text-success' : 
                                   report.prime_cost_percentage <= 65 ? 'text-warning' : 'text-danger';
            
            html += `
                <tr onclick="frappe.set_route('Form', 'Prime Cost Report', '${report.name || ''}')" style="cursor: pointer;">
                    <td>${report.from_date} - ${report.to_date}</td>
                    <td>${format_currency(report.total_sales || 0)}</td>
                    <td>${(report.food_cost_percentage || 0).toFixed(1)}%</td>
                    <td>${(report.labor_cost_percentage || 0).toFixed(1)}%</td>
                    <td class="${primeCostClass} font-weight-bold">${(report.prime_cost_percentage || 0).toFixed(1)}%</td>
                    <td><span class="badge bg-secondary">${report.status || 'N/A'}</span></td>
                </tr>
            `;
        });
        tbody.html(html);
    }

    render_empty_state() {
        this.wrapper.find('.dashboard-content').html(`
            <div class="text-center py-5">
                <i class="fa fa-chart-pie fa-4x text-muted mb-3"></i>
                <h4>No Prime Cost Data</h4>
                <p class="text-muted">Generate your first prime cost report to see analytics.</p>
                <button class="btn btn-primary" onclick="frappe.new_doc('Prime Cost Report')">
                    Create Prime Cost Report
                </button>
            </div>
        `);
    }

    generate_report() {
        const outlet = this.page.fields_dict.outlet.get_value();
        
        if (!outlet) {
            frappe.msgprint(__('Please select an outlet first'));
            return;
        }

        frappe.prompt([
            {
                fieldname: 'week_ending',
                label: __('Week Ending Date'),
                fieldtype: 'Date',
                default: frappe.datetime.get_today(),
                reqd: 1
            }
        ], (values) => {
            frappe.call({
                method: 'bookingzone.api.generate_prime_cost_report',
                args: {
                    outlet: outlet,
                    week_ending_date: values.week_ending
                },
                callback: (r) => {
                    if (r.message) {
                        frappe.msgprint(__('Report generated: {0}', [r.message]));
                        this.refresh();
                    }
                }
            });
        }, __('Generate Weekly Report'), __('Generate'));
    }
}
