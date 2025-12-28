"""
Payment Transaction DocType Controller
=======================================
Handles payment transaction lifecycle with multi-processor support.
"""

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, flt
import json


class PaymentTransaction(Document):
    """
    Payment Transaction document for tracking payments across multiple processors.
    Integrates with Hyperswitch for payment orchestration.
    """
    
    def validate(self):
        """Validate the payment transaction."""
        self.validate_amount()
        self.calculate_net_amount()
    
    def validate_amount(self):
        """Ensure amount is positive."""
        if self.amount and flt(self.amount) <= 0:
            frappe.throw("Amount must be greater than zero")
    
    def calculate_net_amount(self):
        """Calculate net amount after fees."""
        if self.amount:
            self.net_amount = flt(self.amount) - flt(self.fee_amount or 0)
    
    def before_insert(self):
        """Set defaults before insert."""
        if not self.created_at:
            self.created_at = now_datetime()
    
    @frappe.whitelist()
    def process(self, payment_method_data: dict = None):
        """
        Process the payment through the selected processor.
        
        Args:
            payment_method_data: Payment method details (card, bank, etc.)
        """
        if self.status not in ["Pending", "Processing"]:
            frappe.throw(f"Cannot process payment in {self.status} status")
        
        from bookingzone.services.payment_service import get_payment_service
        
        service = get_payment_service()
        result = service.process_payment(self.name, payment_method_data or {})
        
        if result.get("success"):
            frappe.msgprint(
                f"Payment processed successfully. Transaction ID: {result.get('transaction_id')}",
                indicator="green",
                title="Payment Success"
            )
        else:
            frappe.throw(f"Payment failed: {result.get('error', 'Unknown error')}")
        
        return result
    
    @frappe.whitelist()
    def refund(self, amount: float = None, reason: str = None):
        """
        Refund the payment.
        
        Args:
            amount: Refund amount (full refund if not specified)
            reason: Refund reason
        """
        if self.status not in ["Succeeded", "Partially Refunded"]:
            frappe.throw(f"Cannot refund payment in {self.status} status")
        
        from bookingzone.services.payment_service import get_payment_service
        
        service = get_payment_service()
        result = service.refund_payment(
            self.name,
            amount=flt(amount) if amount else None,
            reason=reason
        )
        
        if result.get("success"):
            self.refund_reason = reason
            self.refund_date = now_datetime()
            self.save()
            
            frappe.msgprint(
                f"Refund of {result.get('amount')} processed successfully",
                indicator="green",
                title="Refund Success"
            )
        else:
            frappe.throw(f"Refund failed: {result.get('error', 'Unknown error')}")
        
        return result
    
    @frappe.whitelist()
    def cancel(self):
        """Cancel a pending payment."""
        if self.status not in ["Pending", "Processing"]:
            frappe.throw(f"Cannot cancel payment in {self.status} status")
        
        self.status = "Cancelled"
        self.save()
        
        frappe.msgprint("Payment cancelled", indicator="orange")
    
    @frappe.whitelist()
    def sync_status(self):
        """Sync payment status from the gateway."""
        if not self.hyperswitch_payment_id:
            frappe.throw("No Hyperswitch payment ID to sync")
        
        from bookingzone.services.payment_service import HyperswitchClient
        
        client = HyperswitchClient()
        result = client.get_payment(self.hyperswitch_payment_id)
        
        if not result.get("error"):
            old_status = self.status
            self.status = self._map_status(result.get("status"))
            self.gateway_response = json.dumps(result)
            
            if result.get("payment_method_data"):
                pm_data = result.get("payment_method_data", {})
                if pm_data.get("card"):
                    card = pm_data["card"]
                    self.card_brand = card.get("card_network")
                    self.card_last_four = card.get("last4_digits")
                    self.card_exp_month = card.get("card_exp_month")
                    self.card_exp_year = card.get("card_exp_year")
            
            self.save()
            
            if old_status != self.status:
                frappe.msgprint(
                    f"Payment status updated: {old_status} → {self.status}",
                    indicator="blue",
                    title="Status Updated"
                )
        else:
            frappe.throw(f"Failed to sync status: {result.get('error')}")
    
    def _map_status(self, hyperswitch_status: str) -> str:
        """Map Hyperswitch status to internal status."""
        mapping = {
            "requires_payment_method": "Pending",
            "requires_confirmation": "Pending",
            "requires_action": "Processing",
            "processing": "Processing",
            "succeeded": "Succeeded",
            "failed": "Failed",
            "cancelled": "Cancelled"
        }
        return mapping.get(hyperswitch_status, "Pending")


