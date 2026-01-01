import re
import pytesseract
from PIL import Image

# Initialize client (will fail if no creds, so we'll wrap in try/except usage or mock)
# For now, we assume credentials are set via env var GOOGLE_APPLICATION_CREDENTIALS

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
    # We ignore small amounts that might be tax or line items if possible, but max() is a good heuristic.
    amounts = re.findall(r'\$?\s?(\d+\.\d{2})', text)
    if amounts:
        try:
            # Convert to floats
            valid_amounts = [float(a) for a in amounts]
            if valid_amounts:
                data["total"] = max(valid_amounts)
        except:
            pass
            
    # Date Extraction
    # Supports: MM/DD/YYYY, DD/MM/YYYY, YYYY-MM-DD
    # We pick the first valid-looking date.
    date_pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})|(\d{4}[/-]\d{1,2}[/-]\d{1,2})'
    dates = re.findall(date_pattern, text)
    if dates:
        # re.findall with groups returns tuples, find the non-empty string
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
    
    # List of generic words to skip if they appear on the first line
    skip_words = ["receipt", "invoice", "total", "date", "payment", "subtotal"]
    
    for line in lines:
        if len(line) < 3: continue # Skip very short lines
        
        # If line contains digits (like a phone number or date), it might not be the vendor
        # But some vendors have numbers. Let's just check if it's NOT just a date.
        is_date = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', line)
        if is_date: continue
        
        line_lower = line.lower()
        if any(word in line_lower for word in skip_words):
            continue
            
        # Found a candidate
        data["vendor"] = line
        break
        
    return data

def process_image(file_path: str):
    """
    Uses Tesseract OCR to extract text from the image.
    Returns: full_text, structured_data, confidence
    """
    try:
        # Load image via Pillow
        image = Image.open(file_path)
        
        # Extract text using Tesseract
        full_text = pytesseract.image_to_string(image)
        
        # Tesseract doesn't provide a single confidence score easily without more advanced usage (image_to_data)
        # For simplicity, we'll assume high confidence if we got text, low if empty.
        confidence = 0.9 if full_text.strip() else 0.0

        if not full_text.strip():
            return {"raw_text": "", "structured_data": {}, "confidence": 0.0}

        return {
            "raw_text": full_text,
            "structured_data": extract_structured_data(full_text),
            "confidence": confidence
        }
    except Exception as e:
        print(f"OCR Error: {e}")
        # Return fallback or error
        return None
