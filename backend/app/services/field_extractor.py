"""Field Extraction Engine for SMELens

Deterministic extraction of structured fields from OCR text.
Uses regex patterns, proximity scoring, and contextual rules.

Extracts:
- vendor_name
- date
- total_amount
- currency
- document_type
- line_items (optional)
"""
import re
import logging
from typing import Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class Currency(Enum):
    """Supported currencies with symbols."""
    KES = ("KES", "KSh", "Ksh", "KSH", "KSHS")
    USD = ("USD", "$", "US$")
    EUR = ("EUR", "€")
    GBP = ("GBP", "£")
    UGX = ("UGX",)
    TZS = ("TZS",)
    UNKNOWN = ("",)


@dataclass
class ExtractedAmount:
    """Represents an extracted monetary amount."""
    value: float
    currency: str
    raw_text: str
    confidence: float  # 0.0 - 1.0
    source: str  # e.g., "near_keyword", "largest_value"


@dataclass
class ExtractedDate:
    """Represents an extracted date."""
    value: str  # Normalized format
    original: str  # As found in text
    confidence: float
    format_detected: str


@dataclass 
class ExtractedVendor:
    """Represents an extracted vendor name."""
    name: str
    confidence: float
    source: str  # e.g., "first_line", "header_pattern"


@dataclass
class ExtractionResult:
    """Complete extraction result with all fields."""
    vendor: Optional[ExtractedVendor] = None
    date: Optional[ExtractedDate] = None
    total_amount: Optional[ExtractedAmount] = None
    currency: str = "UNKNOWN"
    document_type: str = "unknown"
    all_amounts: list[ExtractedAmount] = field(default_factory=list)
    all_dates: list[ExtractedDate] = field(default_factory=list)
    extraction_notes: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "vendor": self.vendor.name if self.vendor else None,
            "date": self.date.value if self.date else None,
            "total_amount": self.total_amount.value if self.total_amount else None,
            "currency": self.currency,
            "document_type": self.document_type,
            "all_amounts": [
                {"value": a.value, "currency": a.currency, "confidence": a.confidence}
                for a in self.all_amounts
            ],
            "all_dates": [
                {"value": d.value, "original": d.original}
                for d in self.all_dates
            ],
            "notes": self.extraction_notes
        }


