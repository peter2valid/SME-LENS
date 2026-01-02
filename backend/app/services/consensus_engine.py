"""Consensus Extraction Engine for SMELens

Enterprise-grade multi-strategy extraction where NO single method is trusted alone.

For each critical field (total, date, vendor):
- Runs 3-4 independent detectors
- Compares results and scores agreement
- Accepts values ONLY if consensus threshold is met
- Records which detectors agreed for full transparency

Detectors:
1. Regex-based (pattern matching)
2. Keyword + proximity-based
3. Layout/position-based  
4. Statistical (largest / most frequent)

Consensus Rules:
- 3/4 agree → ACCEPT (high confidence)
- 2/4 agree → LOW CONFIDENCE (user should verify)
- <2 agree → REQUEST USER CONFIRMATION (conflicting values)
"""
import re
import logging
from typing import Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ConsensusLevel(Enum):
    """Consensus strength levels."""
    STRONG = "strong"      # 3+ detectors agree
    MODERATE = "moderate"  # 2 detectors agree
    WEAK = "weak"          # <2 agree or conflicting
    NONE = "none"          # No valid candidates


@dataclass
class DetectorResult:
    """Result from a single detector."""
    detector_name: str
    value: Any
    confidence: float  # 0.0 - 1.0
    evidence: str      # Explanation of why this value was chosen
    position: Optional[tuple[int, int]] = None  # (line_number, char_offset)


@dataclass
class ConsensusResult:
    """Result of consensus voting across detectors."""
    field_name: str
    final_value: Optional[Any]
    consensus_level: ConsensusLevel
    agreement_count: int
    total_detectors: int
    detector_results: list[DetectorResult]
    agreeing_detectors: list[str]
    dissenting_detectors: list[str]
    all_candidates: list[tuple[Any, int]]  # (value, vote_count)
    needs_confirmation: bool
    confirmation_reason: Optional[str]
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "field_name": self.field_name,
            "value": self.final_value,
            "consensus_level": self.consensus_level.value,
            "agreement": f"{self.agreement_count}/{self.total_detectors}",
            "agreeing_detectors": self.agreeing_detectors,
            "dissenting_detectors": self.dissenting_detectors,
            "needs_confirmation": self.needs_confirmation,
            "confirmation_reason": self.confirmation_reason,
            "all_candidates": [
                {"value": v, "votes": c} for v, c in self.all_candidates
            ]
        }


@dataclass 
class LayoutInfo:
    """Layout information for a text segment."""
    line_number: int
    total_lines: int
    zone: str  # "header", "body", "footer"
    char_offset: int
    line_text: str


