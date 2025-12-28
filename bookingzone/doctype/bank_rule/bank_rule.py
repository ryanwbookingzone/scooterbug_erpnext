"""
Bank Rule DocType Controller
=============================
Auto-categorization rules for bank transactions.
Similar to QuickBooks Online bank rules functionality.
"""

import frappe
import re
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, now_datetime


class BankRule(Document):
    def validate(self):
        self.validate_match_value()
        self.validate_amounts()
    
    def validate_match_value(self):
        """Validate match value, especially for regex."""
        if self.match_type == "Regex":
            try:
                re.compile(self.match_value)
            except re.error as e:
                frappe.throw(_("Invalid regex pattern: {0}").format(str(e)))
    
    def validate_amounts(self):
        """Validate amount range."""
        if self.min_amount and self.max_amount:
            if flt(self.min_amount) > flt(self.max_amount):
                frappe.throw(_("Minimum amount cannot be greater than maximum amount"))
    
    def matches_transaction(self, transaction):
        """
        Check if this rule matches a bank transaction.
        
        Args:
            transaction: dict with keys: description, reference_number, 
                        party_name, amount, transaction_type
        
        Returns:
            bool: True if rule matches
        """
        # Check transaction type
        if self.transaction_type:
            if transaction.get("transaction_type") != self.transaction_type:
                return False
        
        # Check amount range
        amount = abs(flt(transaction.get("amount", 0)))
        if self.min_amount and amount < flt(self.min_amount):
            return False
        if self.max_amount and amount > flt(self.max_amount):
            return False
        
        # Get field value to match
        field_map = {
            "Description": "description",
            "Reference Number": "reference_number",
            "Party Name": "party_name"
        }
        field_key = field_map.get(self.match_field, "description")
        field_value = (transaction.get(field_key) or "").lower()
        match_value = (self.match_value or "").lower()
        
        # Apply match type
        if self.match_type == "Contains":
            return match_value in field_value
        elif self.match_type == "Starts With":
            return field_value.startswith(match_value)
        elif self.match_type == "Ends With":
            return field_value.endswith(match_value)
        elif self.match_type == "Exact Match":
            return field_value == match_value
        elif self.match_type == "Regex":
            try:
                return bool(re.search(self.match_value, field_value, re.IGNORECASE))
            except:
                return False
        
        return False
    
    def apply_to_transaction(self, bank_transaction_name):
        """
        Apply this rule to a bank transaction.
        
        Args:
            bank_transaction_name: Name of Bank Transaction document
        
        Returns:
            dict: Result of applying the rule
        """
        bt = frappe.get_doc("Bank Transaction", bank_transaction_name)
        
        result = {
            "rule": self.name,
            "action": self.action_type,
            "applied": False
        }
        
        if self.action_type == "Categorize":
            # Update bank transaction with categorization
            if self.account:
                bt.expense_account = self.account
            if self.cost_center:
                bt.cost_center = self.cost_center
            if self.party_type and self.party:
                bt.party_type = self.party_type
                bt.party = self.party
            
            bt.save(ignore_permissions=True)
            result["applied"] = True
            
        elif self.action_type == "Create Payment Entry":
            # Create Payment Entry
            pe = self._create_payment_entry(bt)
            if pe:
                result["payment_entry"] = pe.name
                result["applied"] = True
                
        elif self.action_type == "Create Journal Entry":
            # Create Journal Entry
            je = self._create_journal_entry(bt)
            if je:
                result["journal_entry"] = je.name
                result["applied"] = True
                
        elif self.action_type == "Link to Party":
            # Just link party
            if self.party_type and self.party:
                bt.party_type = self.party_type
                bt.party = self.party
                bt.save(ignore_permissions=True)
                result["applied"] = True
        
        # Update rule statistics
        if result["applied"]:
            self.times_matched = (self.times_matched or 0) + 1
            self.last_matched = now_datetime()
            self.total_amount_matched = flt(self.total_amount_matched) + abs(flt(bt.deposit or bt.withdrawal))
            self.save(ignore_permissions=True)
        
        return result
    
    def _create_payment_entry(self, bt):
        """Create Payment Entry from bank transaction."""
        try:
            pe = frappe.new_doc("Payment Entry")
            
            if bt.deposit:
                pe.payment_type = "Receive"
                pe.paid_amount = bt.deposit
                pe.received_amount = bt.deposit
            else:
                pe.payment_type = "Pay"
                pe.paid_amount = bt.withdrawal
                pe.received_amount = bt.withdrawal
            
            pe.party_type = self.party_type
            pe.party = self.party
            pe.posting_date = bt.date
            pe.reference_no = bt.reference_number
            pe.reference_date = bt.date
            pe.bank_transaction = bt.name
            
            # Get accounts
            pe.paid_from = bt.bank_account if bt.withdrawal else self.account
            pe.paid_to = self.account if bt.withdrawal else bt.bank_account
            
            pe.insert(ignore_permissions=True)
            return pe
            
        except Exception as e:
            frappe.log_error(f"Failed to create Payment Entry: {str(e)}")
            return None
    
    def _create_journal_entry(self, bt):
        """Create Journal Entry from bank transaction."""
        try:
            je = frappe.new_doc("Journal Entry")
            je.posting_date = bt.date
            je.cheque_no = bt.reference_number
            je.cheque_date = bt.date
            je.bank_transaction = bt.name
            
            amount = bt.deposit or bt.withdrawal
            
            # Debit entry
            je.append("accounts", {
                "account": self.account if bt.withdrawal else bt.bank_account,
                "debit_in_account_currency": amount,
                "cost_center": self.cost_center
            })
            
            # Credit entry
            je.append("accounts", {
                "account": bt.bank_account if bt.withdrawal else self.account,
                "credit_in_account_currency": amount,
                "cost_center": self.cost_center
            })
            
            je.insert(ignore_permissions=True)
            return je
            
        except Exception as e:
            frappe.log_error(f"Failed to create Journal Entry: {str(e)}")
            return None


