"""
Expense Receipt DocType Controller
===================================
Handles receipt processing with PaddleOCR integration.
"""

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, flt
import json


class ExpenseReceipt(Document):
    """
    Expense Receipt document with OCR processing capabilities.
    Uses PaddleOCR for automatic field extraction from receipt images.
    """
    
    def validate(self):
        """Validate the expense receipt."""
        self.validate_amount()
        self.set_status()
    
    def validate_amount(self):
        """Ensure amount is positive."""
        if self.amount and flt(self.amount) <= 0:
            frappe.throw("Amount must be greater than zero")
    
    def set_status(self):
        """Set status based on document state."""
        if not self.status:
            self.status = "Draft"
    
    def after_insert(self):
        """Process OCR after document is inserted."""
        if self.receipt_image and not self.ocr_extracted_data:
            self.process_ocr()
    
    def on_update(self):
        """Process OCR if image is updated."""
        if self.has_value_changed("receipt_image") and self.receipt_image:
            self.process_ocr()
    
    @frappe.whitelist()
    def process_ocr(self):
        """
        Process the receipt image using PaddleOCR.
        Extracts vendor, amount, date, and other fields.
        """
        if not self.receipt_image:
            frappe.throw("Please upload a receipt image first")
        
        self.ocr_status = "Processing"
        self.save(ignore_permissions=True)
        
        try:
            from bookingzone.services.ocr_service import process_receipt
            
            result = process_receipt(self.receipt_image)
            
            if result.get("success"):
                fields = result.get("fields", {})
                
                # Store raw OCR data
                self.ocr_extracted_data = json.dumps(fields, indent=2)
                self.ocr_confidence = flt(fields.get("confidence", 0)) * 100
                self.ocr_engine = fields.get("engine", "PaddleOCR")
                self.ocr_status = "Completed"
                self.ocr_processed_at = now_datetime()
                
                # Auto-populate fields if empty
                if not self.amount and fields.get("total_amount"):
                    self.amount = flt(fields.get("total_amount"))
                
                if not self.tax_amount and fields.get("tax_amount"):
                    self.tax_amount = flt(fields.get("tax_amount"))
                
                if not self.payment_method and fields.get("payment_method"):
                    payment_method = fields.get("payment_method")
                    if "Credit Card" in payment_method:
                        self.payment_method = "Credit Card"
                    elif "Debit" in payment_method:
                        self.payment_method = "Debit Card"
                    elif "Cash" in payment_method:
                        self.payment_method = "Cash"
                    elif "Check" in payment_method:
                        self.payment_method = "Check"
                
                if not self.receipt_date and fields.get("date"):
                    try:
                        from dateutil import parser
                        parsed_date = parser.parse(fields.get("date"))
                        self.receipt_date = parsed_date.strftime("%Y-%m-%d")
                    except:
                        pass
                
                # Try to match vendor
                if not self.vendor and fields.get("vendor_name"):
                    vendor_name = fields.get("vendor_name")
                    supplier = frappe.db.get_value("Supplier", {"supplier_name": ["like", f"%{vendor_name}%"]})
                    if supplier:
                        self.vendor = supplier
                
                self.save(ignore_permissions=True)
                
                frappe.msgprint(
                    f"OCR processing completed with {self.ocr_confidence:.1f}% confidence",
                    indicator="green",
                    title="OCR Success"
                )
                
            else:
                self.ocr_status = "Failed"
                self.ocr_extracted_data = json.dumps({"error": result.get("error", "Unknown error")})
                self.save(ignore_permissions=True)
                
                frappe.throw(f"OCR processing failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.ocr_status = "Failed"
            self.ocr_extracted_data = json.dumps({"error": str(e)})
            self.save(ignore_permissions=True)
            
            frappe.log_error(f"OCR processing error: {str(e)}", "Expense Receipt OCR")
            frappe.throw(f"OCR processing error: {str(e)}")
    
    @frappe.whitelist()
    def create_journal_entry(self):
        """
        Create a Journal Entry from this expense receipt.
        """
        if not self.expense_account:
            frappe.throw("Please select an Expense Account")
        
        if not self.amount:
            frappe.throw("Amount is required")
        
        if self.journal_entry:
            frappe.throw("Journal Entry already created")
        
        # Get default bank/cash account
        default_account = frappe.db.get_value(
            "Company",
            frappe.defaults.get_user_default("Company"),
            "default_cash_account"
        )
        
        if not default_account:
            frappe.throw("Please set a default cash account in Company settings")
        
        # Create Journal Entry
        je = frappe.new_doc("Journal Entry")
        je.posting_date = self.receipt_date
        je.voucher_type = "Journal Entry"
        je.company = frappe.defaults.get_user_default("Company")
        je.user_remark = f"Expense from receipt: {self.name}"
        
        # Debit expense account
        je.append("accounts", {
            "account": self.expense_account,
            "debit_in_account_currency": self.amount,
            "cost_center": self.cost_center
        })
        
        # Credit cash/bank account
        je.append("accounts", {
            "account": default_account,
            "credit_in_account_currency": self.amount,
            "cost_center": self.cost_center
        })
        
        je.insert()
        je.submit()
        
        # Link journal entry
        self.journal_entry = je.name
        self.status = "Posted"
        self.save()
        
        frappe.msgprint(
            f"Journal Entry {je.name} created successfully",
            indicator="green",
            title="Success"
        )
        
        return je.name
    
    @frappe.whitelist()
    def approve(self):
        """Approve the expense receipt."""
        if self.status not in ["Draft", "Pending Review"]:
            frappe.throw("Only Draft or Pending Review receipts can be approved")
        
        self.status = "Approved"
        self.save()
        
        frappe.msgprint("Expense Receipt approved", indicator="green")
    
    @frappe.whitelist()
    def reject(self):
        """Reject the expense receipt."""
        if self.status not in ["Draft", "Pending Review"]:
            frappe.throw("Only Draft or Pending Review receipts can be rejected")
        
        self.status = "Rejected"
        self.save()
        
        frappe.msgprint("Expense Receipt rejected", indicator="orange")


@frappe.whitelist()
def bulk_process_ocr(receipts):
    """
    Process OCR for multiple receipts.
    
    Args:
        receipts: List of receipt names or JSON string
    """
    if isinstance(receipts, str):
        receipts = json.loads(receipts)
    
    processed = 0
    failed = 0
    
    for receipt_name in receipts:
        try:
            doc = frappe.get_doc("Expense Receipt", receipt_name)
            if doc.receipt_image and doc.ocr_status != "Completed":
                doc.process_ocr()
                processed += 1
        except Exception as e:
            frappe.log_error(f"Bulk OCR error for {receipt_name}: {str(e)}")
            failed += 1
    
    return {
        "processed": processed,
        "failed": failed,
        "total": len(receipts)
    }
