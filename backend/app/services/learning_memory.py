"""Learning Memory System for SMELens

Lightweight learning memory (NOT an ML model) that:
- Stores document fingerprints (layout + keywords)
- Stores confirmed field positions
- Stores user corrections
- Stores vendor/document-specific rules

On new scans:
- Matches against past fingerprints
- Reuses known layouts
- Boosts confidence automatically

This improves accuracy over time for repeated documents.
"""
import os
import json
import hashlib
import logging
from typing import Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class DocumentFingerprint:
    """
    Fingerprint of a document's layout and characteristics.
    
    Used to match similar documents for learning.
    """
    # Layout features
    line_count: int
    header_keywords: list[str]
    footer_keywords: list[str]
    has_table: bool
    approximate_word_count: int
    
    # Document characteristics
    document_type: str
    vendor_name: Optional[str]
    currency: str
    
    # Computed hash
    fingerprint_hash: str = ""
    
    def __post_init__(self):
        """Compute fingerprint hash after initialization."""
        if not self.fingerprint_hash:
            self.fingerprint_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute a hash representing this fingerprint."""
        components = [
            str(self.line_count // 5 * 5),  # Bucket by 5 lines
            ','.join(sorted(self.header_keywords[:5])),
            self.document_type,
            self.vendor_name or '',
        ]
        content = '|'.join(components)
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def similarity_score(self, other: 'DocumentFingerprint') -> float:
        """
        Calculate similarity with another fingerprint.
        
        Returns:
            Similarity score (0.0 - 1.0)
        """
        score = 0.0
        
        # Exact hash match
        if self.fingerprint_hash == other.fingerprint_hash:
            return 1.0
        
        # Same document type
        if self.document_type == other.document_type:
            score += 0.3
        
        # Same vendor
        if self.vendor_name and other.vendor_name:
            if self.vendor_name.lower() == other.vendor_name.lower():
                score += 0.4
        
        # Similar line count (within 20%)
        if self.line_count > 0 and other.line_count > 0:
            ratio = min(self.line_count, other.line_count) / max(self.line_count, other.line_count)
            if ratio > 0.8:
                score += 0.1
        
        # Shared header keywords
        shared_keywords = set(self.header_keywords) & set(other.header_keywords)
        if shared_keywords:
            score += len(shared_keywords) * 0.05
        
        # Same currency
        if self.currency == other.currency:
            score += 0.05
        
        return min(score, 1.0)


@dataclass
class FieldPosition:
    """Remembered position of a field in a document layout."""
    field_name: str
    zone: str  # "header", "body", "footer"
    line_percentage: float  # Position as % of document (0.0 - 1.0)
    alignment: str  # "left", "center", "right"
    near_keywords: list[str]
    confidence_boost: float = 0.1  # How much to boost confidence


@dataclass
class UserCorrection:
    """A stored user correction."""
    field_name: str
    original_value: Any
    corrected_value: Any
    document_type: str
    vendor_name: Optional[str]
    timestamp: str
    correction_count: int = 1  # How many times this correction was made


@dataclass
class VendorRule:
    """Vendor-specific extraction rule."""
    vendor_name: str
    field_name: str
    extraction_hint: str  # e.g., "line_after_TOTAL"
    expected_format: str  # e.g., "###.##"
    confidence_boost: float = 0.15


@dataclass
class LearningMemoryEntry:
    """A complete learning memory entry for a document pattern."""
    fingerprint: DocumentFingerprint
    field_positions: list[FieldPosition]
    corrections: list[UserCorrection]
    vendor_rules: list[VendorRule]
    
    # Statistics
    times_seen: int = 1
    times_confirmed: int = 0
    last_seen: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    first_seen: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'fingerprint': asdict(self.fingerprint),
            'field_positions': [asdict(fp) for fp in self.field_positions],
            'corrections': [asdict(c) for c in self.corrections],
            'vendor_rules': [asdict(vr) for vr in self.vendor_rules],
            'times_seen': self.times_seen,
            'times_confirmed': self.times_confirmed,
            'last_seen': self.last_seen,
            'first_seen': self.first_seen
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'LearningMemoryEntry':
        """Create from dictionary."""
        return cls(
            fingerprint=DocumentFingerprint(**data['fingerprint']),
            field_positions=[FieldPosition(**fp) for fp in data.get('field_positions', [])],
            corrections=[UserCorrection(**c) for c in data.get('corrections', [])],
            vendor_rules=[VendorRule(**vr) for vr in data.get('vendor_rules', [])],
            times_seen=data.get('times_seen', 1),
            times_confirmed=data.get('times_confirmed', 0),
            last_seen=data.get('last_seen', datetime.utcnow().isoformat()),
            first_seen=data.get('first_seen', datetime.utcnow().isoformat())
        )


@dataclass
class MemoryMatchResult:
    """Result of matching against learning memory."""
    found_match: bool
    match_score: float  # How well it matches (0.0 - 1.0)
    entry: Optional[LearningMemoryEntry]
    confidence_boost: float  # How much to boost confidence
    field_hints: dict[str, Any]  # Hints for extraction
    explanation: str


class LearningMemory:
    """
    Persistent learning memory for document patterns.
    
    Stores and retrieves learned patterns to improve
    extraction accuracy over time.
    """
    
    # Similarity threshold for matching
    MATCH_THRESHOLD = 0.6
    
    # Maximum entries to store
    MAX_ENTRIES = 1000
    
    # Confidence boost for known patterns
    KNOWN_PATTERN_BOOST = 0.15
    CONFIRMED_PATTERN_BOOST = 0.25
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize learning memory.
        
        Args:
            storage_path: Path to store learning data (default: ./learning_memory.json)
        """
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            # Default to backend uploads directory
            self.storage_path = Path(__file__).parent.parent.parent / "uploads" / "learning_memory.json"
        
        self.entries: dict[str, LearningMemoryEntry] = {}
        self.vendor_index: dict[str, list[str]] = {}  # vendor -> list of fingerprint hashes
        
        self._load()
    
    def _load(self) -> None:
        """Load learning memory from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                
                for hash_key, entry_data in data.get('entries', {}).items():
                    entry = LearningMemoryEntry.from_dict(entry_data)
                    self.entries[hash_key] = entry
                    
                    # Build vendor index
                    if entry.fingerprint.vendor_name:
                        vendor_lower = entry.fingerprint.vendor_name.lower()
                        if vendor_lower not in self.vendor_index:
                            self.vendor_index[vendor_lower] = []
                        self.vendor_index[vendor_lower].append(hash_key)
                
                logger.info(f"LearningMemory: Loaded {len(self.entries)} entries")
            except Exception as e:
                logger.warning(f"LearningMemory: Could not load - {e}")
                self.entries = {}
                self.vendor_index = {}
        else:
            logger.info("LearningMemory: No existing data, starting fresh")
    
    def _save(self) -> None:
        """Save learning memory to storage."""
        try:
            # Ensure directory exists
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'version': '1.0',
                'updated_at': datetime.utcnow().isoformat(),
                'entries': {k: v.to_dict() for k, v in self.entries.items()}
            }
            
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"LearningMemory: Saved {len(self.entries)} entries")
        except Exception as e:
            logger.error(f"LearningMemory: Could not save - {e}")
    
    def create_fingerprint(
        self,
        text: str,
        document_type: str,
        vendor_name: Optional[str] = None,
        currency: str = "KES",
        has_table: bool = False
    ) -> DocumentFingerprint:
        """
        Create a fingerprint from document text.
        
        Args:
            text: Document text
            document_type: Type of document
            vendor_name: Vendor name if known
            currency: Currency code
            has_table: Whether document has detected tables
            
        Returns:
            DocumentFingerprint
        """
        lines = text.split('\n')
        line_count = len(lines)
        word_count = len(text.split())
        
        # Extract header keywords (top 15%)
        header_end = max(int(line_count * 0.15), 3)
        header_text = ' '.join(lines[:header_end]).lower()
        header_keywords = self._extract_keywords(header_text)
        
        # Extract footer keywords (bottom 20%)
        footer_start = int(line_count * 0.80)
        footer_text = ' '.join(lines[footer_start:]).lower()
        footer_keywords = self._extract_keywords(footer_text)
        
        return DocumentFingerprint(
            line_count=line_count,
            header_keywords=header_keywords,
            footer_keywords=footer_keywords,
            has_table=has_table,
            approximate_word_count=word_count,
            document_type=document_type,
            vendor_name=vendor_name,
            currency=currency
        )
    
    def _extract_keywords(self, text: str, max_keywords: int = 10) -> list[str]:
        """Extract significant keywords from text."""
        # Remove numbers and short words
        words = text.split()
        filtered = [
            w for w in words 
            if len(w) > 3 and not w.isdigit() and w.isalpha()
        ]
        
        # Get most common
        counter = Counter(filtered)
        return [word for word, _ in counter.most_common(max_keywords)]
    
    def find_match(
        self,
        fingerprint: DocumentFingerprint
    ) -> MemoryMatchResult:
        """
        Find a matching pattern in memory.
        
        Args:
            fingerprint: Fingerprint of current document
            
        Returns:
            MemoryMatchResult with match details
        """
        best_match: Optional[LearningMemoryEntry] = None
        best_score = 0.0
        
        # First, check exact hash match
        if fingerprint.fingerprint_hash in self.entries:
            entry = self.entries[fingerprint.fingerprint_hash]
            best_match = entry
            best_score = 1.0
            logger.info(f"LearningMemory: Exact hash match found")
        else:
            # Check vendor index for faster matching
            candidates = []
            
            if fingerprint.vendor_name:
                vendor_lower = fingerprint.vendor_name.lower()
                if vendor_lower in self.vendor_index:
                    for hash_key in self.vendor_index[vendor_lower]:
                        if hash_key in self.entries:
                            candidates.append(self.entries[hash_key])
            
            # Also check similar fingerprints
            for entry in self.entries.values():
                if entry not in candidates:
                    score = fingerprint.similarity_score(entry.fingerprint)
                    if score >= self.MATCH_THRESHOLD:
                        candidates.append(entry)
            
            # Find best match among candidates
            for entry in candidates:
                score = fingerprint.similarity_score(entry.fingerprint)
                if score > best_score:
                    best_score = score
                    best_match = entry
        
        if best_match and best_score >= self.MATCH_THRESHOLD:
            # Calculate confidence boost
            if best_score >= 0.95:
                boost = self.CONFIRMED_PATTERN_BOOST if best_match.times_confirmed > 0 else self.KNOWN_PATTERN_BOOST
            else:
                boost = self.KNOWN_PATTERN_BOOST * best_score
            
            # Extract field hints
            field_hints = {}
            for fp in best_match.field_positions:
                field_hints[fp.field_name] = {
                    'zone': fp.zone,
                    'line_percentage': fp.line_percentage,
                    'near_keywords': fp.near_keywords
                }
            
            # Apply vendor rules
            for vr in best_match.vendor_rules:
                if vr.field_name not in field_hints:
                    field_hints[vr.field_name] = {}
                field_hints[vr.field_name]['extraction_hint'] = vr.extraction_hint
                field_hints[vr.field_name]['expected_format'] = vr.expected_format
            
            explanation = f"Matched known pattern (seen {best_match.times_seen} times"
            if best_match.times_confirmed > 0:
                explanation += f", confirmed {best_match.times_confirmed} times"
            explanation += ")"
            
            return MemoryMatchResult(
                found_match=True,
                match_score=best_score,
                entry=best_match,
                confidence_boost=boost,
                field_hints=field_hints,
                explanation=explanation
            )
        
        return MemoryMatchResult(
            found_match=False,
            match_score=0.0,
            entry=None,
            confidence_boost=0.0,
            field_hints={},
            explanation="No matching pattern in memory"
        )
    
    def learn_from_document(
        self,
        fingerprint: DocumentFingerprint,
        extracted_fields: dict[str, Any],
        field_positions: Optional[dict[str, dict]] = None,
        user_confirmed: bool = False
    ) -> None:
        """
        Learn from a processed document.
        
        Args:
            fingerprint: Document fingerprint
            extracted_fields: Successfully extracted fields
            field_positions: Position information for fields
            user_confirmed: Whether user confirmed the extraction
        """
        hash_key = fingerprint.fingerprint_hash
        
        if hash_key in self.entries:
            # Update existing entry
            entry = self.entries[hash_key]
            entry.times_seen += 1
            entry.last_seen = datetime.utcnow().isoformat()
            
            if user_confirmed:
                entry.times_confirmed += 1
        else:
            # Create new entry
            positions = []
            if field_positions:
                for field_name, pos_info in field_positions.items():
                    positions.append(FieldPosition(
                        field_name=field_name,
                        zone=pos_info.get('zone', 'body'),
                        line_percentage=pos_info.get('line_percentage', 0.5),
                        alignment=pos_info.get('alignment', 'left'),
                        near_keywords=pos_info.get('near_keywords', [])
                    ))
            
            entry = LearningMemoryEntry(
                fingerprint=fingerprint,
                field_positions=positions,
                corrections=[],
                vendor_rules=[],
                times_seen=1,
                times_confirmed=1 if user_confirmed else 0
            )
            
            self.entries[hash_key] = entry
            
            # Update vendor index
            if fingerprint.vendor_name:
                vendor_lower = fingerprint.vendor_name.lower()
                if vendor_lower not in self.vendor_index:
                    self.vendor_index[vendor_lower] = []
                if hash_key not in self.vendor_index[vendor_lower]:
                    self.vendor_index[vendor_lower].append(hash_key)
        
        # Enforce max entries limit
        if len(self.entries) > self.MAX_ENTRIES:
            self._prune_old_entries()
        
        self._save()
        logger.info(f"LearningMemory: Learned from document (hash={hash_key[:8]}...)")
    
    def record_correction(
        self,
        fingerprint: DocumentFingerprint,
        field_name: str,
        original_value: Any,
        corrected_value: Any
    ) -> None:
        """
        Record a user correction for learning.
        
        Args:
            fingerprint: Document fingerprint
            field_name: Name of corrected field
            original_value: Original extracted value
            corrected_value: User's corrected value
        """
        hash_key = fingerprint.fingerprint_hash
        
        if hash_key in self.entries:
            entry = self.entries[hash_key]
            
            # Check if this correction already exists
            existing = None
            for c in entry.corrections:
                if (c.field_name == field_name and 
                    str(c.original_value) == str(original_value)):
                    existing = c
                    break
            
            if existing:
                existing.corrected_value = corrected_value
                existing.correction_count += 1
                existing.timestamp = datetime.utcnow().isoformat()
            else:
                entry.corrections.append(UserCorrection(
                    field_name=field_name,
                    original_value=original_value,
                    corrected_value=corrected_value,
                    document_type=fingerprint.document_type,
                    vendor_name=fingerprint.vendor_name,
                    timestamp=datetime.utcnow().isoformat()
                ))
            
            self._save()
            logger.info(f"LearningMemory: Recorded correction for {field_name}")
    
    def add_vendor_rule(
        self,
        vendor_name: str,
        field_name: str,
        extraction_hint: str,
        expected_format: str = ""
    ) -> None:
        """
        Add a vendor-specific extraction rule.
        
        Args:
            vendor_name: Vendor name
            field_name: Field this rule applies to
            extraction_hint: Hint for extraction (e.g., "line_after_TOTAL")
            expected_format: Expected value format
        """
        vendor_lower = vendor_name.lower()
        
        # Find or create entry for this vendor
        if vendor_lower in self.vendor_index and self.vendor_index[vendor_lower]:
            hash_key = self.vendor_index[vendor_lower][0]
            if hash_key in self.entries:
                entry = self.entries[hash_key]
                
                # Check if rule already exists
                existing = None
                for vr in entry.vendor_rules:
                    if vr.field_name == field_name:
                        existing = vr
                        break
                
                if existing:
                    existing.extraction_hint = extraction_hint
                    existing.expected_format = expected_format
                else:
                    entry.vendor_rules.append(VendorRule(
                        vendor_name=vendor_name,
                        field_name=field_name,
                        extraction_hint=extraction_hint,
                        expected_format=expected_format
                    ))
                
                self._save()
                logger.info(f"LearningMemory: Added rule for {vendor_name}/{field_name}")
    
    def get_common_corrections(
        self,
        document_type: Optional[str] = None,
        vendor_name: Optional[str] = None,
        min_count: int = 2
    ) -> list[UserCorrection]:
        """
        Get frequently made corrections.
        
        Args:
            document_type: Filter by document type
            vendor_name: Filter by vendor
            min_count: Minimum correction count
            
        Returns:
            List of common corrections
        """
        corrections = []
        
        for entry in self.entries.values():
            for c in entry.corrections:
                if c.correction_count < min_count:
                    continue
                
                if document_type and c.document_type != document_type:
                    continue
                
                if vendor_name and c.vendor_name and c.vendor_name.lower() != vendor_name.lower():
                    continue
                
                corrections.append(c)
        
        return sorted(corrections, key=lambda c: c.correction_count, reverse=True)
    
    def _prune_old_entries(self) -> None:
        """Remove old, less-used entries to stay under limit."""
        if len(self.entries) <= self.MAX_ENTRIES:
            return
        
        # Sort by usefulness (times_seen + times_confirmed * 2)
        sorted_entries = sorted(
            self.entries.items(),
            key=lambda x: x[1].times_seen + x[1].times_confirmed * 2,
            reverse=True
        )
        
        # Keep top entries
        keep = dict(sorted_entries[:self.MAX_ENTRIES])
        removed = set(self.entries.keys()) - set(keep.keys())
        
        self.entries = keep
        
        # Clean up vendor index
        for vendor, hashes in self.vendor_index.items():
            self.vendor_index[vendor] = [h for h in hashes if h not in removed]
        
        logger.info(f"LearningMemory: Pruned {len(removed)} old entries")
    
    def get_statistics(self) -> dict[str, Any]:
        """Get learning memory statistics."""
        total_entries = len(self.entries)
        total_corrections = sum(
            len(e.corrections) for e in self.entries.values()
        )
        total_rules = sum(
            len(e.vendor_rules) for e in self.entries.values()
        )
        
        vendors = set()
        for e in self.entries.values():
            if e.fingerprint.vendor_name:
                vendors.add(e.fingerprint.vendor_name.lower())
        
        return {
            "total_patterns": total_entries,
            "unique_vendors": len(vendors),
            "total_corrections": total_corrections,
            "total_vendor_rules": total_rules,
            "storage_path": str(self.storage_path)
        }


# Global instance for shared memory
_global_memory: Optional[LearningMemory] = None


def get_learning_memory() -> LearningMemory:
    """Get the global learning memory instance."""
    global _global_memory
    if _global_memory is None:
        _global_memory = LearningMemory()
    return _global_memory


def apply_learning_memory(
    text: str,
    document_type: str,
    vendor_name: Optional[str] = None,
    currency: str = "KES"
) -> MemoryMatchResult:
    """
    Convenience function to apply learning memory.
    
    Args:
        text: Document text
        document_type: Type of document
        vendor_name: Vendor name if known
        currency: Currency code
        
    Returns:
        MemoryMatchResult with match details and hints
    """
    memory = get_learning_memory()
    fingerprint = memory.create_fingerprint(
        text=text,
        document_type=document_type,
        vendor_name=vendor_name,
        currency=currency
    )
    return memory.find_match(fingerprint)