@frappe.whitelist()
def apply_rules_to_transaction(bank_transaction_name):
    """
    Apply all matching rules to a bank transaction.
    
    Args:
        bank_transaction_name: Name of Bank Transaction document
    
    Returns:
        dict: Results of rule application
    """
    bt = frappe.get_doc("Bank Transaction", bank_transaction_name)
    
    # Build transaction dict for matching
    transaction = {
        "description": bt.description,
        "reference_number": bt.reference_number,
        "party_name": bt.party,
        "amount": bt.deposit or bt.withdrawal,
        "transaction_type": "Credit" if bt.deposit else "Debit"
    }
    
    # Get all active rules, ordered by priority
    rules = frappe.get_all(
        "Bank Rule",
        filters={"is_active": 1},
        fields=["name"],
        order_by="priority asc"
    )
    
    results = []
    
    for rule_data in rules:
        rule = frappe.get_doc("Bank Rule", rule_data.name)
        
        # Check bank account filter
        if rule.bank_account and rule.bank_account != bt.bank_account:
            continue
        
        if rule.matches_transaction(transaction):
            result = rule.apply_to_transaction(bank_transaction_name)
            results.append(result)
            
            # Stop after first match (rules are prioritized)
            if result.get("applied"):
                break
    
    return {
        "transaction": bank_transaction_name,
        "rules_checked": len(rules),
        "results": results
    }


@frappe.whitelist()
def bulk_apply_rules(bank_account=None, from_date=None, to_date=None):
    """
    Apply rules to multiple unreconciled bank transactions.
    
    Args:
        bank_account: Optional bank account filter
        from_date: Optional start date
        to_date: Optional end date
    
    Returns:
        dict: Summary of rule applications
    """
    filters = {
        "docstatus": 1,
        "status": ["in", ["Pending", "Unreconciled"]]
    }
    
    if bank_account:
        filters["bank_account"] = bank_account
    if from_date:
        filters["date"] = [">=", from_date]
    if to_date:
        filters["date"] = ["<=", to_date]
    
    transactions = frappe.get_all(
        "Bank Transaction",
        filters=filters,
        pluck="name"
    )
    
    applied = 0
    errors = 0
    
    for bt_name in transactions:
        try:
            result = apply_rules_to_transaction(bt_name)
            if any(r.get("applied") for r in result.get("results", [])):
                applied += 1
        except Exception as e:
            errors += 1
            frappe.log_error(f"Error applying rules to {bt_name}: {str(e)}")
    
    return {
        "total_transactions": len(transactions),
        "rules_applied": applied,
        "errors": errors
    }


@frappe.whitelist()
def suggest_rule_from_transaction(bank_transaction_name):
    """
    Suggest a bank rule based on a transaction.
    
    Args:
        bank_transaction_name: Name of Bank Transaction document
    
    Returns:
        dict: Suggested rule parameters
    """
    bt = frappe.get_doc("Bank Transaction", bank_transaction_name)
    
    # Extract key words from description
    description = bt.description or ""
    words = description.split()
    
    # Find most distinctive word (not common words)
    common_words = {"the", "a", "an", "to", "from", "for", "of", "in", "on", "at", "by"}
    distinctive_words = [w for w in words if w.lower() not in common_words and len(w) > 3]
    
    suggested_match = distinctive_words[0] if distinctive_words else description[:20]
    
    return {
        "rule_name": f"Rule for {suggested_match}",
        "match_type": "Contains",
        "match_field": "Description",
        "match_value": suggested_match,
        "transaction_type": "Credit" if bt.deposit else "Debit",
        "sample_amount": bt.deposit or bt.withdrawal,
        "sample_description": description
    }
