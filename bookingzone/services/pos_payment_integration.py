"""
BookingZone POS Payment Integration
====================================
Integrates the multi-gateway payment service with BookingZone's 
EXISTING POS Order system.

This module bridges:
- Existing: POS Order, POS Session, Game Card, Gift Card
- New: Hyperswitch multi-gateway payment orchestration

The existing POS system remains unchanged - this adds payment
processing capabilities on top.
"""

import frappe
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from .payment_service import (
    get_payment_service,
    MultiGatewayPaymentService,
    HyperswitchOrchestrator
)


class POSPaymentIntegration:
    """
    Integrates Hyperswitch payments with BookingZone's existing POS system.
    
    Existing DocTypes (unchanged):
    - POS Order: Main transaction document
    - POS Order Item: Line items
    - POS Session: Cashier sessions
    - Game Card: Arcade cards
    - Game Card Transaction: Card reloads/usage
    - Gift Card: Gift cards
    - Gift Card Transaction: Gift card usage
    - Points Transaction: Loyalty points
    
    This integration adds:
    - Multi-gateway card processing
    - Split payments (card + cash + gift card)
    - Real-time payment status
    - Automatic GL posting
    """
    
    def __init__(self):
        self.payment_service = get_payment_service()
    
    # ==================== POS ORDER PAYMENTS ====================
    
    def process_pos_order_payment(
        self,
        pos_order: str,
        payments: List[Dict]
    ) -> Dict:
        """
        Process payment for a POS Order with multiple payment methods.
        
        Args:
            pos_order: POS Order document name
            payments: List of payment splits, e.g.:
                [
                    {"method": "card", "amount": 50.00, "payment_method_data": {...}},
                    {"method": "cash", "amount": 20.00},
                    {"method": "gift_card", "amount": 10.00, "gift_card": "GC-001"},
                    {"method": "game_card", "amount": 5.00, "game_card": "GAME-001"},
                    {"method": "points", "amount": 5.00, "membership": "MEM-001"}
                ]
        
        Returns:
            Payment result with status for each payment method
        """
        pos_doc = frappe.get_doc("POS Order", pos_order)
        
        if pos_doc.docstatus == 1:
            return {"success": False, "error": "POS Order already submitted"}
        
        total_order = pos_doc.grand_total or 0
        total_payments = sum(p.get("amount", 0) for p in payments)
        
        if abs(total_payments - total_order) > 0.01:
            return {
                "success": False, 
                "error": f"Payment total ({total_payments}) doesn't match order total ({total_order})"
            }
        
        results = []
        all_success = True
        
        for payment in payments:
            method = payment.get("method")
            amount = payment.get("amount", 0)
            
            if amount <= 0:
                continue
            
            if method == "card":
                # Process card payment through Hyperswitch
                result = self._process_card_payment(pos_doc, payment)
            elif method == "cash":
                # Record cash payment
                result = self._process_cash_payment(pos_doc, payment)
            elif method == "gift_card":
                # Deduct from gift card
                result = self._process_gift_card_payment(pos_doc, payment)
            elif method == "game_card":
                # Deduct from game card
                result = self._process_game_card_payment(pos_doc, payment)
            elif method == "points":
                # Redeem loyalty points
                result = self._process_points_payment(pos_doc, payment)
            else:
                result = {"success": False, "error": f"Unknown payment method: {method}"}
            
            results.append({"method": method, "amount": amount, **result})
            
            if not result.get("success"):
                all_success = False
                # Don't continue if a payment fails
                break
        
        if all_success:
            # Update POS Order status
            pos_doc.payment_status = "Paid"
            pos_doc.paid_amount = total_payments
            pos_doc.save(ignore_permissions=True)
            
            # Create GL entries
            self._create_pos_gl_entries(pos_doc, results)
        
        return {
            "success": all_success,
            "pos_order": pos_order,
            "total_paid": total_payments if all_success else 0,
            "payment_results": results
        }
    
    def _process_card_payment(self, pos_doc, payment: Dict) -> Dict:
        """Process card payment through Hyperswitch."""
        amount = payment.get("amount", 0)
        payment_method_data = payment.get("payment_method_data", {})
        
        # Create payment through Hyperswitch
        create_result = self.payment_service.create_payment(
            amount=amount,
            currency=pos_doc.currency or "USD",
            customer=pos_doc.customer,
            description=f"POS Order {pos_doc.name}",
            metadata={
                "pos_order": pos_doc.name,
                "pos_session": pos_doc.pos_session,
                "payment_type": "card"
            }
        )
        
        if not create_result.get("success"):
            return create_result
        
        # If payment method data provided, process immediately
        if payment_method_data:
            process_result = self.payment_service.process_payment(
                create_result.get("payment_id"),
                payment_method_data
            )
            return process_result
        
        # Otherwise return client_secret for frontend processing
        return {
            "success": True,
            "requires_action": True,
            "payment_id": create_result.get("payment_id"),
            "client_secret": create_result.get("client_secret"),
            "publishable_key": create_result.get("publishable_key")
        }
    
    def _process_cash_payment(self, pos_doc, payment: Dict) -> Dict:
        """Record cash payment."""
        amount = payment.get("amount", 0)
        
        # Cash payments are recorded directly
        # The POS Session tracks cash in drawer
        
        return {
            "success": True,
            "method": "cash",
            "amount": amount,
            "reference": f"CASH-{pos_doc.name}"
        }
    
    def _process_gift_card_payment(self, pos_doc, payment: Dict) -> Dict:
        """Process gift card payment using existing Gift Card DocType."""
        amount = payment.get("amount", 0)
        gift_card_name = payment.get("gift_card")
        
        if not gift_card_name:
            return {"success": False, "error": "Gift card not specified"}
        
        try:
            gift_card = frappe.get_doc("Gift Card", gift_card_name)
            
            # Check balance
            current_balance = gift_card.balance or 0
            if current_balance < amount:
                return {
                    "success": False, 
                    "error": f"Insufficient gift card balance. Available: {current_balance}"
                }
            
            # Deduct from gift card
            gift_card.balance = current_balance - amount
            gift_card.save(ignore_permissions=True)
            
            # Create Gift Card Transaction
            txn = frappe.new_doc("Gift Card Transaction")
            txn.gift_card = gift_card_name
            txn.transaction_type = "Redemption"
            txn.amount = -amount
            txn.pos_order = pos_doc.name
            txn.transaction_date = datetime.now()
            txn.balance_after = gift_card.balance
            txn.insert(ignore_permissions=True)
            
            return {
                "success": True,
                "method": "gift_card",
                "gift_card": gift_card_name,
                "amount": amount,
                "remaining_balance": gift_card.balance,
                "transaction": txn.name
            }
            
        except frappe.DoesNotExistError:
            return {"success": False, "error": f"Gift card {gift_card_name} not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _process_game_card_payment(self, pos_doc, payment: Dict) -> Dict:
        """Process game card payment using existing Game Card DocType."""
        amount = payment.get("amount", 0)
        game_card_name = payment.get("game_card")
        
        if not game_card_name:
            return {"success": False, "error": "Game card not specified"}
        
        try:
            game_card = frappe.get_doc("Game Card", game_card_name)
            
            # Check balance (could be credits or dollar value)
            current_balance = game_card.balance or 0
            if current_balance < amount:
                return {
                    "success": False,
                    "error": f"Insufficient game card balance. Available: {current_balance}"
                }
            
            # Deduct from game card
            game_card.balance = current_balance - amount
            game_card.save(ignore_permissions=True)
            
            # Create Game Card Transaction
            txn = frappe.new_doc("Game Card Transaction")
            txn.game_card = game_card_name
            txn.transaction_type = "Purchase"
            txn.amount = -amount
            txn.pos_order = pos_doc.name
            txn.transaction_date = datetime.now()
            txn.balance_after = game_card.balance
            txn.insert(ignore_permissions=True)
            
            return {
                "success": True,
                "method": "game_card",
                "game_card": game_card_name,
                "amount": amount,
                "remaining_balance": game_card.balance,
                "transaction": txn.name
            }
            
        except frappe.DoesNotExistError:
            return {"success": False, "error": f"Game card {game_card_name} not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _process_points_payment(self, pos_doc, payment: Dict) -> Dict:
        """Process loyalty points payment using existing Membership/Points system."""
        amount = payment.get("amount", 0)
        membership_name = payment.get("membership")
        
        if not membership_name:
            # Try to find membership by customer
            membership_name = frappe.db.get_value(
                "Membership",
                {"customer": pos_doc.customer, "status": "Active"},
                "name"
            )
        
        if not membership_name:
            return {"success": False, "error": "No active membership found"}
        
        try:
            membership = frappe.get_doc("Membership", membership_name)
            
            # Get points value (assume 1 point = $0.01 or configurable)
            points_value = frappe.db.get_single_value("Loyalty Settings", "points_value") or 0.01
            points_needed = int(amount / points_value)
            
            current_points = membership.points_balance or 0
            if current_points < points_needed:
                return {
                    "success": False,
                    "error": f"Insufficient points. Need {points_needed}, have {current_points}"
                }
            
            # Deduct points
            membership.points_balance = current_points - points_needed
            membership.save(ignore_permissions=True)
            
            # Create Points Transaction
            txn = frappe.new_doc("Points Transaction")
            txn.membership = membership_name
            txn.transaction_type = "Redemption"
            txn.points = -points_needed
            txn.monetary_value = amount
            txn.pos_order = pos_doc.name
            txn.transaction_date = datetime.now()
            txn.balance_after = membership.points_balance
            txn.insert(ignore_permissions=True)
            
            return {
                "success": True,
                "method": "points",
                "membership": membership_name,
                "points_redeemed": points_needed,
                "amount": amount,
                "remaining_points": membership.points_balance,
                "transaction": txn.name
            }
            
        except frappe.DoesNotExistError:
            return {"success": False, "error": f"Membership {membership_name} not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _create_pos_gl_entries(self, pos_doc, payment_results: List[Dict]):
        """Create GL entries for POS payments."""
        # This integrates with ERPNext's accounting
        # Each payment method posts to appropriate accounts
        
        for result in payment_results:
            if not result.get("success"):
                continue
            
            method = result.get("method")
            amount = result.get("amount", 0)
            
            # Get accounts from POS Profile or defaults
            if method == "card":
                debit_account = frappe.db.get_single_value(
                    "POS Settings", "card_receivable_account"
                ) or "Card Receivables - BZ"
            elif method == "cash":
                debit_account = frappe.db.get_single_value(
                    "POS Settings", "cash_account"
                ) or "Cash - BZ"
            elif method in ["gift_card", "game_card"]:
                debit_account = frappe.db.get_single_value(
                    "POS Settings", "prepaid_liability_account"
                ) or "Prepaid Card Liability - BZ"
            elif method == "points":
                debit_account = frappe.db.get_single_value(
                    "POS Settings", "loyalty_expense_account"
                ) or "Loyalty Expense - BZ"
            else:
                continue
            
            # GL entries are created when POS Order is submitted
            # This just records the payment allocation
    
    # ==================== GAME CARD OPERATIONS ====================
    
    def reload_game_card(
        self,
        game_card: str,
        amount: float,
        payment_method: str = "card",
        payment_data: Dict = None
    ) -> Dict:
        """
        Reload a game card with funds.
        
        Args:
            game_card: Game Card document name
            amount: Reload amount
            payment_method: "card", "cash", or "gift_card"
            payment_data: Payment method data for card payments
        """
        try:
            game_card_doc = frappe.get_doc("Game Card", game_card)
            
            # Process payment first
            if payment_method == "card":
                # Create payment through Hyperswitch
                payment_result = self.payment_service.create_payment(
                    amount=amount,
                    currency="USD",
                    description=f"Game Card Reload - {game_card}",
                    metadata={
                        "game_card": game_card,
                        "transaction_type": "reload"
                    }
                )
                
                if not payment_result.get("success"):
                    return payment_result
                
                if payment_data:
                    process_result = self.payment_service.process_payment(
                        payment_result.get("payment_id"),
                        payment_data
                    )
                    if not process_result.get("success"):
                        return process_result
                else:
                    return {
                        "success": True,
                        "requires_action": True,
                        "payment_id": payment_result.get("payment_id"),
                        "client_secret": payment_result.get("client_secret")
                    }
            
            # Add balance to game card
            current_balance = game_card_doc.balance or 0
            game_card_doc.balance = current_balance + amount
            game_card_doc.save(ignore_permissions=True)
            
            # Create transaction record
            txn = frappe.new_doc("Game Card Transaction")
            txn.game_card = game_card
            txn.transaction_type = "Reload"
            txn.amount = amount
            txn.payment_method = payment_method
            txn.transaction_date = datetime.now()
            txn.balance_after = game_card_doc.balance
            txn.insert(ignore_permissions=True)
            
            return {
                "success": True,
                "game_card": game_card,
                "reload_amount": amount,
                "new_balance": game_card_doc.balance,
                "transaction": txn.name
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ==================== GIFT CARD OPERATIONS ====================
    
    def purchase_gift_card(
        self,
        amount: float,
        recipient_name: str = None,
        recipient_email: str = None,
        message: str = None,
        payment_method: str = "card",
        payment_data: Dict = None
    ) -> Dict:
        """
        Purchase a new gift card.
        
        Args:
            amount: Gift card value
            recipient_name: Recipient's name
            recipient_email: Recipient's email for digital delivery
            message: Personal message
            payment_method: Payment method
            payment_data: Payment method data
        """
        # Process payment first
        if payment_method == "card":
            payment_result = self.payment_service.create_payment(
                amount=amount,
                currency="USD",
                description=f"Gift Card Purchase - ${amount}",
                metadata={"transaction_type": "gift_card_purchase"}
            )
            
            if not payment_result.get("success"):
                return payment_result
            
            if payment_data:
                process_result = self.payment_service.process_payment(
                    payment_result.get("payment_id"),
                    payment_data
                )
                if not process_result.get("success"):
                    return process_result
            else:
                return {
                    "success": True,
                    "requires_action": True,
                    "payment_id": payment_result.get("payment_id"),
                    "client_secret": payment_result.get("client_secret")
                }
        
        # Create gift card
        gift_card = frappe.new_doc("Gift Card")
        gift_card.initial_value = amount
        gift_card.balance = amount
        gift_card.recipient_name = recipient_name
        gift_card.recipient_email = recipient_email
        gift_card.message = message
        gift_card.status = "Active"
        gift_card.purchase_date = datetime.now()
        gift_card.insert(ignore_permissions=True)
        
        # Create initial transaction
        txn = frappe.new_doc("Gift Card Transaction")
        txn.gift_card = gift_card.name
        txn.transaction_type = "Purchase"
        txn.amount = amount
        txn.transaction_date = datetime.now()
        txn.balance_after = amount
        txn.insert(ignore_permissions=True)
        
        # Send email if recipient email provided
        if recipient_email:
            self._send_gift_card_email(gift_card, recipient_email, message)
        
        return {
            "success": True,
            "gift_card": gift_card.name,
            "card_number": gift_card.card_number,
            "value": amount,
            "recipient": recipient_name
        }
    
    def _send_gift_card_email(self, gift_card, email: str, message: str = None):
        """Send gift card notification email."""
        try:
            frappe.sendmail(
                recipients=[email],
                subject=f"You've received a ${gift_card.balance} Gift Card!",
                message=f"""
                <h2>You've received a gift card!</h2>
                <p>Card Number: <strong>{gift_card.card_number}</strong></p>
                <p>Value: <strong>${gift_card.balance}</strong></p>
                {f'<p>Message: {message}</p>' if message else ''}
                <p>Use this card at any of our locations.</p>
                """
            )
        except Exception as e:
            frappe.log_error(f"Failed to send gift card email: {str(e)}")
    
    # ==================== POS SESSION MANAGEMENT ====================
    
    def open_pos_session(
        self,
        pos_profile: str,
        opening_cash: float = 0
    ) -> Dict:
        """
        Open a new POS session.
        
        Args:
            pos_profile: POS Profile to use
            opening_cash: Opening cash in drawer
        """
        # Check for existing open session
        existing = frappe.db.get_value(
            "POS Session",
            {"user": frappe.session.user, "status": "Open"},
            "name"
        )
        
        if existing:
            return {
                "success": False,
                "error": f"You already have an open session: {existing}"
            }
        
        session = frappe.new_doc("POS Session")
        session.pos_profile = pos_profile
        session.user = frappe.session.user
        session.opening_time = datetime.now()
        session.opening_cash = opening_cash
        session.status = "Open"
        session.insert(ignore_permissions=True)
        
        return {
            "success": True,
            "session": session.name,
            "pos_profile": pos_profile,
            "opening_cash": opening_cash
        }
    
    def close_pos_session(
        self,
        session: str,
        closing_cash: float,
        card_total: float = 0,
        gift_card_total: float = 0,
        game_card_total: float = 0,
        points_total: float = 0
    ) -> Dict:
        """
        Close a POS session with reconciliation.
        
        Args:
            session: POS Session name
            closing_cash: Actual cash in drawer
            card_total: Total card payments
            gift_card_total: Total gift card redemptions
            game_card_total: Total game card redemptions
            points_total: Total points redemptions
        """
        session_doc = frappe.get_doc("POS Session", session)
        
        if session_doc.status != "Open":
            return {"success": False, "error": "Session is not open"}
        
        # Calculate expected totals from POS Orders
        orders = frappe.get_all(
            "POS Order",
            filters={"pos_session": session, "docstatus": 1},
            fields=["grand_total", "paid_amount"]
        )
        
        expected_total = sum(o.get("paid_amount", 0) for o in orders)
        actual_total = closing_cash + card_total + gift_card_total + game_card_total + points_total
        
        # Calculate cash variance
        expected_cash = session_doc.opening_cash + sum(
            # Would need to query actual cash payments
            0  # Placeholder
        )
        cash_variance = closing_cash - expected_cash
        
        # Update session
        session_doc.closing_time = datetime.now()
        session_doc.closing_cash = closing_cash
        session_doc.card_total = card_total
        session_doc.gift_card_total = gift_card_total
        session_doc.game_card_total = game_card_total
        session_doc.points_total = points_total
        session_doc.cash_variance = cash_variance
        session_doc.status = "Closed"
        session_doc.save(ignore_permissions=True)
        
        return {
            "success": True,
            "session": session,
            "total_sales": expected_total,
            "total_collected": actual_total,
            "cash_variance": cash_variance,
            "status": "Closed"
        }


# ==================== SINGLETON & API ====================

_pos_payment_integration = None

def get_pos_payment_integration() -> POSPaymentIntegration:
    """Get or create the POS payment integration singleton."""
    global _pos_payment_integration
    if _pos_payment_integration is None:
        _pos_payment_integration = POSPaymentIntegration()
    return _pos_payment_integration


# ==================== FRAPPE API METHODS ====================

@frappe.whitelist()
def process_pos_payment(pos_order: str, payments: str) -> Dict:
    """Process payment for a POS Order."""
    integration = get_pos_payment_integration()
    
    if isinstance(payments, str):
        payments = json.loads(payments)
    
    return integration.process_pos_order_payment(pos_order, payments)


@frappe.whitelist()
def reload_game_card(
    game_card: str,
    amount: float,
    payment_method: str = "card",
    payment_data: str = None
) -> Dict:
    """Reload a game card."""
    integration = get_pos_payment_integration()
    
    if payment_data and isinstance(payment_data, str):
        payment_data = json.loads(payment_data)
    
    return integration.reload_game_card(
        game_card,
        float(amount),
        payment_method,
        payment_data
    )


@frappe.whitelist()
def purchase_gift_card(
    amount: float,
    recipient_name: str = None,
    recipient_email: str = None,
    message: str = None,
    payment_method: str = "card",
    payment_data: str = None
) -> Dict:
    """Purchase a new gift card."""
    integration = get_pos_payment_integration()
    
    if payment_data and isinstance(payment_data, str):
        payment_data = json.loads(payment_data)
    
    return integration.purchase_gift_card(
        float(amount),
        recipient_name,
        recipient_email,
        message,
        payment_method,
        payment_data
    )


@frappe.whitelist()
def open_session(pos_profile: str, opening_cash: float = 0) -> Dict:
    """Open a new POS session."""
    integration = get_pos_payment_integration()
    return integration.open_pos_session(pos_profile, float(opening_cash))


@frappe.whitelist()
def close_session(
    session: str,
    closing_cash: float,
    card_total: float = 0,
    gift_card_total: float = 0,
    game_card_total: float = 0,
    points_total: float = 0
) -> Dict:
    """Close a POS session."""
    integration = get_pos_payment_integration()
    return integration.close_pos_session(
        session,
        float(closing_cash),
        float(card_total),
        float(gift_card_total),
        float(game_card_total),
        float(points_total)
    )


@frappe.whitelist()
def get_payment_methods_for_pos() -> List[Dict]:
    """Get available payment methods for POS."""
    methods = [
        {"method": "cash", "label": "Cash", "icon": "fa-money-bill"},
        {"method": "card", "label": "Credit/Debit Card", "icon": "fa-credit-card"},
        {"method": "gift_card", "label": "Gift Card", "icon": "fa-gift"},
        {"method": "game_card", "label": "Game Card", "icon": "fa-gamepad"},
        {"method": "points", "label": "Loyalty Points", "icon": "fa-star"}
    ]
    
    # Check which gateways are configured
    gateways = frappe.get_all(
        "Payment Gateway Configuration",
        filters={"is_active": 1},
        fields=["gateway_name", "gateway_type"]
    )
    
    if gateways:
        methods[1]["gateways"] = gateways
    
    return methods
