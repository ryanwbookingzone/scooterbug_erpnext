"""
Recipe DocType Controller
==========================
Manages recipe costing and food cost calculations.
Links to existing Menu Item DocType for menu integration.
"""

import frappe
from frappe.model.document import Document
from frappe import _


class Recipe(Document):
    def validate(self):
        self.calculate_costs()
        self.validate_ingredients()
    
    def before_save(self):
        self.update_menu_item_cost()
    
    def calculate_costs(self):
        """Calculate total ingredient cost and derived metrics."""
        total_cost = 0
        
        for ingredient in self.ingredients:
            # Get current item price
            if ingredient.item_code:
                item_price = self.get_ingredient_cost(
                    ingredient.item_code,
                    ingredient.quantity,
                    ingredient.uom
                )
                ingredient.cost = item_price
                total_cost += item_price
        
        self.total_ingredient_cost = total_cost
        
        # Calculate cost per portion
        if self.yield_quantity and self.yield_quantity > 0:
            self.cost_per_portion = total_cost / self.yield_quantity
        else:
            self.cost_per_portion = total_cost
        
        # Calculate food cost percentage and margin
        if self.selling_price and self.selling_price > 0:
            self.food_cost_percentage = (self.cost_per_portion / self.selling_price) * 100
            self.gross_margin = self.selling_price - self.cost_per_portion
        else:
            self.food_cost_percentage = 0
            self.gross_margin = 0
    
    def get_ingredient_cost(self, item_code, quantity, uom):
        """Get the cost of an ingredient based on current valuation."""
        # Try to get from Item Price first
        item_price = frappe.db.get_value(
            "Item Price",
            {
                "item_code": item_code,
                "buying": 1
            },
            "price_list_rate"
        )
        
        if not item_price:
            # Fall back to last purchase rate
            item_price = frappe.db.get_value("Item", item_code, "last_purchase_rate") or 0
        
        # Convert quantity to stock UOM if needed
        conversion_factor = self.get_uom_conversion(item_code, uom)
        
        return (item_price * quantity) / conversion_factor if conversion_factor else item_price * quantity
    
    def get_uom_conversion(self, item_code, uom):
        """Get UOM conversion factor."""
        stock_uom = frappe.db.get_value("Item", item_code, "stock_uom")
        
        if uom == stock_uom:
            return 1
        
        conversion = frappe.db.get_value(
            "UOM Conversion Detail",
            {"parent": item_code, "uom": uom},
            "conversion_factor"
        )
        
        return conversion or 1
    
    def validate_ingredients(self):
        """Validate that all ingredients exist."""
        for ingredient in self.ingredients:
            if ingredient.item_code:
                if not frappe.db.exists("Item", ingredient.item_code):
                    frappe.throw(
                        _("Item {0} does not exist").format(ingredient.item_code)
                    )
    
    def update_menu_item_cost(self):
        """Update linked Menu Item with recipe cost."""
        if self.menu_item:
            try:
                menu_item = frappe.get_doc("Menu Item", self.menu_item)
                if hasattr(menu_item, 'food_cost'):
                    menu_item.food_cost = self.cost_per_portion
                    menu_item.save(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(f"Failed to update Menu Item cost: {str(e)}")
    
    @frappe.whitelist()
    def recalculate_costs(self):
        """Recalculate costs based on current ingredient prices."""
        self.calculate_costs()
        self.save()
        return {
            "total_ingredient_cost": self.total_ingredient_cost,
            "cost_per_portion": self.cost_per_portion,
            "food_cost_percentage": self.food_cost_percentage,
            "gross_margin": self.gross_margin
        }
    
    @frappe.whitelist()
    def duplicate_recipe(self, new_name):
        """Create a copy of this recipe with a new name."""
        new_recipe = frappe.copy_doc(self)
        new_recipe.recipe_name = new_name
        new_recipe.status = "Draft"
        new_recipe.insert()
        return new_recipe.name


@frappe.whitelist()
def get_recipe_cost_breakdown(recipe_name):
    """Get detailed cost breakdown for a recipe."""
    recipe = frappe.get_doc("Recipe", recipe_name)
    
    breakdown = []
    for ingredient in recipe.ingredients:
        breakdown.append({
            "item_code": ingredient.item_code,
            "item_name": ingredient.item_name,
            "quantity": ingredient.quantity,
            "uom": ingredient.uom,
            "cost": ingredient.cost,
            "percentage": (ingredient.cost / recipe.total_ingredient_cost * 100) if recipe.total_ingredient_cost else 0
        })
    
    return {
        "recipe_name": recipe.recipe_name,
        "total_cost": recipe.total_ingredient_cost,
        "cost_per_portion": recipe.cost_per_portion,
        "selling_price": recipe.selling_price,
        "food_cost_percentage": recipe.food_cost_percentage,
        "gross_margin": recipe.gross_margin,
        "ingredients": breakdown
    }


@frappe.whitelist()
def bulk_update_recipe_costs():
    """Recalculate costs for all active recipes."""
    recipes = frappe.get_all(
        "Recipe",
        filters={"status": "Active"},
        pluck="name"
    )
    
    updated = 0
    for recipe_name in recipes:
        try:
            recipe = frappe.get_doc("Recipe", recipe_name)
            recipe.calculate_costs()
            recipe.save(ignore_permissions=True)
            updated += 1
        except Exception as e:
            frappe.log_error(f"Failed to update recipe {recipe_name}: {str(e)}")
    
    return {"updated": updated, "total": len(recipes)}