class ConsensusExtractor:
    """
    Multi-strategy extraction engine with consensus voting.
    
    Never trusts a single detector. All critical fields must
    pass consensus voting before being accepted.
    """
    
    # Consensus thresholds
    STRONG_CONSENSUS_THRESHOLD = 3  # Minimum agreeing detectors for high confidence
    MODERATE_CONSENSUS_THRESHOLD = 2
    
    # Zone boundaries (percentage of document)
    HEADER_ZONE_END = 0.15  # Top 15%
    FOOTER_ZONE_START = 0.80  # Bottom 20%
    
    # Amount keywords
    TOTAL_KEYWORDS = [
        'total', 'grand total', 'net total', 'amount due', 
        'balance due', 'balance', 'payable', 'pay', 'sum', 'gross'
    ]
    SUBTOTAL_KEYWORDS = ['subtotal', 'sub total', 'sub-total']
    
    # Vendor skip patterns
    VENDOR_SKIP_PATTERNS = [
        r'\d{2}[/.-]\d{2}[/.-]\d{2,4}',  # Dates
        r'^\d+\.?\d*$',  # Pure numbers
        r'^tel[:\s]', r'^phone[:\s]', r'^fax[:\s]',
        r'^email[:\s]', r'^www\.', r'^http',
        r'^receipt', r'^invoice', r'^order',
        r'^date[:\s]', r'^time[:\s]',
    ]
    
    def __init__(self):
        """Initialize the consensus extractor."""
        self.lines: list[str] = []
        self.total_lines: int = 0
        
    def _get_zone(self, line_idx: int) -> str:
        """Determine which zone a line belongs to."""
        if self.total_lines == 0:
            return "body"
        
        position = line_idx / self.total_lines
        
        if position <= self.HEADER_ZONE_END:
            return "header"
        elif position >= self.FOOTER_ZONE_START:
            return "footer"
        else:
            return "body"
    
    def _get_layout_info(self, line_idx: int, char_offset: int = 0) -> LayoutInfo:
        """Get layout information for a position in the document."""
        return LayoutInfo(
            line_number=line_idx,
            total_lines=self.total_lines,
            zone=self._get_zone(line_idx),
            char_offset=char_offset,
            line_text=self.lines[line_idx] if line_idx < len(self.lines) else ""
        )
    
    # ==================== AMOUNT EXTRACTION ====================
    
    def extract_total_amount(
        self, 
        text: str,
        currency: str = "KES"
    ) -> ConsensusResult:
        """
        Extract total amount using 4 independent detectors.
        
        Detectors:
        1. Regex: Find amounts near 'total' keywords
        2. Proximity: Find amounts on same line as total keywords
        3. Position: Find amounts in footer zone (bottom 20%)
        4. Statistical: Find largest reasonable amount
        """
        self.lines = text.split('\n')
        self.total_lines = len(self.lines)
        
        # Run all detectors
        detector_results: list[DetectorResult] = []
        
        # Detector 1: Regex-based
        regex_result = self._detect_amount_regex(text, currency)
        if regex_result:
            detector_results.append(regex_result)
        
        # Detector 2: Keyword proximity
        proximity_result = self._detect_amount_proximity(text, currency)
        if proximity_result:
            detector_results.append(proximity_result)
        
        # Detector 3: Layout/Position
        position_result = self._detect_amount_position(text, currency)
        if position_result:
            detector_results.append(position_result)
        
        # Detector 4: Statistical (largest)
        statistical_result = self._detect_amount_statistical(text, currency)
        if statistical_result:
            detector_results.append(statistical_result)
        
        return self._build_consensus("total_amount", detector_results)
    
    def _detect_amount_regex(
        self, 
        text: str, 
        currency: str
    ) -> Optional[DetectorResult]:
        """Detector 1: Find amount using regex after total keywords."""
        text_lower = text.lower()
        
        # Build pattern: total keyword followed by amount
        keyword_pattern = '|'.join(self.TOTAL_KEYWORDS)
        # Avoid subtotals
        subtotal_pattern = '|'.join(self.SUBTOTAL_KEYWORDS)
        
        # Pattern: keyword ... amount (within same line or next)
        pattern = rf'(?:^|[^\w])({keyword_pattern})\s*[:\s]*[{currency}$€£]?\s*([\d,]+\.?\d*)'
        
        best_match = None
        best_value = 0.0
        
        for match in re.finditer(pattern, text_lower, re.MULTILINE):
            keyword = match.group(1)
            amount_str = match.group(2).replace(',', '')
            
            # Skip if it's actually a subtotal
            context_start = max(0, match.start() - 20)
            context = text_lower[context_start:match.start()]
            if any(sub in context for sub in self.SUBTOTAL_KEYWORDS):
                continue
            
            try:
                value = float(amount_str)
                if value > best_value and value > 0:
                    best_value = value
                    best_match = match
            except ValueError:
                continue
        
        if best_match and best_value > 0:
            return DetectorResult(
                detector_name="regex",
                value=best_value,
                confidence=0.85,
                evidence=f"Found after keyword '{best_match.group(1)}' via regex pattern"
            )
        
        return None
    
    def _detect_amount_proximity(
        self, 
        text: str, 
        currency: str
    ) -> Optional[DetectorResult]:
        """Detector 2: Find amount on same line as total keyword."""
        for i, line in enumerate(self.lines):
            line_lower = line.lower()
            
            # Skip subtotals
            if any(sub in line_lower for sub in self.SUBTOTAL_KEYWORDS):
                continue
            
            # Check for total keywords
            has_total_keyword = any(kw in line_lower for kw in self.TOTAL_KEYWORDS)
            
            if has_total_keyword:
                # Extract all amounts from this line
                amounts = re.findall(r'[\d,]+\.?\d*', line)
                
                for amount_str in amounts:
                    try:
                        value = float(amount_str.replace(',', ''))
                        # Skip small values that might be dates/times
                        if value > 0.5 and not self._looks_like_date(amount_str):
                            return DetectorResult(
                                detector_name="proximity",
                                value=value,
                                confidence=0.90,
                                evidence=f"On same line as 'total' keyword (line {i+1})",
                                position=(i, line.find(amount_str))
                            )
                    except ValueError:
                        continue
        
        return None
    
    def _detect_amount_position(
        self, 
        text: str, 
        currency: str
    ) -> Optional[DetectorResult]:
        """Detector 3: Find prominent amount in footer zone."""
        # Footer zone: bottom 20% of document
        footer_start = int(self.total_lines * self.FOOTER_ZONE_START)
        
        footer_amounts: list[tuple[float, int, str]] = []  # (value, line, evidence)
        
        for i in range(footer_start, self.total_lines):
            line = self.lines[i]
            
            # Skip subtotals
            if any(sub in line.lower() for sub in self.SUBTOTAL_KEYWORDS):
                continue
            
            amounts = re.findall(r'[\d,]+\.?\d*', line)
            for amount_str in amounts:
                try:
                    value = float(amount_str.replace(',', ''))
                    if value > 0.5 and not self._looks_like_date(amount_str):
                        footer_amounts.append((value, i, f"Footer zone line {i+1}"))
                except ValueError:
                    continue
        
        if footer_amounts:
            # Return largest amount in footer
            best = max(footer_amounts, key=lambda x: x[0])
            return DetectorResult(
                detector_name="position",
                value=best[0],
                confidence=0.75,
                evidence=f"Largest amount in footer zone ({best[2]})",
                position=(best[1], 0)
            )
        
        return None
    
    def _detect_amount_statistical(
        self, 
        text: str, 
        currency: str
    ) -> Optional[DetectorResult]:
        """Detector 4: Find statistically prominent amount."""
        all_amounts: list[float] = []
        
        for line in self.lines:
            # Skip lines with subtotal
            if any(sub in line.lower() for sub in self.SUBTOTAL_KEYWORDS):
                continue
                
            amounts = re.findall(r'[\d,]+\.?\d*', line)
            for amount_str in amounts:
                try:
                    value = float(amount_str.replace(',', ''))
                    # Filter reasonable receipt/invoice amounts
                    if 0.5 < value < 10000000 and not self._looks_like_date(amount_str):
                        all_amounts.append(value)
                except ValueError:
                    continue
        
        if not all_amounts:
            return None
        
        # Strategy: largest amount is often the total
        largest = max(all_amounts)
        
        # Additional check: is it significantly larger than others?
        if len(all_amounts) > 1:
            sorted_amounts = sorted(all_amounts, reverse=True)
            second_largest = sorted_amounts[1] if len(sorted_amounts) > 1 else 0
            
            # If largest is much bigger, it's likely the total
            if largest > second_largest * 1.5:
                confidence = 0.80
            else:
                confidence = 0.60
        else:
            confidence = 0.70
        
        return DetectorResult(
            detector_name="statistical",
            value=largest,
            confidence=confidence,
            evidence=f"Largest amount in document ({largest})"
        )
    
    def _looks_like_date(self, s: str) -> bool:
        """Check if string looks like a date component."""
        # Years
        try:
            v = float(s.replace(',', ''))
            if 1900 <= v <= 2100:
                return True
        except ValueError:
            pass
        return False
    
    # ==================== DATE EXTRACTION ====================
    
    def extract_date(self, text: str) -> ConsensusResult:
        """
        Extract document date using 4 independent detectors.
        
        Detectors:
        1. Regex: Standard date patterns
        2. Proximity: Near 'date' keyword
        3. Position: Header zone (top 15%)
        4. Statistical: Most recent reasonable date
        """
        self.lines = text.split('\n')
        self.total_lines = len(self.lines)
        
        detector_results: list[DetectorResult] = []
        
        # Detector 1: Regex patterns
        regex_result = self._detect_date_regex(text)
        if regex_result:
            detector_results.append(regex_result)
        
        # Detector 2: Keyword proximity
        proximity_result = self._detect_date_proximity(text)
        if proximity_result:
            detector_results.append(proximity_result)
        
        # Detector 3: Header position
        position_result = self._detect_date_position(text)
        if position_result:
            detector_results.append(position_result)
        
        # Detector 4: Statistical (most recent)
        statistical_result = self._detect_date_statistical(text)
        if statistical_result:
            detector_results.append(statistical_result)
        
        return self._build_consensus("date", detector_results)
    
    def _detect_date_regex(self, text: str) -> Optional[DetectorResult]:
        """Detector 1: Find date using regex patterns."""
        patterns = [
            # YYYY-MM-DD (ISO)
            (r'(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})', 'YMD'),
            # DD/MM/YYYY
            (r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})', 'DMY'),
            # Month name formats
            (r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[,.]?\s+(\d{4})', 'D_Mon_Y'),
        ]
        
        for pattern, fmt in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                normalized = self._normalize_date(match.groups(), fmt)
                if normalized:
                    return DetectorResult(
                        detector_name="regex",
                        value=normalized,
                        confidence=0.85,
                        evidence=f"Matched {fmt} pattern: {match.group(0)}"
                    )
        
        return None
    
    def _detect_date_proximity(self, text: str) -> Optional[DetectorResult]:
        """Detector 2: Find date near 'date' keyword."""
        for i, line in enumerate(self.lines):
            line_lower = line.lower()
            
            if 'date' in line_lower or 'dated' in line_lower:
                # Look for date on this line or next
                search_text = line
                if i + 1 < len(self.lines):
                    search_text += ' ' + self.lines[i + 1]
                
                # Try to extract date
                patterns = [
                    (r'(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})', 'YMD'),
                    (r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})', 'DMY'),
                    (r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{2})\b', 'DMY_short'),
                ]
                
                for pattern, fmt in patterns:
                    match = re.search(pattern, search_text)
                    if match:
                        normalized = self._normalize_date(match.groups(), fmt)
                        if normalized:
                            return DetectorResult(
                                detector_name="proximity",
                                value=normalized,
                                confidence=0.90,
                                evidence=f"Near 'date' keyword on line {i+1}",
                                position=(i, 0)
                            )
        
        return None
    
    def _detect_date_position(self, text: str) -> Optional[DetectorResult]:
        """Detector 3: Find date in header zone."""
        header_end = int(self.total_lines * self.HEADER_ZONE_END)
        header_end = max(header_end, 5)  # At least 5 lines
        
        patterns = [
            (r'(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})', 'YMD'),
            (r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})', 'DMY'),
        ]
        
        for i in range(min(header_end, len(self.lines))):
            line = self.lines[i]
            for pattern, fmt in patterns:
                match = re.search(pattern, line)
                if match:
                    normalized = self._normalize_date(match.groups(), fmt)
                    if normalized:
                        return DetectorResult(
                            detector_name="position",
                            value=normalized,
                            confidence=0.75,
                            evidence=f"In header zone (line {i+1})",
                            position=(i, 0)
                        )
        
        return None
    
    def _detect_date_statistical(self, text: str) -> Optional[DetectorResult]:
        """Detector 4: Find most recent reasonable date."""
        all_dates: list[tuple[str, str]] = []  # (normalized, original)
        
        patterns = [
            (r'(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})', 'YMD'),
            (r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})', 'DMY'),
        ]
        
        for pattern, fmt in patterns:
            for match in re.finditer(pattern, text):
                normalized = self._normalize_date(match.groups(), fmt)
                if normalized:
                    all_dates.append((normalized, match.group(0)))
        
        if not all_dates:
            return None
        
        # Return most recent date (assuming recent documents)
        all_dates.sort(reverse=True)
        best = all_dates[0]
        
        return DetectorResult(
            detector_name="statistical",
            value=best[0],
            confidence=0.65,
            evidence=f"Most recent date found: {best[1]}"
        )
    
    def _normalize_date(self, groups: tuple, fmt: str) -> Optional[str]:
        """Normalize date to YYYY-MM-DD format."""
        try:
            if fmt == 'YMD':
                year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
            elif fmt == 'DMY':
                day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
            elif fmt == 'DMY_short':
                day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                year = 2000 + year if year < 50 else 1900 + year
            elif fmt == 'D_Mon_Y':
                day = int(groups[0])
                month = self._month_to_num(groups[1])
                year = int(groups[2])
            else:
                return None
            
            # Validate
            if not (1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= 2100):
                return None
            
            return f"{year:04d}-{month:02d}-{day:02d}"
        except (ValueError, IndexError):
            return None
    
    def _month_to_num(self, name: str) -> int:
        """Convert month name to number."""
        months = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
            'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
            'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        return months.get(name.lower()[:3], 0)
    
    # ==================== VENDOR EXTRACTION ====================
    
    def extract_vendor(self, text: str) -> ConsensusResult:
        """
        Extract vendor/business name using 4 independent detectors.
        
        Detectors:
        1. Regex: Look for business suffixes (Ltd, Inc, LLC)
        2. Proximity: Near receipt/invoice header
        3. Position: Header zone, first prominent line
        4. Statistical: Most capitalized/prominent text
        """
        self.lines = text.split('\n')
        self.total_lines = len(self.lines)
        
        detector_results: list[DetectorResult] = []
        
        # Detector 1: Business name patterns
        regex_result = self._detect_vendor_regex(text)
        if regex_result:
            detector_results.append(regex_result)
        
        # Detector 2: Header proximity
        proximity_result = self._detect_vendor_proximity(text)
        if proximity_result:
            detector_results.append(proximity_result)
        
        # Detector 3: Position-based
        position_result = self._detect_vendor_position(text)
        if position_result:
            detector_results.append(position_result)
        
        # Detector 4: Statistical (most prominent)
        statistical_result = self._detect_vendor_statistical(text)
        if statistical_result:
            detector_results.append(statistical_result)
        
        return self._build_consensus("vendor", detector_results)
    
    def _detect_vendor_regex(self, text: str) -> Optional[DetectorResult]:
        """Detector 1: Find vendor using business name patterns."""
        # Business suffixes
        suffixes = r'\b(Ltd|Limited|Inc|LLC|Corp|Corporation|Co\.|Company|PLC|LLP)\b'
        
        for i, line in enumerate(self.lines):
            if re.search(suffixes, line, re.IGNORECASE):
                clean_name = line.strip()
                if len(clean_name) > 3:
                    return DetectorResult(
                        detector_name="regex",
                        value=clean_name,
                        confidence=0.90,
                        evidence=f"Contains business suffix on line {i+1}",
                        position=(i, 0)
                    )
        
        return None
    
    def _detect_vendor_proximity(self, text: str) -> Optional[DetectorResult]:
        """Detector 2: Find vendor near document header."""
        # First non-empty, non-date, non-number line
        for i, line in enumerate(self.lines[:10]):
            line = line.strip()
            
            if len(line) < 3:
                continue
            
            # Skip if matches skip patterns
            skip = False
            for pattern in self.VENDOR_SKIP_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    skip = True
                    break
            
            if skip:
                continue
            
            # Must contain letters
            if not re.search(r'[a-zA-Z]', line):
                continue
            
            return DetectorResult(
                detector_name="proximity",
                value=line,
                confidence=0.80,
                evidence=f"First valid text in header (line {i+1})",
                position=(i, 0)
            )
        
        return None
    
    def _detect_vendor_position(self, text: str) -> Optional[DetectorResult]:
        """Detector 3: Find vendor in top 15% using position rules."""
        header_end = int(self.total_lines * self.HEADER_ZONE_END)
        header_end = max(header_end, 5)
        
        for i in range(min(header_end, len(self.lines))):
            line = self.lines[i].strip()
            
            if len(line) < 4:
                continue
            
            # Preference for ALL CAPS lines (often business names)
            if line.isupper() and re.search(r'[A-Z]', line):
                return DetectorResult(
                    detector_name="position",
                    value=line,
                    confidence=0.85,
                    evidence=f"All-caps header in top 15% (line {i+1})",
                    position=(i, 0)
                )
        
        # Fallback: first reasonable line in header
        for i in range(min(header_end, len(self.lines))):
            line = self.lines[i].strip()
            if len(line) > 3 and re.search(r'[a-zA-Z]', line):
                skip = any(re.search(p, line, re.IGNORECASE) for p in self.VENDOR_SKIP_PATTERNS)
                if not skip:
                    return DetectorResult(
                        detector_name="position",
                        value=line,
                        confidence=0.70,
                        evidence=f"In header zone (line {i+1})",
                        position=(i, 0)
                    )
        
        return None
    
    def _detect_vendor_statistical(self, text: str) -> Optional[DetectorResult]:
        """Detector 4: Find most prominent/capitalized vendor name."""
        candidates: list[tuple[str, float]] = []  # (name, score)
        
        for i, line in enumerate(self.lines[:15]):
            line = line.strip()
            
            if len(line) < 3:
                continue
            
            # Skip patterns
            skip = any(re.search(p, line, re.IGNORECASE) for p in self.VENDOR_SKIP_PATTERNS)
            if skip:
                continue
            
            # Score based on characteristics
            score = 0.0
            
            # All caps bonus
            if line.isupper():
                score += 0.3
            
            # Contains business keywords
            if re.search(r'\b(store|shop|market|restaurant|cafe|hotel|bank)\b', line, re.IGNORECASE):
                score += 0.2
            
            # Length bonus (but not too long)
            if 5 <= len(line) <= 40:
                score += 0.1
            
            # Position bonus (earlier = better)
            position_score = (15 - i) / 15 * 0.2
            score += position_score
            
            if score > 0:
                candidates.append((line, score))
        
        if candidates:
            best = max(candidates, key=lambda x: x[1])
            return DetectorResult(
                detector_name="statistical",
                value=best[0],
                confidence=0.65,
                evidence=f"Highest prominence score ({best[1]:.2f})"
            )
        
        return None
    
    # ==================== CONSENSUS LOGIC ====================
    
    def _build_consensus(
        self, 
        field_name: str, 
        detector_results: list[DetectorResult]
    ) -> ConsensusResult:
        """
        Build consensus from multiple detector results.
        
        Voting rules:
        - 3+ agree → STRONG consensus, accept value
        - 2 agree → MODERATE consensus, accept but flag
        - <2 agree → WEAK consensus, request confirmation
        """
        if not detector_results:
            return ConsensusResult(
                field_name=field_name,
                final_value=None,
                consensus_level=ConsensusLevel.NONE,
                agreement_count=0,
                total_detectors=0,
                detector_results=[],
                agreeing_detectors=[],
                dissenting_detectors=[],
                all_candidates=[],
                needs_confirmation=True,
                confirmation_reason=f"No {field_name} candidates detected"
            )
        
        # Count votes for each unique value
        vote_counts: dict[Any, list[str]] = {}  # value -> list of detector names
        
        for result in detector_results:
            # Normalize value for comparison
            value = self._normalize_for_comparison(result.value)
            
            if value not in vote_counts:
                vote_counts[value] = []
            vote_counts[value].append(result.detector_name)
        
        # Find the value with most votes
        all_candidates = [(v, len(detectors)) for v, detectors in vote_counts.items()]
        all_candidates.sort(key=lambda x: x[1], reverse=True)
        
        if not all_candidates:
            return ConsensusResult(
                field_name=field_name,
                final_value=None,
                consensus_level=ConsensusLevel.NONE,
                agreement_count=0,
                total_detectors=len(detector_results),
                detector_results=detector_results,
                agreeing_detectors=[],
                dissenting_detectors=[d.detector_name for d in detector_results],
                all_candidates=[],
                needs_confirmation=True,
                confirmation_reason=f"Could not parse {field_name} values"
            )
        
        best_value, best_count = all_candidates[0]
        agreeing = vote_counts[best_value]
        dissenting = [d.detector_name for d in detector_results if d.detector_name not in agreeing]
        
        # Determine consensus level
        total = len(detector_results)
        
        if best_count >= self.STRONG_CONSENSUS_THRESHOLD:
            level = ConsensusLevel.STRONG
            needs_confirmation = False
            reason = None
        elif best_count >= self.MODERATE_CONSENSUS_THRESHOLD:
            level = ConsensusLevel.MODERATE
            needs_confirmation = False
            reason = None
        else:
            level = ConsensusLevel.WEAK
            needs_confirmation = True
            
            # Explain why confirmation is needed
            if len(all_candidates) > 1:
                reason = f"Conflicting values detected: {[c[0] for c in all_candidates[:3]]}"
            else:
                reason = f"Only {best_count} detector(s) found this value"
        
        # Get original (non-normalized) value for output
        final_value = None
        for result in detector_results:
            if self._normalize_for_comparison(result.value) == best_value:
                final_value = result.value
                break
        
        return ConsensusResult(
            field_name=field_name,
            final_value=final_value,
            consensus_level=level,
            agreement_count=best_count,
            total_detectors=total,
            detector_results=detector_results,
            agreeing_detectors=agreeing,
            dissenting_detectors=dissenting,
            all_candidates=all_candidates,
            needs_confirmation=needs_confirmation,
            confirmation_reason=reason
        )
    
    def _normalize_for_comparison(self, value: Any) -> Any:
        """Normalize value for comparison across detectors."""
        if value is None:
            return None
        
        if isinstance(value, float):
            # Round to 2 decimal places for amount comparison
            return round(value, 2)
        
        if isinstance(value, str):
            # Normalize strings (case-insensitive, trimmed)
            return value.strip().lower()
        
        return value


def extract_with_consensus(
    text: str,
    currency: str = "KES"
) -> dict[str, ConsensusResult]:
    """
    Convenience function to extract all fields with consensus.
    
    Args:
        text: OCR text to extract from
        currency: Default currency code
        
    Returns:
        Dictionary of field_name -> ConsensusResult
    """
    extractor = ConsensusExtractor()
    
    return {
        "total_amount": extractor.extract_total_amount(text, currency),
        "date": extractor.extract_date(text),
        "vendor": extractor.extract_vendor(text)
    }
