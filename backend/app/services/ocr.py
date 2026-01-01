"""OCR Service for SMELens

Uses Tesseract OCR to extract text from receipt/invoice images.
Includes regex-based parsing to extract structured data (vendor, total, date).
"""
import re
import logging
import pytesseract
from PIL import Image

# Configure logger for OCR service
logger = logging.getLogger(__name__)

# Verify Tesseract is installed (will log warning if not found)
try:
    tesseract_version = pytesseract.get_tesseract_version()
    logger.info(f"Tesseract OCR initialized - version {tesseract_version}")
except Exception as e:
    logger.warning(f"Tesseract may not be properly installed: {e}")

def extract_structured_data(text):
    """
    Simple regex-based extraction for SME fields.
    Refine this with LLMs or better regex in production.
    """
    data = {
        "total": None,
        "vendor": "Unknown Vendor",
        "date": None,
        "raw_text": text
    }
    
    # GROSS/TOTAL Amount Extraction
    # Strategy: Find all dollar amounts, usually the largest one at the bottom is the total.
    amounts = re.findall(r'\$?\s?(\d+\.\d{2})', text)
    if amounts:
        try:
            valid_amounts = [float(a) for a in amounts]
            if valid_amounts:
                data["total"] = max(valid_amounts)
        except:
            pass
            
    # Date Extraction
    # Supports: MM/DD/YYYY, DD/MM/YYYY, YYYY-MM-DD
    date_pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})|(\d{4}[/-]\d{1,2}[/-]\d{1,2})'
    dates = re.findall(date_pattern, text)
    if dates:
        for group in dates:
            for match in group:
                if match:
                    data["date"] = match
                    break
            if data["date"]:
                break
        
    # Vendor Extraction
    # Heuristic: The first non-empty line that isn't a date or generic label is often the vendor.
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    skip_words = ["receipt", "invoice", "total", "date", "payment", "subtotal"]
    
    for line in lines:
        if len(line) < 3: continue
        
        is_date = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', line)
        if is_date: continue
        
        line_lower = line.lower()
        if any(word in line_lower for word in skip_words):
            continue
            
        data["vendor"] = line
        break
        
    return data

def process_image(file_path: str) -> dict | None:
    """
    Main OCR processing function.
    
    Uses Tesseract OCR to extract text from the image, then parses
    the text to extract structured data (vendor, total, date).
    
    Args:
        file_path: Path to the image file
        
    Returns:
        dict with raw_text, structured_data, and confidence score
        None if OCR fails completely
    """
    logger.info(f"OCR: Starting processing for {file_path}")
    
    try:
        # Load image via Pillow
        image = Image.open(file_path)
        logger.info(f"OCR: Image loaded successfully - size {image.size}, mode {image.mode}")
        
        # Extract text using Tesseract
        full_text = pytesseract.image_to_string(image)
        
        # Get detailed OCR data for confidence calculation
        try:
            ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            confidences = [int(c) for c, t in zip(ocr_data['conf'], ocr_data['text']) 
                          if c != '-1' and t.strip()]
            confidence = sum(confidences) / len(confidences) / 100 if confidences else 0.0
        except Exception as conf_err:
            logger.warning(f"OCR: Could not calculate confidence: {conf_err}")
            confidence = 0.9 if full_text.strip() else 0.0

        if not full_text.strip():
            logger.warning("OCR: No text extracted from image")
            return {"raw_text": "", "structured_data": {}, "confidence": 0.0}

        # Parse structured data from the raw text
        structured_data = extract_structured_data(full_text)
        
        logger.info(f"OCR: Success - extracted {len(full_text)} chars, confidence {confidence:.2f}")
        logger.info(f"OCR: Structured data - vendor: {structured_data.get('vendor')}, total: {structured_data.get('total')}")
        
        return {
            "raw_text": full_text,
            "structured_data": structured_data,
            "confidence": round(confidence, 2)
        }
        
    except FileNotFoundError:
        logger.error(f"OCR: File not found - {file_path}")
        return None
    except Exception as e:
        logger.error(f"OCR: Processing failed - {type(e).__name__}: {e}")
        return None