@frappe.whitelist()
def get_payment_link(sales_invoice: str) -> dict:
    """
    Generate a payment link for a Sales Invoice.
    
    Args:
        sales_invoice: Sales Invoice name
        
    Returns:
        Dict with payment link details
    """
    invoice = frappe.get_doc("Sales Invoice", sales_invoice)
    
    if invoice.outstanding_amount <= 0:
        return {"success": False, "error": "Invoice already paid"}
    
    from bookingzone.services.payment_service import get_payment_service
    
    service = get_payment_service()
    result = service.create_payment(
        amount=invoice.outstanding_amount,
        currency=invoice.currency,
        customer=invoice.customer,
        sales_invoice=sales_invoice
    )
    
    if result.get("success"):
        # Generate payment link URL
        site_url = frappe.utils.get_url()
        payment_link = f"{site_url}/pay/{result.get('payment_id')}"
        
        # Update invoice with payment link
        frappe.db.set_value("Sales Invoice", sales_invoice, {
            "custom_payment_link": payment_link,
            "custom_payment_transaction": result.get("payment_id")
        })
        
        return {
            "success": True,
            "payment_link": payment_link,
            "payment_id": result.get("payment_id"),
            "client_secret": result.get("client_secret")
        }
    
    return result


@frappe.whitelist()
def process_webhook(payload: str, signature: str = None) -> dict:
    """
    Process payment webhook from Hyperswitch or direct processors.
    
    Args:
        payload: Webhook payload JSON
        signature: Webhook signature for verification
        
    Returns:
        Processing result
    """
    try:
        data = json.loads(payload) if isinstance(payload, str) else payload
        
        event_type = data.get("event_type") or data.get("type")
        payment_id = data.get("payment_id") or data.get("data", {}).get("object", {}).get("id")
        
        if not payment_id:
            return {"success": False, "error": "No payment ID in webhook"}
        
        # Find payment transaction
        payment_name = frappe.db.get_value(
            "Payment Transaction",
            {"hyperswitch_payment_id": payment_id},
            "name"
        ) or frappe.db.get_value(
            "Payment Transaction",
            {"transaction_id": payment_id},
            "name"
        )
        
        if not payment_name:
            frappe.log_error(f"Payment not found for webhook: {payment_id}", "Payment Webhook")
            return {"success": False, "error": "Payment not found"}
        
        payment_doc = frappe.get_doc("Payment Transaction", payment_name)
        
        # Update status based on event
        if event_type in ["payment_succeeded", "payment.succeeded", "charge.succeeded"]:
            payment_doc.status = "Succeeded"
            payment_doc.completed_at = now_datetime()
            
            # Create Payment Entry
            if payment_doc.sales_invoice and not payment_doc.payment_entry:
                try:
                    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
                    
                    pe = get_payment_entry("Sales Invoice", payment_doc.sales_invoice)
                    pe.reference_no = payment_doc.transaction_id or payment_doc.name
                    pe.reference_date = frappe.utils.today()
                    pe.insert()
                    pe.submit()
                    
                    payment_doc.payment_entry = pe.name
                except Exception as e:
                    frappe.log_error(f"Failed to create Payment Entry: {str(e)}", "Payment Webhook")
        
        elif event_type in ["payment_failed", "payment.failed", "charge.failed"]:
            payment_doc.status = "Failed"
            payment_doc.failure_reason = data.get("error", {}).get("message", "Payment failed")
        
        elif event_type in ["refund_succeeded", "refund.succeeded", "charge.refunded"]:
            refund_amount = data.get("amount", 0) / 100  # Convert from cents
            payment_doc.refund_amount = (payment_doc.refund_amount or 0) + refund_amount
            payment_doc.refund_date = now_datetime()
            
            if payment_doc.refund_amount >= payment_doc.amount:
                payment_doc.status = "Refunded"
            else:
                payment_doc.status = "Partially Refunded"
        
        payment_doc.gateway_response = json.dumps(data)
        payment_doc.save(ignore_permissions=True)
        frappe.db.commit()
        
        return {"success": True, "status": payment_doc.status}
        
    except Exception as e:
        frappe.log_error(f"Webhook processing error: {str(e)}", "Payment Webhook")
        return {"success": False, "error": str(e)}
