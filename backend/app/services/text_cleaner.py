"""OCR Text Cleaner and Corrector for SMELens

Post-OCR processing to fix common OCR errors and normalize text.
Uses deterministic rules, NOT AI guessing.

Features:
- Character confusion correction (O↔0, l↔1, S↔5)
- Currency format normalization
- Date format normalization  
- Whitespace cleanup
- Common word corrections
"""
import re
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CleaningResult:
    """Result of text cleaning operation."""
    original_text: str
    cleaned_text: str
    corrections_made: list[dict]
    correction_count: int


class OCRTextCleaner:
    """
    Cleans and corrects OCR output using deterministic rules.
    
    Focuses on common OCR mistakes without introducing hallucinations.
    """
    
    # Common OCR character confusions
    # Format: (pattern, replacement, context_hint)
    CHAR_CONFUSIONS = [
        # O/0 confusion - replace O with 0 in numeric contexts
        (r'(?<=[0-9])O(?=[0-9])', '0', 'O→0 in numbers'),
        (r'(?<=[0-9])O(?=\s|$|,|\.)', '0', 'O→0 at number end'),
        (r'(?<=\$)O', '0', 'O→0 after $'),
        
        # l/1 confusion - replace l with 1 in numeric contexts
        (r'(?<=[0-9])l(?=[0-9])', '1', 'l→1 in numbers'),
        (r'(?<=\$)l', '1', 'l→1 after $'),
        
        # S/5 confusion - replace S with 5 in numeric contexts
        (r'(?<=[0-9])S(?=[0-9])', '5', 'S→5 in numbers'),
        
        # I/1 confusion
        (r'(?<=[0-9])I(?=[0-9])', '1', 'I→1 in numbers'),
        
        # B/8 confusion
        (r'(?<=[0-9])B(?=[0-9])', '8', 'B→8 in numbers'),
        
        # Common word OCR errors
        (r'\bTOTAI\b', 'TOTAL', 'TOTAI→TOTAL'),
        (r'\bT0TAL\b', 'TOTAL', 'T0TAL→TOTAL'),
        (r'\bTOTAL\b', 'TOTAL', 'case normalize'),  # Ensure consistent case
        (r'\bSUBTOTAI\b', 'SUBTOTAL', 'SUBTOTAI→SUBTOTAL'),
        (r'\bAM0UNT\b', 'AMOUNT', 'AM0UNT→AMOUNT'),
        (r'\bBAIANCE\b', 'BALANCE', 'BAIANCE→BALANCE'),
        (r'\bRECE1PT\b', 'RECEIPT', 'RECE1PT→RECEIPT'),
        (r'\bINV0ICE\b', 'INVOICE', 'INV0ICE→INVOICE'),
    ]
    
    # Currency patterns to normalize
    CURRENCY_PATTERNS = [
        # Kenya Shillings variations
        (r'\bKSH\.?\s*', 'KES ', 'KSH→KES'),
        (r'\bKSHS\.?\s*', 'KES ', 'KSHS→KES'),
        (r'\bKes\.?\s*', 'KES ', 'Kes→KES'),
        
        # USD variations
        (r'\bUS\$\s*', 'USD ', 'US$→USD'),
        (r'\bUSD\s*\$', 'USD ', 'USD$→USD'),
        
        # Fix spacing around currency symbols
        (r'\$\s+(\d)', r'$\1', 'remove space after $'),
        (r'(\d)\s+\$', r'\1 $', 'normalize space before $'),
    ]
    
    # Date format patterns - for recognition, not correction
    DATE_PATTERNS = [
        r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',      # MM/DD/YYYY, DD-MM-YY
        r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',         # YYYY-MM-DD
        r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}',
        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{2,4}',
    ]
    
    def __init__(self):
        """Initialize the text cleaner."""
        self.corrections: list[dict] = []
    
    def clean(self, text: str) -> CleaningResult:
        """
        Apply all cleaning rules to OCR text.
        
        Args:
            text: Raw OCR text
            
        Returns:
            CleaningResult with cleaned text and corrections log
        """
        self.corrections = []
        original = text
        cleaned = text
        
        logger.info(f"TextCleaner: Starting - {len(text)} characters")
        
        # Step 1: Basic whitespace cleanup
        cleaned = self._clean_whitespace(cleaned)
        
        # Step 2: Fix character confusions
        cleaned = self._fix_char_confusions(cleaned)
        
        # Step 3: Normalize currency
        cleaned = self._normalize_currency(cleaned)
        
        # Step 4: Fix decimal separators in numbers
        cleaned = self._fix_decimals(cleaned)
        
        # Step 5: Final whitespace normalization
        cleaned = self._final_normalize(cleaned)
        
        logger.info(f"TextCleaner: Complete - {len(self.corrections)} corrections")
        
        return CleaningResult(
            original_text=original,
            cleaned_text=cleaned,
            corrections_made=self.corrections.copy(),
            correction_count=len(self.corrections)
        )
    
    def _clean_whitespace(self, text: str) -> str:
        """Remove excessive whitespace while preserving structure."""
        # Replace multiple spaces with single space
        cleaned = re.sub(r' {2,}', ' ', text)
        
        # Replace multiple newlines with double newline
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        # Remove trailing whitespace from lines
        cleaned = '\n'.join(line.rstrip() for line in cleaned.split('\n'))
        
        if cleaned != text:
            self.corrections.append({
                "type": "whitespace",
                "description": "Normalized whitespace"
            })
        
        return cleaned
    
    def _fix_char_confusions(self, text: str) -> str:
        """Apply character confusion fixes."""
        cleaned = text
        
        for pattern, replacement, description in self.CHAR_CONFUSIONS:
            new_text = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
            if new_text != cleaned:
                self.corrections.append({
                    "type": "char_confusion",
                    "description": description,
                    "pattern": pattern
                })
                cleaned = new_text
        
        return cleaned
    
    def _normalize_currency(self, text: str) -> str:
        """Normalize currency symbols and codes."""
        cleaned = text
        
        for pattern, replacement, description in self.CURRENCY_PATTERNS:
            new_text = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
            if new_text != cleaned:
                self.corrections.append({
                    "type": "currency",
                    "description": description
                })
                cleaned = new_text
        
        return cleaned
    
    def _fix_decimals(self, text: str) -> str:
        """
        Fix common decimal separator issues.
        
        OCR often misreads decimal points or adds extra spaces.
        """
        cleaned = text
        
        # Fix space in decimals: "10. 00" -> "10.00"
        pattern = r'(\d+)\.\s+(\d{2})\b'
        new_text = re.sub(pattern, r'\1.\2', cleaned)
        if new_text != cleaned:
            self.corrections.append({
                "type": "decimal",
                "description": "Fixed space in decimal"
            })
            cleaned = new_text
        
        # Fix comma as decimal: "10,00" -> "10.00" (common in some locales)
        # Only when followed by exactly 2 digits (likely decimal, not thousands)
        pattern = r'(\d+),(\d{2})\b(?!\d)'
        new_text = re.sub(pattern, r'\1.\2', cleaned)
        if new_text != cleaned:
            self.corrections.append({
                "type": "decimal",
                "description": "Converted comma decimal to period"
            })
            cleaned = new_text
        
        return cleaned
    
    def _final_normalize(self, text: str) -> str:
        """Final normalization pass."""
        # Strip leading/trailing whitespace
        cleaned = text.strip()
        
        # Ensure consistent line endings
        cleaned = cleaned.replace('\r\n', '\n').replace('\r', '\n')
        
        return cleaned