class FieldExtractor:
    """
    Deterministic field extractor for SME documents.
    
    Uses pattern matching and contextual rules to extract
    structured data from OCR text without AI guessing.
    """
    
    # Keywords indicating total amount (case-insensitive)
    TOTAL_KEYWORDS = [
        r'\btotal\b', r'\bgrand\s*total\b', r'\bnet\s*total\b',
        r'\bamount\s*due\b', r'\bbalance\s*due\b', r'\bbalance\b',
        r'\bpayable\b', r'\bsum\b', r'\bgross\b', r'\bpay\b'
    ]
    
    # Keywords indicating subtotal (should not be selected as total)
    SUBTOTAL_KEYWORDS = [
        r'\bsubtotal\b', r'\bsub\s*total\b', r'\bsub-total\b'
    ]
    
    # Date patterns with format hints
    DATE_PATTERNS = [
        # DD/MM/YYYY or MM/DD/YYYY
        (r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})', 'DMY_or_MDY'),
        # YYYY-MM-DD (ISO)
        (r'(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})', 'YMD'),
        # DD/MM/YY or MM/DD/YY
        (r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{2})\b', 'DMY_or_MDY_short'),
        # Month name formats
        (r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[,.]?\s+(\d{4})', 'D_Mon_Y'),
        (r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[,.]?\s+(\d{1,2})[,.]?\s+(\d{4})', 'Mon_D_Y'),
    ]
    
    # Currency patterns
    CURRENCY_PATTERNS = [
        (r'\bKES\b|\bKSH\b|\bKSHS\b|\bKsh\b', 'KES'),
        (r'\$|USD', 'USD'),
        (r'€|EUR', 'EUR'),
        (r'£|GBP', 'GBP'),
        (r'\bUGX\b', 'UGX'),
        (r'\bTZS\b', 'TZS'),
    ]
    
    # Amount pattern - matches monetary values
    AMOUNT_PATTERN = r'(?:KES|KSH|USD|\$|€|£)?\s*([\d,]+\.?\d*)'
    
    # Vendor skip words - lines containing these are likely not vendor names
    VENDOR_SKIP_WORDS = [
        'receipt', 'invoice', 'total', 'subtotal', 'date', 'time',
        'tax', 'vat', 'payment', 'cash', 'change', 'balance',
        'thank you', 'thanks', 'tel:', 'phone:', 'email:', 'www.',
        'address:', 'p.o. box', 'po box'
    ]
    
    def __init__(self):
        """Initialize the field extractor."""
        self.notes: list[str] = []
    
    def extract_all(self, text: str) -> ExtractionResult:
        """
        Extract all fields from OCR text.
        
        Args:
            text: Cleaned OCR text
            
        Returns:
            ExtractionResult with all extracted fields
        """
        self.notes = []
        logger.info(f"FieldExtractor: Starting extraction from {len(text)} chars")
        
        # Detect document type first
        doc_type = self._detect_document_type(text)
        
        # Detect currency
        currency = self._detect_currency(text)
        
        # Extract all amounts
        all_amounts = self._extract_amounts(text, currency)
        
        # Find the most likely total
        total = self._find_total(text, all_amounts)
        
        # Extract all dates
        all_dates = self._extract_dates(text)
        
        # Find the most likely document date
        doc_date = self._find_document_date(all_dates)
        
        # Extract vendor name
        vendor = self._extract_vendor(text)
        
        logger.info(f"FieldExtractor: Found vendor={vendor.name if vendor else None}, "
                   f"total={total.value if total else None}, "
                   f"date={doc_date.value if doc_date else None}")
        
        return ExtractionResult(
            vendor=vendor,
            date=doc_date,
            total_amount=total,
            currency=currency,
            document_type=doc_type,
            all_amounts=all_amounts,
            all_dates=all_dates,
            extraction_notes=self.notes.copy()
        )
    
    def _detect_document_type(self, text: str) -> str:
        """Detect the type of document based on keywords."""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['receipt', 'received', 'sold to']):
            return 'receipt'
        elif any(word in text_lower for word in ['invoice', 'inv no', 'invoice no']):
            return 'invoice'
        elif any(word in text_lower for word in ['quotation', 'quote', 'estimate']):
            return 'quotation'
        elif any(word in text_lower for word in ['purchase order', 'p.o.', 'po number']):
            return 'purchase_order'
        elif any(word in text_lower for word in ['delivery note', 'delivery']):
            return 'delivery_note'
        else:
            self.notes.append("Could not determine document type")
            return 'unknown'
    
    def _detect_currency(self, text: str) -> str:
        """Detect the primary currency used in the document."""
        currency_counts: dict[str, int] = {}
        
        for pattern, currency in self.CURRENCY_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                currency_counts[currency] = len(matches)
        
        if currency_counts:
            # Return the most frequently occurring currency
            primary = max(currency_counts.keys(), key=lambda k: currency_counts[k])
            return primary
        
        # Default to KES for African SME context
        self.notes.append("No currency detected, defaulting to KES")
        return 'KES'
    
    def _extract_amounts(self, text: str, currency: str) -> list[ExtractedAmount]:
        """Extract all monetary amounts from text."""
        amounts: list[ExtractedAmount] = []
        
        # Find all number patterns that look like amounts
        # Pattern matches: $123.45, 123.45, 1,234.56, etc.
        pattern = r'(?:' + '|'.join(p for p, _ in self.CURRENCY_PATTERNS) + r')?\s*([\d,]+\.?\d*)'
        
        for match in re.finditer(pattern, text, re.IGNORECASE):
            raw = match.group(0).strip()
            num_str = match.group(1).replace(',', '')
            
            try:
                value = float(num_str)
                
                # Skip very small values (likely not prices)
                if value < 0.01:
                    continue
                    
                # Skip values that look like dates or times
                if self._looks_like_date_or_time(raw):
                    continue
                
                # Skip values that look like years (1900-2100)
                if self._looks_like_year(value):
                    continue
                
                amounts.append(ExtractedAmount(
                    value=value,
                    currency=currency,
                    raw_text=raw,
                    confidence=0.5,  # Base confidence
                    source="pattern_match"
                ))
            except ValueError:
                continue
        
        # Remove duplicates
        seen = set()
        unique_amounts = []
        for a in amounts:
            if a.value not in seen:
                seen.add(a.value)
                unique_amounts.append(a)
        
        return unique_amounts
    
    def _looks_like_date_or_time(self, text: str) -> bool:
        """Check if a number string looks like a date or time."""
        # Time pattern: HH:MM or HH:MM:SS
        if re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', text):
            return True
        # Date pattern
        if re.match(r'^\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}$', text):
            return True
        return False
    
    def _looks_like_year(self, value: float) -> bool:
        """Check if a value looks like a year (should not be a price)."""
        # Years are typically 1900-2100
        if 1900 <= value <= 2100 and value == int(value):
            return True
        return False
    
    def _find_total(
        self, 
        text: str, 
        amounts: list[ExtractedAmount]
    ) -> Optional[ExtractedAmount]:
        """
        Find the most likely total amount using multiple strategies.
        
        Strategies:
        1. Amount appearing near "TOTAL" keyword
        2. Largest amount (common heuristic)
        3. Last amount in document (often the total)
        """
        if not amounts:
            self.notes.append("No amounts found in document")
            return None
        
        text_lower = text.lower()
        lines = text_lower.split('\n')
        
        # Strategy 1: Look for amounts near total keywords
        total_candidates: list[tuple[ExtractedAmount, float]] = []
        
        for i, line in enumerate(lines):
            is_subtotal_line = any(
                re.search(kw, line) for kw in self.SUBTOTAL_KEYWORDS
            )
            is_total_line = any(
                re.search(kw, line) for kw in self.TOTAL_KEYWORDS
            ) and not is_subtotal_line
            
            if is_total_line:
                # Find amounts on this line or next line
                search_area = line
                if i + 1 < len(lines):
                    search_area += ' ' + lines[i + 1]
                
                for amount in amounts:
                    # Check if this amount appears in the search area
                    amount_str = f"{amount.value:.2f}"
                    if amount_str in search_area or str(int(amount.value)) in search_area:
                        # High confidence - near total keyword
                        total_candidates.append((amount, 0.95))
        
        # If we found candidates near keywords, use the largest one
        if total_candidates:
            best = max(total_candidates, key=lambda x: (x[1], x[0].value))
            best[0].confidence = best[1]
            best[0].source = "near_keyword"
            return best[0]
        
        # Strategy 2: Prefer amounts with currency symbols
        amounts_with_currency = [
            a for a in amounts 
            if any(sym in a.raw_text for sym in ['$', '€', '£', 'KES', 'KSH', 'USD'])
        ]
        
        if amounts_with_currency:
            # Pick the largest amount that has a currency symbol
            best = max(amounts_with_currency, key=lambda a: a.value)
            best.confidence = 0.85
            best.source = "currency_symbol"
            self.notes.append("Total identified by currency symbol")
            return best
        
        # Strategy 3: Use the largest amount as fallback
        largest = max(amounts, key=lambda a: a.value)
        largest.confidence = 0.7
        largest.source = "largest_value"
        self.notes.append("Total identified as largest amount (no keyword found)")
        
        return largest
    
    def _extract_dates(self, text: str) -> list[ExtractedDate]:
        """Extract all dates from text."""
        dates: list[ExtractedDate] = []
        
        for pattern, format_type in self.DATE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                original = match.group(0)
                normalized = self._normalize_date(match, format_type)
                
                if normalized:
                    dates.append(ExtractedDate(
                        value=normalized,
                        original=original,
                        confidence=0.8,
                        format_detected=format_type
                    ))
        
        return dates
    
    def _normalize_date(self, match: re.Match, format_type: str) -> Optional[str]:
        """Normalize a date match to YYYY-MM-DD format."""
        try:
            groups = match.groups()
            
            if format_type == 'YMD':
                year, month, day = groups[0], groups[1], groups[2]
            elif format_type in ['DMY_or_MDY', 'DMY_or_MDY_short']:
                # Assume DD/MM/YYYY for African context
                day, month, year = groups[0], groups[1], groups[2]
                if len(year) == 2:
                    year = '20' + year if int(year) < 50 else '19' + year
            elif format_type == 'D_Mon_Y':
                day = groups[0]
                month = self._month_name_to_num(groups[1])
                year = groups[2]
            elif format_type == 'Mon_D_Y':
                month = self._month_name_to_num(groups[0])
                day = groups[1]
                year = groups[2]
            else:
                return None
            
            # Validate and format
            day = int(day)
            month = int(month) if isinstance(month, str) else month
            year = int(year)
            
            if 1 <= day <= 31 and 1 <= month <= 12:
                return f"{year:04d}-{month:02d}-{day:02d}"
                
        except (ValueError, TypeError, IndexError):
            pass
        
        return None
    
    def _month_name_to_num(self, name: str) -> int:
        """Convert month name to number."""
        months = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
            'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
            'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        return months.get(name.lower()[:3], 0)
    
    def _find_document_date(
        self, 
        dates: list[ExtractedDate]
    ) -> Optional[ExtractedDate]:
        """Find the most likely document date."""
        if not dates:
            self.notes.append("No dates found in document")
            return None
        
        # Prefer dates near keywords like "Date:", "Dated", etc.
        # For now, return the first date found (usually the document date)
        return dates[0]
    
    def _extract_vendor(self, text: str) -> Optional[ExtractedVendor]:
        """
        Extract vendor/business name from text.
        
        Strategy:
        1. First non-trivial line that's not a date or keyword
        2. Lines in ALL CAPS (often business names)
        3. Lines before the word "RECEIPT" or "INVOICE"
        """
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Skip empty or very short lines
            if len(line) < 3:
                continue
            
            # Skip lines with skip words
            line_lower = line.lower()
            if any(skip in line_lower for skip in self.VENDOR_SKIP_WORDS):
                continue
            
            # Skip lines that are just dates
            if re.match(r'^[\d/.-]+$', line):
                continue
            
            # Skip lines that are just numbers
            if re.match(r'^[\d,.\s$€£]+$', line):
                continue
            
            # Found a candidate
            confidence = 0.8
            source = "first_line"
            
            # Boost confidence if all caps
            if line.isupper() and len(line) > 3:
                confidence = 0.9
                source = "all_caps_header"
            
            return ExtractedVendor(
                name=line,
                confidence=confidence,
                source=source
            )
        
        self.notes.append("Could not identify vendor name")
        return None


def extract_fields(text: str) -> ExtractionResult:
    """
    Convenience function to extract fields from OCR text.
    
    Args:
        text: Cleaned OCR text
        
    Returns:
        ExtractionResult with all extracted fields
    """
    extractor = FieldExtractor()
    return extractor.extract_all(text)
