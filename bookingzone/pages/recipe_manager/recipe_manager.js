/**
 * Recipe Manager Page
 * ====================
 * Visual recipe management with cost analysis and menu item linking.
 */

frappe.pages['recipe-manager'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Recipe Manager',
        single_column: true
    });

    // Add category filter
    page.add_field({
        fieldname: 'category',
        label: __('Category'),
        fieldtype: 'Link',
        options: 'Recipe Category',
        change: function() {
            page.manager.filter_recipes();
        }
    });

    // Add search
    page.add_field({
        fieldname: 'search',
        label: __('Search'),
        fieldtype: 'Data',
        change: function() {
            page.manager.filter_recipes();
        }
    });

    // Add new recipe button
    page.add_button(__('New Recipe'), function() {
        frappe.new_doc('Recipe');
    }, 'btn-primary');

    // Add recalculate costs button
    page.add_button(__('Recalculate All Costs'), function() {
        page.manager.recalculate_all_costs();
    });

    // Initialize manager
    page.manager = new RecipeManager(page);
};

class RecipeManager {
    constructor(page) {
        this.page = page;
        this.wrapper = $(page.body);
        this.recipes = [];
        this.init();
    }

    init() {
        this.render_skeleton();
        this.load_recipes();
    }

    render_skeleton() {
        this.wrapper.html(`
            <div class="recipe-manager">
                <!-- Summary Cards -->
                <div class="row mb-4">
                    <div class="col-lg-3 col-md-6 mb-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h3 class="mb-0" id="total-recipes">0</h3>
                                <small class="text-muted">Total Recipes</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-lg-3 col-md-6 mb-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h3 class="mb-0" id="avg-food-cost">0%</h3>
                                <small class="text-muted">Avg Food Cost %</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-lg-3 col-md-6 mb-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h3 class="mb-0" id="high-cost-count">0</h3>
                                <small class="text-muted">High Cost Recipes</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-lg-3 col-md-6 mb-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h3 class="mb-0" id="linked-menu-items">0</h3>
                                <small class="text-muted">Linked Menu Items</small>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Recipe Grid -->
                <div class="recipe-grid" id="recipe-grid">
                    <div class="text-center py-5">
                        <div class="spinner-border text-primary" role="status"></div>
                        <p class="mt-3 text-muted">Loading recipes...</p>
                    </div>
                </div>
            </div>

            <style>
                .recipe-manager .recipe-card {
                    border: 1px solid #dee2e6;
                    border-radius: 12px;
                    overflow: hidden;
                    transition: all 0.2s;
                    cursor: pointer;
                    height: 100%;
                }
                .recipe-manager .recipe-card:hover {
                    border-color: #5e64ff;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                    transform: translateY(-2px);
                }
                .recipe-manager .recipe-card .recipe-image {
                    height: 150px;
                    background-color: #f8f9fa;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 3rem;
                    color: #dee2e6;
                }
                .recipe-manager .recipe-card .recipe-image img {
                    width: 100%;
                    height: 100%;
                    object-fit: cover;
                }
                .recipe-manager .recipe-card .recipe-body {
                    padding: 16px;
                }
                .recipe-manager .recipe-card .recipe-name {
                    font-weight: 600;
                    font-size: 1.1rem;
                    margin-bottom: 4px;
                }
                .recipe-manager .recipe-card .recipe-category {
                    font-size: 0.85rem;
                    color: #6c757d;
                }
                .recipe-manager .recipe-card .cost-badge {
                    display: inline-block;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 0.85rem;
                    font-weight: 600;
                }
                .recipe-manager .recipe-card .cost-badge.good {
                    background-color: #d4edda;
                    color: #155724;
                }
                .recipe-manager .recipe-card .cost-badge.warning {
                    background-color: #fff3cd;
                    color: #856404;
                }
                .recipe-manager .recipe-card .cost-badge.danger {
                    background-color: #f8d7da;
                    color: #721c24;
                }
            </style>
        `);
    }

