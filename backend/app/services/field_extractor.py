"""Field Extraction Engine for SMELens

Deterministic extraction of structured fields from OCR text.
Uses regex patterns, proximity scoring, and contextual rules.

Extracts:
- vendor_name / sender / institution_name
- date
- total_amount
- currency
- document_type
- form_title
- identifiers
- subject
"""
import re
import logging
from typing import Optional, Any
from dataclasses import dataclass, field
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
    value: str  # Normalized format YYYY-MM-DD
    original: str  # As found in text
    confidence: float
    format_detected: str


@dataclass 
class ExtractedVendor:
    """Represents an extracted vendor/sender/institution."""
    name: str
    confidence: float
    source: str  # e.g., "first_line", "header_pattern"


@dataclass
class ExtractionResult:
    """Complete extraction result with all fields."""
    # Common fields
    document_type: str = "unknown"
    date: Optional[ExtractedDate] = None
    currency: str = "UNKNOWN"
    
    # Receipt/Invoice fields
    vendor: Optional[ExtractedVendor] = None
    total_amount: Optional[ExtractedAmount] = None
    
    # Form fields
    institution_name: Optional[str] = None
    form_title: Optional[str] = None
    identifiers: dict[str, str] = field(default_factory=dict)
    
    # Letter fields
    sender: Optional[str] = None
    subject: Optional[str] = None
    
    # Government ID fields
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    place_of_birth: Optional[str] = None
    id_number: Optional[str] = None
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    issuing_authority: Optional[str] = None
    
    # Metadata
    all_amounts: list[ExtractedAmount] = field(default_factory=list)
    all_dates: list[ExtractedDate] = field(default_factory=list)
    extraction_notes: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        base = {
            "document_type": self.document_type,
            "date": self.date.value if self.date else None,
            "currency": self.currency,
            "notes": self.extraction_notes
        }
        
        if self.document_type in ["receipt", "invoice"]:
            base.update({
                "vendor": self.vendor.name if self.vendor else None,
                "total_amount": self.total_amount.value if self.total_amount else None,
            })
        elif self.document_type == "form":
            base.update({
                "institution_name": self.institution_name,
                "form_title": self.form_title,
                "identifiers": self.identifiers
            })
        elif self.document_type == "letter":
            base.update({
                "sender": self.sender,
                "subject": self.subject
            })
        elif self.document_type in ["birth_certificate", "national_id", "passport", "driving_license"]:
            base.update({
                "full_name": self.full_name,
                "date_of_birth": self.date_of_birth,
                "place_of_birth": self.place_of_birth,
                "id_number": self.id_number,
                "father_name": self.father_name,
                "mother_name": self.mother_name,
                "issuing_authority": self.issuing_authority,
                "identifiers": self.identifiers
            })
        else:
            # Include everything for unknown
            base.update({
                "vendor": self.vendor.name if self.vendor else None,
                "total_amount": self.total_amount.value if self.total_amount else None,
                "institution_name": self.institution_name,
                "form_title": self.form_title,
                "identifiers": self.identifiers,
                "sender": self.sender,
                "subject": self.subject
            })
            
        return base


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
    
    # Vendor skip words - lines containing these are likely not vendor names
    VENDOR_SKIP_WORDS = [
        'receipt', 'invoice', 'total', 'subtotal', 'date', 'time',
        'tax', 'vat', 'payment', 'cash', 'change', 'balance',
        'thank you', 'thanks', 'tel:', 'phone:', 'email:', 'www.',
        'address:', 'p.o. box', 'po box', 'pin:', 'vat no:'
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
        
        # Extract all dates
        all_dates = self._extract_dates(text)
        doc_date = self._find_document_date(all_dates)
        
        result = ExtractionResult(
            document_type=doc_type,
            date=doc_date,
            currency=currency,
            all_dates=all_dates,
            extraction_notes=self.notes
        )
        
        # Document-specific extraction
        if doc_type in ['receipt', 'invoice']:
            # Extract amounts
            all_amounts = self._extract_amounts(text, currency)
            total = self._find_total(text, all_amounts)
            vendor = self._extract_vendor(text)
            
            result.total_amount = total
            result.vendor = vendor
            result.all_amounts = all_amounts
            
        elif doc_type == 'form':
            # Extract form fields
            result.institution_name = self._extract_institution(text)
            result.form_title = self._extract_form_title(text)
            result.identifiers = self._extract_identifiers(text)
            
        elif doc_type == 'letter':
            # Extract letter fields
            result.sender = self._extract_sender(text)
            result.subject = self._extract_subject(text)
        
        elif doc_type in ['birth_certificate', 'national_id', 'passport', 'driving_license']:
            # Extract government ID fields
            gov_fields = self._extract_government_id_fields(text, doc_type)
            result.full_name = gov_fields.get('full_name')
            result.date_of_birth = gov_fields.get('date_of_birth')
            result.place_of_birth = gov_fields.get('place_of_birth')
            result.id_number = gov_fields.get('id_number')
            result.father_name = gov_fields.get('father_name')
            result.mother_name = gov_fields.get('mother_name')
            result.issuing_authority = gov_fields.get('issuing_authority')
            result.identifiers = gov_fields.get('identifiers', {})
            
        else:
            # Unknown type - try to extract everything
            all_amounts = self._extract_amounts(text, currency)
            total = self._find_total(text, all_amounts)
            vendor = self._extract_vendor(text)
            
            result.total_amount = total
            result.vendor = vendor
            result.all_amounts = all_amounts
        
        return result
    
    def _detect_document_type(self, text: str) -> str:
        """Detect the type of document based on keywords."""
        text_upper = text.upper()
        
        # Government ID Documents
        if any(word in text_upper for word in ["BIRTH", "CERTIFICATE OF BIRTH", "BORN"]):
            return "birth_certificate"
            
        if any(word in text_upper for word in ["NATIONAL ID", "IDENTITY CARD", "ID CARD"]):
            return "national_id"
            
        if any(word in text_upper for word in ["PASSPORT", "TRAVEL DOCUMENT"]):
            return "passport"
            
        if any(word in text_upper for word in ["DRIVING LICENCE", "DRIVER'S LICENSE", "DRIVING LICENSE"]):
            return "driving_license"
        
        # Task 1 Rules
        if any(word in text_upper for word in ["RECEIPT", "TOTAL", "AMOUNT"]):
            # Check if it's actually an invoice
            if "INVOICE" in text_upper:
                return "invoice"
            return "receipt"
            
        if any(word in text_upper for word in ["INVOICE", "DUE DATE"]):
            return "invoice"
            
        if any(word in text_upper for word in ["FORM", "STUDENT", "REGISTRATION", "SEMESTER"]):
            return "form"
            
        if any(word in text for word in ["Dear", "Yours faithfully"]):
            return "letter"
            
        self.notes.append("Could not determine document type")
        return "unknown"
    
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
        if re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', text):
            return True
        if re.match(r'^\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}$', text):
            return True
        return False
    
    def _looks_like_year(self, value: float) -> bool:
        """Check if a value looks like a year (should not be a price)."""
        if 1900 <= value <= 2100 and value == int(value):
            return True
        return False

    def _find_total(self, text: str, amounts: list[ExtractedAmount]) -> Optional[ExtractedAmount]:
        """Find the most likely total amount."""
        if not amounts:
            self.notes.append("No amounts found in document")
            return None
        
        text_lower = text.lower()
        lines = text_lower.split('\n')
        
        # Strategy 1: Look for amounts near total keywords
        total_candidates: list[tuple[ExtractedAmount, float]] = []
        
        for i, line in enumerate(lines):
            is_subtotal_line = any(re.search(kw, line) for kw in self.SUBTOTAL_KEYWORDS)
            is_total_line = any(re.search(kw, line) for kw in self.TOTAL_KEYWORDS) and not is_subtotal_line
            
            if is_total_line:
                search_area = line
                if i + 1 < len(lines):
                    search_area += ' ' + lines[i + 1]
                
                for amount in amounts:
                    amount_str = f"{amount.value:.2f}"
                    if amount_str in search_area or str(int(amount.value)) in search_area:
                        total_candidates.append((amount, 0.95))
        
        if total_candidates:
            best = max(total_candidates, key=lambda x: (x[1], x[0].value))
            best[0].confidence = best[1]
            best[0].source = "near_keyword"
            return best[0]
        
        # Strategy 2: Largest amount with currency symbol
        amounts_with_currency = [
            a for a in amounts 
            if any(sym in a.raw_text for sym in ['$', '€', '£', 'KES', 'KSH', 'USD'])
        ]
        
        if amounts_with_currency:
            best = max(amounts_with_currency, key=lambda a: a.value)
            best.confidence = 0.85
            best.source = "currency_symbol"
            return best
        
        # Strategy 3: Largest amount
        largest = max(amounts, key=lambda a: a.value)
        largest.confidence = 0.7
        largest.source = "largest_value"
        return largest
    
    def _extract_dates(self, text: str) -> list[ExtractedDate]:
        """Extract all dates from text."""
        dates: list[ExtractedDate] = []
        
        for pattern, format_type in self.DATE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                original = match.group(0)
                
                # Reject OCR noise (Task 3)
                if re.search(r'[<>=]', original):
                    continue
                    
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
            
            day = int(day)
            month = int(month) if isinstance(month, str) else month
            year = int(year)
            
            if 1 <= day <= 31 and 1 <= month <= 12:
                return f"{year:04d}-{month:02d}-{day:02d}"
                
        except (ValueError, TypeError, IndexError):
            pass
        return None
    
    def _month_name_to_num(self, name: str) -> int:
        months = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
            'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
            'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        return months.get(name.lower()[:3], 0)
    
    def _find_document_date(self, dates: list[ExtractedDate]) -> Optional[ExtractedDate]:
        """Find the most likely document date."""
        if not dates:
            self.notes.append("No dates found in document")
            return None
        return dates[0]
    
    def _extract_vendor(self, text: str) -> Optional[ExtractedVendor]:
        """
        Extract vendor/business name.
        Task 3: Prefer top 15% of document.
        """
        lines = text.split('\n')
        total_lines = len(lines)
        threshold_line = max(int(total_lines * 0.15), 5) # At least 5 lines or 15%
        
        for i, line in enumerate(lines):
            if i > threshold_line:
                break
                
            line = line.strip()
            
            # Task 3: Ignore symbols, random OCR noise, must be > 3 chars
            if len(line) <= 3:
                continue
                
            # Check for alphabetic words
            if not re.search(r'[a-zA-Z]', line):
                continue
                
            # Skip lines with skip words
            line_lower = line.lower()
            if any(skip in line_lower for skip in self.VENDOR_SKIP_WORDS):
                continue
            
            # Skip dates/numbers
            if re.match(r'^[\d/.-]+$', line) or re.match(r'^[\d,.\s$€£]+$', line):
                continue
            
            confidence = 0.8
            source = "top_15_percent"
            
            if line.isupper():
                confidence = 0.9
                source = "all_caps_header"
            
            return ExtractedVendor(name=line, confidence=confidence, source=source)
        
        self.notes.append("Could not identify vendor name in top 15%")
        return None

    def _extract_institution(self, text: str) -> Optional[str]:
        """Extract institution name for forms."""
        # Similar to vendor but looks for "University", "School", "College", "Institute"
        lines = text.split('\n')
        keywords = ["university", "school", "college", "institute", "academy", "hospital", "clinic"]
        
        for line in lines[:10]: # Top 10 lines
            if any(kw in line.lower() for kw in keywords):
                return line.strip()
        
        # Fallback to first valid line
        for line in lines[:5]:
            if len(line) > 5 and not any(char.isdigit() for char in line):
                return line.strip()
        return None

    def _extract_form_title(self, text: str) -> Optional[str]:
        """Extract form title."""
        lines = text.split('\n')
        keywords = ["form", "registration", "application", "admission", "report"]
        
        for line in lines[:10]:
            if any(kw in line.lower() for kw in keywords):
                return line.strip()
        return None

    def _extract_identifiers(self, text: str) -> dict[str, str]:
        """Extract IDs like registration numbers."""
        identifiers = {}
        
        # Reg No / Student No
        reg_match = re.search(r'(?:reg|registration|student|admission)\s*(?:no|number|id)?\s*[:.]?\s*([A-Z0-9/-]+)', text, re.IGNORECASE)
        if reg_match:
            identifiers["registration_number"] = reg_match.group(1)
            
        # ID Number
        id_match = re.search(r'(?:id|identity)\s*(?:no|number)\s*[:.]?\s*(\d+)', text, re.IGNORECASE)
        if id_match:
            identifiers["id_number"] = id_match.group(1)
            
        return identifiers

    def _extract_sender(self, text: str) -> Optional[str]:
        """Extract sender for letters."""
        # Usually top left or bottom (Yours faithfully)
        # For now, assume top line
        lines = text.split('\n')
        for line in lines[:5]:
            if len(line) > 3 and not any(char.isdigit() for char in line):
                return line.strip()
        return None

    def _extract_subject(self, text: str) -> Optional[str]:
        """Extract subject line (RE: ...)"""
        match = re.search(r'(?:RE|REF|SUBJECT)\s*[:.]?\s*(.+)', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_government_id_fields(self, text: str, doc_type: str) -> dict[str, Any]:
        """
        Extract fields from government ID documents.
        
        Handles: birth_certificate, national_id, passport, driving_license
        """
        fields: dict[str, Any] = {}
        identifiers: dict[str, str] = {}
        
        # Clean text for better matching
        text_clean = text.replace('\n', ' ').replace('  ', ' ')
        lines = text.split('\n')
        
        # Extract Name - look for common patterns
        name_patterns = [
            r'(?:NAME|FULL\s*NAME|NAME\s*OF\s*CHILD|NAMES?)\s*[:.]?\s*([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+)',
            r'(?:^|\n)\s*([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*(?:\n|$)',  # Name on its own line
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                name = match.group(1).strip()
                # Validate - should have 2+ words, not be a keyword
                if len(name.split()) >= 2 and not any(kw in name.upper() for kw in ['REPUBLIC', 'KENYA', 'CERTIFICATE', 'BIRTH']):
                    fields['full_name'] = name.title()
                    break
        
        # Also try to find name near specific keywords in birth certificates
        if not fields.get('full_name') and doc_type == 'birth_certificate':
            # Look for ID number pattern like "16700087725 Peter Njaroge"
            match = re.search(r'(\d{8,12})\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', text)
            if match:
                identifiers['entry_number'] = match.group(1)
                fields['full_name'] = match.group(2).title()
        
        # Extract Date of Birth
        dob_patterns = [
            r'(?:DATE\s*OF\s*BIRTH|BORN\s*ON|D\.?O\.?B\.?|BIRTH\s*DATE)\s*[:.]?\s*(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})',
            r'(?:BORN)\s+(?:ON\s+)?(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})',
        ]
        
        for pattern in dob_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields['date_of_birth'] = match.group(1)
                break
        
        # Extract Place of Birth
        place_patterns = [
            r'(?:PLACE\s*OF\s*BIRTH|BORN\s*(?:AT|IN)|DISTRICT)\s*[:.]?\s*([A-Za-z][A-Za-z\s]+?)(?:\n|,|\.)',
            r'(?:DISTRICT|SUB-?COUNTY|LOCATION)\s*[:.]?\s*([A-Za-z][A-Za-z\s]+?)(?:\n|,|\.)',
        ]
        
        for pattern in place_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                place = match.group(1).strip()
                if len(place) > 2:
                    fields['place_of_birth'] = place.title()
                    break
        
        # Extract ID/Certificate Number
        id_patterns = [
            r'(?:CERTIFICATE\s*NO|CERT\.?\s*NO|ID\s*NO|ENTRY\s*NO|NO\.?)\s*[:.]?\s*([A-Z0-9/-]+)',
            r'(?:^|\s)(\d{6,12})(?:\s|$)',  # Long number that could be ID
        ]
        
        for pattern in id_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                id_num = match.group(1).strip()
                if len(id_num) >= 5:
                    fields['id_number'] = id_num
                    identifiers['certificate_number'] = id_num
                    break
        
        # Extract Father's Name
        father_patterns = [
            r'(?:FATHER|NAME\s*OF\s*FATHER|FATHER\'?S?\s*NAME)\s*[:.]?\s*([A-Za-z][A-Za-z\s]+?)(?:\n|,|\.)',
        ]
        
        for pattern in father_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if len(name) > 2:
                    fields['father_name'] = name.title()
                    break
        
        # Extract Mother's Name
        mother_patterns = [
            r'(?:MOTHER|NAME\s*OF\s*MOTHER|MOTHER\'?S?\s*NAME|MAIDEN\s*NAME)\s*[:.]?\s*([A-Za-z][A-Za-z\s]+?)(?:\n|,|\.)',
        ]
        
        for pattern in mother_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if len(name) > 2:
                    fields['mother_name'] = name.title()
                    break
        
        # Extract Issuing Authority
        authority_patterns = [
            r'(?:REPUBLIC\s*OF\s*KENYA)',
            r'(?:DIRECTOR\s*OF\s*CIVIL\s*REGISTRATION)',
            r'(?:REGISTRAR)',
        ]
        
        for pattern in authority_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                fields['issuing_authority'] = "Republic of Kenya - Civil Registration"
                break
        
        fields['identifiers'] = identifiers
        
        self.notes.append(f"Extracted {len([v for v in fields.values() if v])} fields from {doc_type}")
        
        return fields


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