class TextCorrector:
    """
    Context-aware text corrector for SME documents.
    
    Uses proximity and contextual rules to identify and flag
    potential OCR errors without making assumptions.
    """
    
    # Keywords that indicate amounts nearby
    AMOUNT_KEYWORDS = [
        'total', 'amount', 'balance', 'due', 'subtotal', 'sub-total',
        'grand total', 'net', 'gross', 'sum', 'pay', 'payment'
    ]
    
    # Keywords that indicate dates nearby
    DATE_KEYWORDS = [
        'date', 'dated', 'issued', 'due date', 'invoice date',
        'receipt date', 'transaction'
    ]
    
    def find_amounts_near_keywords(self, text: str) -> list[dict]:
        """
        Find amounts that appear near total-related keywords.
        
        Returns list of potential totals with their proximity scores.
        """
        results = []
        lines = text.lower().split('\n')
        
        for i, line in enumerate(lines):
            for keyword in self.AMOUNT_KEYWORDS:
                if keyword in line:
                    # Look for amounts on this line or next line
                    search_text = line
                    if i + 1 < len(lines):
                        search_text += ' ' + lines[i + 1]
                    
                    # Find all dollar amounts
                    amounts = re.findall(r'\$?\s*([\d,]+\.?\d*)', search_text)
                    for amount in amounts:
                        try:
                            value = float(amount.replace(',', ''))
                            results.append({
                                "value": value,
                                "keyword": keyword,
                                "line": i,
                                "proximity_score": 0.9 if keyword in line else 0.7
                            })
                        except ValueError:
                            continue
        
        return results
    
    def identify_suspicious_values(self, text: str) -> list[dict]:
        """
        Identify values that look suspicious or need verification.
        
        Examples:
        - Amounts with unusual decimals (not .00, .50, .99, etc.)
        - Very large numbers that might be misreads
        - Numbers with mixed characters
        """
        suspicious = []
        
        # Find all potential amounts
        amounts = re.findall(r'\$?\s*([\d,]+\.\d+)', text)
        
        for amount in amounts:
            try:
                value = float(amount.replace(',', ''))
                
                # Check for unusual decimal values
                decimal_part = value - int(value)
                common_decimals = [0.0, 0.25, 0.50, 0.75, 0.99, 0.95]
                if decimal_part not in common_decimals and value > 10:
                    suspicious.append({
                        "value": amount,
                        "reason": "Unusual decimal value",
                        "severity": "low"
                    })
                
                # Check for suspiciously large values
                if value > 1000000:
                    suspicious.append({
                        "value": amount,
                        "reason": "Very large value - verify accuracy",
                        "severity": "medium"
                    })
                    
            except ValueError:
                suspicious.append({
                    "value": amount,
                    "reason": "Could not parse as number",
                    "severity": "high"
                })
        
        return suspicious


def clean_text(text: str) -> CleaningResult:
    """
    Convenience function to clean OCR text.
    
    Args:
        text: Raw OCR text
        
    Returns:
        CleaningResult with cleaned text and corrections
    """
    cleaner = OCRTextCleaner()
    return cleaner.clean(text)