    load_recipes() {
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Recipe',
                fields: [
                    'name', 'recipe_name', 'category', 'total_cost', 
                    'selling_price', 'food_cost_percentage', 'yield_quantity',
                    'yield_unit', 'is_active', 'menu_item', 'image'
                ],
                filters: {is_active: 1},
                limit_page_length: 0
            },
            callback: (r) => {
                if (r.message) {
                    this.recipes = r.message;
                    this.render_recipes();
                    this.update_stats();
                }
            }
        });
    }

    render_recipes() {
        const container = $('#recipe-grid');
        const category = this.page.fields_dict.category.get_value();
        const search = (this.page.fields_dict.search.get_value() || '').toLowerCase();

        let filteredRecipes = this.recipes;

        if (category) {
            filteredRecipes = filteredRecipes.filter(r => r.category === category);
        }

        if (search) {
            filteredRecipes = filteredRecipes.filter(r => 
                (r.recipe_name || '').toLowerCase().includes(search) ||
                (r.name || '').toLowerCase().includes(search)
            );
        }

        if (!filteredRecipes.length) {
            container.html(`
                <div class="text-center py-5 text-muted">
                    <i class="fa fa-utensils fa-3x mb-3"></i>
                    <p>No recipes found</p>
                    <button class="btn btn-primary" onclick="frappe.new_doc('Recipe')">
                        Create First Recipe
                    </button>
                </div>
            `);
            return;
        }

        let html = '<div class="row">';
        filteredRecipes.forEach(recipe => {
            const foodCostPct = recipe.food_cost_percentage || 0;
            let costClass = 'good';
            if (foodCostPct > 35) costClass = 'danger';
            else if (foodCostPct > 30) costClass = 'warning';

            html += `
                <div class="col-lg-3 col-md-4 col-sm-6 mb-4">
                    <div class="recipe-card" onclick="frappe.set_route('Form', 'Recipe', '${recipe.name}')">
                        <div class="recipe-image">
                            ${recipe.image 
                                ? `<img src="${recipe.image}" alt="${recipe.recipe_name}">`
                                : '<i class="fa fa-utensils"></i>'
                            }
                        </div>
                        <div class="recipe-body">
                            <div class="recipe-name">${recipe.recipe_name}</div>
                            <div class="recipe-category">${recipe.category || 'Uncategorized'}</div>
                            <div class="d-flex justify-content-between align-items-center mt-3">
                                <div>
                                    <small class="text-muted">Cost</small>
                                    <div class="font-weight-bold">${format_currency(recipe.total_cost || 0)}</div>
                                </div>
                                <div>
                                    <small class="text-muted">Sells</small>
                                    <div class="font-weight-bold">${format_currency(recipe.selling_price || 0)}</div>
                                </div>
                                <span class="cost-badge ${costClass}">${foodCostPct.toFixed(1)}%</span>
                            </div>
                            ${recipe.menu_item 
                                ? `<div class="mt-2"><span class="badge bg-info">Linked to Menu</span></div>`
                                : ''
                            }
                        </div>
                    </div>
                </div>
            `;
        });
        html += '</div>';

        container.html(html);
    }

    filter_recipes() {
        this.render_recipes();
    }

    update_stats() {
        const total = this.recipes.length;
        const avgCost = this.recipes.reduce((sum, r) => sum + (r.food_cost_percentage || 0), 0) / (total || 1);
        const highCost = this.recipes.filter(r => (r.food_cost_percentage || 0) > 35).length;
        const linked = this.recipes.filter(r => r.menu_item).length;

        $('#total-recipes').text(total);
        $('#avg-food-cost').text(avgCost.toFixed(1) + '%');
        $('#high-cost-count').text(highCost);
        $('#linked-menu-items').text(linked);
    }

    recalculate_all_costs() {
        frappe.call({
            method: 'bookingzone.api.update_all_recipe_costs',
            callback: (r) => {
                if (r.message) {
                    frappe.msgprint({
                        title: __('Success'),
                        message: __('Updated {0} recipes', [r.message.updated]),
                        indicator: 'green'
                    });
                    this.load_recipes();
                }
            }
        });
    }
}
