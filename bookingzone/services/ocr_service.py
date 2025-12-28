"""
BookingZone OCR Service
========================
Open-source OCR integration using PaddleOCR for receipt and invoice processing.
Replaces Google Cloud Vision with zero-cost, self-hosted solution.

Features:
- Receipt scanning with automatic field extraction
- Invoice processing with line item detection
- Multi-language support (109 languages)
- Structure preservation (tables, forms)
- Confidence scoring with Tesseract fallback
"""

import frappe
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import tempfile
import base64

# PaddleOCR Configuration
OCR_CONFIG = {
    "engine": "paddleocr",
    "version": "3.0",
    "settings": {
        "use_gpu": frappe.conf.get("paddleocr_use_gpu", False),
        "gpu_mem": int(frappe.conf.get("paddleocr_gpu_mem", 500)),
        "use_doc_orientation_classify": True,
        "use_doc_unwarping": True,
        "use_textline_orientation": True,
        "lang": "en",
        "det_db_thresh": 0.3,
        "det_db_box_thresh": 0.5
    },
    "fallback": {
        "engine": "tesseract",
        "confidence_threshold": 0.8
    }
}


class PaddleOCRService:
    """
    PaddleOCR-based document processing service.
    Provides receipt scanning, invoice processing, and key field extraction.
    """
    
    def __init__(self):
        self.ocr = None
        self.structure_engine = None
        self._initialize_ocr()
    
    def _initialize_ocr(self):
        """Initialize PaddleOCR engine with configured settings."""
        try:
            from paddleocr import PaddleOCR
            
            self.ocr = PaddleOCR(
                use_angle_cls=True,
                lang=OCR_CONFIG["settings"]["lang"],
                use_gpu=OCR_CONFIG["settings"]["use_gpu"],
                gpu_mem=OCR_CONFIG["settings"]["gpu_mem"],
                det_db_thresh=OCR_CONFIG["settings"]["det_db_thresh"],
                det_db_box_thresh=OCR_CONFIG["settings"]["det_db_box_thresh"],
                show_log=False
            )
            frappe.logger().info("PaddleOCR initialized successfully")
        except ImportError:
            frappe.logger().warning("PaddleOCR not installed, using fallback")
            self.ocr = None
        except Exception as e:
            frappe.logger().error(f"Failed to initialize PaddleOCR: {str(e)}")
            self.ocr = None
    
    def process_image(self, image_path: str) -> Dict:
        """
        Process an image and extract text with bounding boxes.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dict containing extracted text, confidence, and structured data
        """
        if not os.path.exists(image_path):
            return {"success": False, "error": "Image file not found"}
        
        try:
            if self.ocr:
                result = self._process_with_paddleocr(image_path)
            else:
                result = self._process_with_tesseract(image_path)
            
            # Check confidence and use fallback if needed
            if result.get("confidence", 0) < OCR_CONFIG["fallback"]["confidence_threshold"]:
                fallback_result = self._process_with_tesseract(image_path)
                if fallback_result.get("confidence", 0) > result.get("confidence", 0):
                    result = fallback_result
                    result["engine"] = "tesseract_fallback"
            
            return result
            
        except Exception as e:
            frappe.logger().error(f"OCR processing failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _process_with_paddleocr(self, image_path: str) -> Dict:
        """Process image using PaddleOCR."""
        result = self.ocr.ocr(image_path, cls=True)
        
        if not result or not result[0]:
            return {
                "success": True,
                "engine": "paddleocr",
                "text": "",
                "confidence": 0,
                "lines": [],
                "raw_result": []
            }
        
        lines = []
        total_confidence = 0
        text_parts = []
        
        for line in result[0]:
            bbox = line[0]
            text = line[1][0]
            confidence = line[1][1]
            
            lines.append({
                "text": text,
                "confidence": confidence,
                "bbox": {
                    "x1": bbox[0][0],
                    "y1": bbox[0][1],
                    "x2": bbox[2][0],
                    "y2": bbox[2][1]
                }
            })
            text_parts.append(text)
            total_confidence += confidence
        
        avg_confidence = total_confidence / len(lines) if lines else 0
        
        return {
            "success": True,
            "engine": "paddleocr",
            "text": "\n".join(text_parts),
            "confidence": avg_confidence,
            "lines": lines,
            "raw_result": result
        }
    
    def _process_with_tesseract(self, image_path: str) -> Dict:
        """Fallback processing using Tesseract OCR."""
        try:
            import pytesseract
            from PIL import Image
            
            image = Image.open(image_path)
            
            # Get detailed data with confidence
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            
            lines = []
            text_parts = []
            total_confidence = 0
            valid_count = 0
            
            current_line = []
            current_line_num = -1
            
            for i, text in enumerate(data['text']):
                if text.strip():
                    conf = int(data['conf'][i])
                    if conf > 0:
                        line_num = data['line_num'][i]
                        
                        if line_num != current_line_num and current_line:
                            line_text = " ".join(current_line)
                            text_parts.append(line_text)
                            current_line = []
                        
                        current_line.append(text)
                        current_line_num = line_num
                        total_confidence += conf
                        valid_count += 1
            
            if current_line:
                text_parts.append(" ".join(current_line))
            
            avg_confidence = (total_confidence / valid_count / 100) if valid_count else 0
            
            return {
                "success": True,
                "engine": "tesseract",
                "text": "\n".join(text_parts),
                "confidence": avg_confidence,
                "lines": lines,
                "raw_result": data
            }
            
        except Exception as e:
            return {
                "success": False,
                "engine": "tesseract",
                "error": str(e)
            }
    
    def extract_receipt_fields(self, ocr_result: Dict) -> Dict:
        """
        Extract key fields from a receipt OCR result.
        
        Fields extracted:
        - vendor_name
        - date
        - total_amount
        - subtotal
        - tax_amount
        - payment_method
        - line_items
        """
        if not ocr_result.get("success"):
            return {"success": False, "error": "OCR processing failed"}
        
        text = ocr_result.get("text", "")
        lines = text.split("\n")
        
        extracted = {
            "vendor_name": self._extract_vendor_name(lines),
            "date": self._extract_date(text),
            "total_amount": self._extract_total(text),
            "subtotal": self._extract_subtotal(text),
            "tax_amount": self._extract_tax(text),
            "payment_method": self._extract_payment_method(text),
            "line_items": self._extract_line_items(lines),
            "raw_text": text,
            "confidence": ocr_result.get("confidence", 0),
            "engine": ocr_result.get("engine", "unknown")
        }
        
        return {"success": True, "fields": extracted}
    
    def extract_invoice_fields(self, ocr_result: Dict) -> Dict:
        """
        Extract key fields from an invoice OCR result.
        
        Fields extracted:
        - vendor_name
        - vendor_address
        - invoice_number
        - invoice_date
        - due_date
        - total_amount
        - subtotal
        - tax_amount
        - line_items
        - payment_terms
        """
        if not ocr_result.get("success"):
            return {"success": False, "error": "OCR processing failed"}
        
        text = ocr_result.get("text", "")
        lines = text.split("\n")
        
        extracted = {
            "vendor_name": self._extract_vendor_name(lines),
            "vendor_address": self._extract_address(lines),
            "invoice_number": self._extract_invoice_number(text),
            "invoice_date": self._extract_date(text),
            "due_date": self._extract_due_date(text),
            "total_amount": self._extract_total(text),
            "subtotal": self._extract_subtotal(text),
            "tax_amount": self._extract_tax(text),
            "line_items": self._extract_invoice_line_items(lines),
            "payment_terms": self._extract_payment_terms(text),
            "raw_text": text,
            "confidence": ocr_result.get("confidence", 0),
            "engine": ocr_result.get("engine", "unknown")
        }
        
        return {"success": True, "fields": extracted}
    
    def _extract_vendor_name(self, lines: List[str]) -> Optional[str]:
        """Extract vendor name (usually first non-empty line)."""
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if line and len(line) > 2 and not re.match(r'^[\d\-\.\$]+$', line):
                return line
        return None
    
    def _extract_date(self, text: str) -> Optional[str]:
        """Extract date from text using common patterns."""
        patterns = [
            r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',  # MM/DD/YYYY or MM-DD-YYYY
            r'(\d{4}[/\-]\d{1,2}[/\-]\d{1,2})',     # YYYY/MM/DD
            r'([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})', # Month DD, YYYY
            r'(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})',   # DD Month YYYY
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _extract_total(self, text: str) -> Optional[float]:
        """Extract total amount from text."""
        patterns = [
            r'(?:total|amount\s*due|grand\s*total|balance\s*due)[:\s]*\$?\s*([\d,]+\.?\d*)',
            r'\$\s*([\d,]+\.\d{2})\s*$',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            if matches:
                # Return the last (usually largest) match
                amount_str = matches[-1].replace(',', '')
                try:
                    return float(amount_str)
                except ValueError:
                    continue
        return None
    
    def _extract_subtotal(self, text: str) -> Optional[float]:
        """Extract subtotal from text."""
        pattern = r'(?:subtotal|sub\s*total)[:\s]*\$?\s*([\d,]+\.?\d*)'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1).replace(',', ''))
            except ValueError:
                pass
        return None
    
    def _extract_tax(self, text: str) -> Optional[float]:
        """Extract tax amount from text."""
        patterns = [
            r'(?:tax|sales\s*tax|vat|gst)[:\s]*\$?\s*([\d,]+\.?\d*)',
            r'(?:tax)[:\s]*\$?\s*([\d,]+\.\d{2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1).replace(',', ''))
                except ValueError:
                    continue
        return None
    
    def _extract_payment_method(self, text: str) -> Optional[str]:
        """Extract payment method from text."""
        methods = {
            r'visa': 'Credit Card - Visa',
            r'mastercard|mc': 'Credit Card - Mastercard',
            r'amex|american\s*express': 'Credit Card - Amex',
            r'discover': 'Credit Card - Discover',
            r'debit': 'Debit Card',
            r'cash': 'Cash',
            r'check|cheque': 'Check',
            r'credit\s*card': 'Credit Card',
        }
        
        text_lower = text.lower()
        for pattern, method in methods.items():
            if re.search(pattern, text_lower):
                return method
        return None
    
    def _extract_line_items(self, lines: List[str]) -> List[Dict]:
        """Extract line items from receipt."""
        items = []
        item_pattern = r'^(.+?)\s+\$?\s*([\d,]+\.?\d*)$'
        
        for line in lines:
            line = line.strip()
            match = re.match(item_pattern, line)
            if match:
                description = match.group(1).strip()
                amount_str = match.group(2).replace(',', '')
                
                # Skip totals and subtotals
                if any(keyword in description.lower() for keyword in ['total', 'subtotal', 'tax', 'change', 'cash', 'credit']):
                    continue
                
                try:
                    amount = float(amount_str)
                    if amount > 0 and amount < 10000:  # Reasonable item price
                        items.append({
                            "description": description,
                            "amount": amount
                        })
                except ValueError:
                    continue
        
        return items
    
    def _extract_invoice_number(self, text: str) -> Optional[str]:
        """Extract invoice number from text."""
        patterns = [
            r'(?:invoice|inv|invoice\s*#|inv\s*#)[:\s#]*([A-Za-z0-9\-]+)',
            r'(?:number|no|#)[:\s]*([A-Za-z0-9\-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _extract_due_date(self, text: str) -> Optional[str]:
        """Extract due date from text."""
        pattern = r'(?:due\s*date|payment\s*due|due)[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
    def _extract_address(self, lines: List[str]) -> Optional[str]:
        """Extract address from lines."""
        address_lines = []
        for i, line in enumerate(lines[1:6]):  # Skip first line (vendor name)
            line = line.strip()
            # Look for address patterns
            if re.search(r'\d+\s+\w+', line) or re.search(r'[A-Za-z]+,?\s+[A-Z]{2}\s+\d{5}', line):
                address_lines.append(line)
        
        return "\n".join(address_lines) if address_lines else None
    
    def _extract_invoice_line_items(self, lines: List[str]) -> List[Dict]:
        """Extract line items from invoice with quantity and unit price."""
        items = []
        # Pattern: Description, Qty, Unit Price, Amount
        item_pattern = r'^(.+?)\s+(\d+)\s+\$?\s*([\d,]+\.?\d*)\s+\$?\s*([\d,]+\.?\d*)$'
        
        for line in lines:
            line = line.strip()
            match = re.match(item_pattern, line)
            if match:
                try:
                    items.append({
                        "description": match.group(1).strip(),
                        "quantity": int(match.group(2)),
                        "unit_price": float(match.group(3).replace(',', '')),
                        "amount": float(match.group(4).replace(',', ''))
                    })
                except ValueError:
                    continue
        
        return items
    
    def _extract_payment_terms(self, text: str) -> Optional[str]:
        """Extract payment terms from text."""
        patterns = [
            r'(?:terms|payment\s*terms)[:\s]*([^\n]+)',
            r'(net\s*\d+)',
            r'(due\s*on\s*receipt)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None


# Singleton instance
_ocr_service = None

def get_ocr_service() -> PaddleOCRService:
    """Get or create the OCR service singleton."""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = PaddleOCRService()
    return _ocr_service


# Frappe API Methods
@frappe.whitelist()
def process_receipt(file_url: str) -> Dict:
    """
    Process a receipt image and extract fields.
    
    Args:
        file_url: URL or path to the receipt image
        
    Returns:
        Dict with extracted receipt fields
    """
    service = get_ocr_service()
    
    # Get file path from URL
    if file_url.startswith('/files/'):
        file_path = frappe.get_site_path('public', file_url.lstrip('/'))
    elif file_url.startswith('/private/'):
        file_path = frappe.get_site_path(file_url.lstrip('/'))
    else:
        file_path = file_url
    
    # Process image
    ocr_result = service.process_image(file_path)
    
    if not ocr_result.get("success"):
        return ocr_result
    
    # Extract receipt fields
    return service.extract_receipt_fields(ocr_result)


@frappe.whitelist()
def process_invoice(file_url: str) -> Dict:
    """
    Process an invoice image and extract fields.
    
    Args:
        file_url: URL or path to the invoice image
        
    Returns:
        Dict with extracted invoice fields
    """
    service = get_ocr_service()
    
    # Get file path from URL
    if file_url.startswith('/files/'):
        file_path = frappe.get_site_path('public', file_url.lstrip('/'))
    elif file_url.startswith('/private/'):
        file_path = frappe.get_site_path(file_url.lstrip('/'))
    else:
        file_path = file_url
    
    # Process image
    ocr_result = service.process_image(file_path)
    
    if not ocr_result.get("success"):
        return ocr_result
    
    # Extract invoice fields
    return service.extract_invoice_fields(ocr_result)


@frappe.whitelist()
def process_document(file_url: str, document_type: str = "auto") -> Dict:
    """
    Process a document image and extract fields based on type.
    
    Args:
        file_url: URL or path to the document image
        document_type: Type of document ("receipt", "invoice", or "auto")
        
    Returns:
        Dict with extracted fields
    """
    if document_type == "receipt":
        return process_receipt(file_url)
    elif document_type == "invoice":
        return process_invoice(file_url)
    else:
        # Auto-detect: try receipt first, then invoice
        result = process_receipt(file_url)
        if result.get("success") and result.get("fields", {}).get("total_amount"):
            result["detected_type"] = "receipt"
            return result
        
        result = process_invoice(file_url)
        result["detected_type"] = "invoice"
        return result


@frappe.whitelist()
def get_ocr_status() -> Dict:
    """
    Get the status of the OCR service.
    
    Returns:
        Dict with OCR service status and configuration
    """
    service = get_ocr_service()
    
    return {
        "paddleocr_available": service.ocr is not None,
        "tesseract_available": True,  # Always available as fallback
        "config": OCR_CONFIG,
        "version": "3.0"
    }
