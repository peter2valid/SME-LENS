"""Human-in-the-Loop Confirmation System for SMELens

Intelligent user confirmation mechanism that:
- Asks users ONLY when confidence < threshold
- Asks when conflicting candidates exist
- Highlights only uncertain fields
- Accepts user corrections
- Persists corrections as ground truth

Never confidently returns wrong data.
When unsure, ask the user.
"""
import logging
from typing import Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class ConfirmationReason(Enum):
    """Reasons why confirmation is requested."""
    LOW_CONFIDENCE = "low_confidence"
    CONFLICTING_VALUES = "conflicting_values"
    MISSING_CRITICAL_FIELD = "missing_critical_field"
    UNUSUAL_VALUE = "unusual_value"
    OCR_QUALITY_POOR = "ocr_quality_poor"
    MULTIPLE_CANDIDATES = "multiple_candidates"


class FieldPriority(Enum):
    """Priority levels for field confirmation."""
    CRITICAL = "critical"    # Must be correct (e.g., total)
    HIGH = "high"           # Important (e.g., date, vendor)
    MEDIUM = "medium"       # Useful (e.g., currency)
    LOW = "low"             # Nice to have


@dataclass
class ConfirmationCandidate:
    """A candidate value for user selection."""
    value: Any
    source: str  # Which detector/method found this
    confidence: float
    evidence: str  # Why this might be correct


@dataclass
class FieldConfirmationRequest:
    """Request for user confirmation on a single field."""
    field_name: str
    display_name: str  # User-friendly name
    current_value: Optional[Any]
    candidates: list[ConfirmationCandidate]
    reason: ConfirmationReason
    reason_text: str
    priority: FieldPriority
    context: str  # Surrounding text for user reference
    allow_custom: bool = True  # Allow user to enter custom value


@dataclass
class ConfirmationRequest:
    """Complete confirmation request for a document."""
    needs_confirmation: bool
    fields: list[FieldConfirmationRequest]
    document_id: str
    document_type: str
    overall_confidence: float
    summary: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON/API response."""
        return {
            "needs_confirmation": self.needs_confirmation,
            "fields": [
                {
                    "field_name": f.field_name,
                    "display_name": f.display_name,
                    "current_value": f.current_value,
                    "candidates": [
                        {
                            "value": c.value,
                            "source": c.source,
                            "confidence": round(c.confidence, 2),
                            "evidence": c.evidence
                        }
                        for c in f.candidates
                    ],
                    "reason": f.reason.value,
                    "reason_text": f.reason_text,
                    "priority": f.priority.value,
                    "context": f.context,
                    "allow_custom": f.allow_custom
                }
                for f in self.fields
            ],
            "document_id": self.document_id,
            "document_type": self.document_type,
            "overall_confidence": round(self.overall_confidence, 2),
            "summary": self.summary,
            "created_at": self.created_at
        }


@dataclass
class UserCorrection:
    """A user's correction for a field."""
    field_name: str
    original_value: Any
    corrected_value: Any
    correction_source: str  # "user_selection" or "user_input"
    selected_candidate_index: Optional[int] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ConfirmationResponse:
    """User's response to confirmation request."""
    document_id: str
    corrections: list[UserCorrection]
    confirmed_as_is: list[str]  # Fields confirmed without changes
    skipped: list[str]  # Fields user chose to skip
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class ConfirmationManager:
    """
    Manages the human-in-the-loop confirmation flow.
    
    Determines when to ask for confirmation and processes
    user responses.
    """
    
    # Confidence thresholds
    CONFIDENCE_THRESHOLD_HIGH = 0.85  # Above this, no confirmation needed
    CONFIDENCE_THRESHOLD_LOW = 0.50   # Below this, always ask
    
    # Field priorities
    FIELD_PRIORITIES = {
        'total_amount': FieldPriority.CRITICAL,
        'date': FieldPriority.HIGH,
        'vendor': FieldPriority.HIGH,
        'currency': FieldPriority.MEDIUM,
        'invoice_number': FieldPriority.HIGH,
        'tax_amount': FieldPriority.MEDIUM,
    }
    
    # Display names for fields
    FIELD_DISPLAY_NAMES = {
        'total_amount': 'Total Amount',
        'date': 'Document Date',
        'vendor': 'Vendor/Business Name',
        'currency': 'Currency',
        'invoice_number': 'Invoice Number',
        'tax_amount': 'Tax Amount',
        'subtotal': 'Subtotal',
    }
    
    def __init__(self):
        """Initialize the confirmation manager."""
        self.pending_confirmations: dict[str, ConfirmationRequest] = {}
    
    def evaluate_extraction(
        self,
        document_id: str,
        document_type: str,
        extracted_fields: dict[str, Any],
        consensus_results: dict[str, Any],
        overall_confidence: float,
        raw_text: str
    ) -> ConfirmationRequest:
        """
        Evaluate extraction results and determine if confirmation is needed.
        
        Args:
            document_id: Unique identifier for the document
            document_type: Type of document (receipt, invoice, etc.)
            extracted_fields: Dictionary of extracted field values
            consensus_results: Results from consensus extraction
            overall_confidence: Overall confidence score (0-1)
            raw_text: Original OCR text for context
            
        Returns:
            ConfirmationRequest indicating what (if anything) needs confirmation
        """
        logger.info(f"ConfirmationManager: Evaluating document {document_id}")
        
        fields_needing_confirmation: list[FieldConfirmationRequest] = []
        
        # Check each field that has consensus results
        for field_name, consensus in consensus_results.items():
            request = self._evaluate_field(
                field_name=field_name,
                consensus=consensus,
                current_value=extracted_fields.get(field_name),
                raw_text=raw_text
            )
            
            if request:
                fields_needing_confirmation.append(request)
        
        # Check for missing critical fields
        critical_fields = ['total_amount', 'date', 'vendor']
        for field_name in critical_fields:
            if field_name not in extracted_fields or extracted_fields[field_name] is None:
                # Check if we already have a request for this field
                if not any(f.field_name == field_name for f in fields_needing_confirmation):
                    fields_needing_confirmation.append(
                        FieldConfirmationRequest(
                            field_name=field_name,
                            display_name=self.FIELD_DISPLAY_NAMES.get(field_name, field_name),
                            current_value=None,
                            candidates=[],
                            reason=ConfirmationReason.MISSING_CRITICAL_FIELD,
                            reason_text=f"Could not extract {field_name}",
                            priority=self.FIELD_PRIORITIES.get(field_name, FieldPriority.MEDIUM),
                            context=self._get_context_for_field(field_name, raw_text),
                            allow_custom=True
                        )
                    )
        
        # Check overall confidence
        if overall_confidence < self.CONFIDENCE_THRESHOLD_LOW and not fields_needing_confirmation:
            # Low confidence but no specific field issues
            # Ask for confirmation on critical fields anyway
            for field_name in critical_fields:
                if extracted_fields.get(field_name) is not None:
                    fields_needing_confirmation.append(
                        FieldConfirmationRequest(
                            field_name=field_name,
                            display_name=self.FIELD_DISPLAY_NAMES.get(field_name, field_name),
                            current_value=extracted_fields.get(field_name),
                            candidates=[
                                ConfirmationCandidate(
                                    value=extracted_fields[field_name],
                                    source="extraction",
                                    confidence=overall_confidence,
                                    evidence="Automatically extracted value"
                                )
                            ],
                            reason=ConfirmationReason.LOW_CONFIDENCE,
                            reason_text=f"Low overall confidence ({overall_confidence:.0%})",
                            priority=self.FIELD_PRIORITIES.get(field_name, FieldPriority.MEDIUM),
                            context=self._get_context_for_field(field_name, raw_text),
                            allow_custom=True
                        )
                    )
        
        # Sort by priority
        fields_needing_confirmation.sort(
            key=lambda f: (
                0 if f.priority == FieldPriority.CRITICAL else
                1 if f.priority == FieldPriority.HIGH else
                2 if f.priority == FieldPriority.MEDIUM else 3
            )
        )
        
        needs_confirmation = len(fields_needing_confirmation) > 0
        
        # Build summary
        if not needs_confirmation:
            summary = "All fields extracted with high confidence."
        elif len(fields_needing_confirmation) == 1:
            summary = f"Please verify: {fields_needing_confirmation[0].display_name}"
        else:
            field_names = [f.display_name for f in fields_needing_confirmation[:3]]
            summary = f"Please verify: {', '.join(field_names)}"
            if len(fields_needing_confirmation) > 3:
                summary += f" and {len(fields_needing_confirmation) - 3} more"
        
        request = ConfirmationRequest(
            needs_confirmation=needs_confirmation,
            fields=fields_needing_confirmation,
            document_id=document_id,
            document_type=document_type,
            overall_confidence=overall_confidence,
            summary=summary
        )
        
        # Store for later
        if needs_confirmation:
            self.pending_confirmations[document_id] = request
        
        logger.info(f"ConfirmationManager: needs_confirmation={needs_confirmation}, "
                   f"fields={len(fields_needing_confirmation)}")
        
        return request
    
    def _evaluate_field(
        self,
        field_name: str,
        consensus: Any,
        current_value: Any,
        raw_text: str
    ) -> Optional[FieldConfirmationRequest]:
        """
        Evaluate a single field for confirmation need.
        
        Args:
            field_name: Name of the field
            consensus: Consensus result for this field
            current_value: Current extracted value
            raw_text: Raw text for context
            
        Returns:
            FieldConfirmationRequest if confirmation needed, else None
        """
        # Handle different consensus result formats
        if hasattr(consensus, 'needs_confirmation') and consensus.needs_confirmation:
            # ConsensusResult object
            candidates = []
            
            if hasattr(consensus, 'all_candidates'):
                for value, votes in consensus.all_candidates[:5]:
                    candidates.append(ConfirmationCandidate(
                        value=value,
                        source=f"{votes} detectors",
                        confidence=votes / max(consensus.total_detectors, 1),
                        evidence=f"Detected by {votes} method(s)"
                    ))
            
            reason = ConfirmationReason.CONFLICTING_VALUES
            reason_text = consensus.confirmation_reason or "Multiple possible values detected"
            
            if hasattr(consensus, 'consensus_level'):
                if str(consensus.consensus_level) == 'ConsensusLevel.WEAK':
                    reason = ConfirmationReason.LOW_CONFIDENCE
                    reason_text = f"Weak consensus ({consensus.agreement_count}/{consensus.total_detectors} agree)"
            
            return FieldConfirmationRequest(
                field_name=field_name,
                display_name=self.FIELD_DISPLAY_NAMES.get(field_name, field_name),
                current_value=current_value,
                candidates=candidates,
                reason=reason,
                reason_text=reason_text,
                priority=self.FIELD_PRIORITIES.get(field_name, FieldPriority.MEDIUM),
                context=self._get_context_for_field(field_name, raw_text),
                allow_custom=True
            )
        
        elif isinstance(consensus, dict):
            # Dictionary format
            if consensus.get('needs_confirmation', False):
                candidates = []
                
                for cand in consensus.get('all_candidates', [])[:5]:
                    if isinstance(cand, dict):
                        candidates.append(ConfirmationCandidate(
                            value=cand.get('value'),
                            source=f"{cand.get('votes', 1)} detectors",
                            confidence=cand.get('confidence', 0.5),
                            evidence=cand.get('evidence', 'Detected value')
                        ))
                    elif isinstance(cand, tuple):
                        candidates.append(ConfirmationCandidate(
                            value=cand[0],
                            source=f"{cand[1]} votes",
                            confidence=cand[1] / 4,  # Assume 4 detectors
                            evidence=f"Detected by {cand[1]} method(s)"
                        ))
                
                return FieldConfirmationRequest(
                    field_name=field_name,
                    display_name=self.FIELD_DISPLAY_NAMES.get(field_name, field_name),
                    current_value=current_value,
                    candidates=candidates,
                    reason=ConfirmationReason(consensus.get('reason', 'low_confidence')),
                    reason_text=consensus.get('reason_text', 'Please verify this value'),
                    priority=self.FIELD_PRIORITIES.get(field_name, FieldPriority.MEDIUM),
                    context=self._get_context_for_field(field_name, raw_text),
                    allow_custom=True
                )
        
        return None
    
    def _get_context_for_field(
        self,
        field_name: str,
        raw_text: str,
        context_lines: int = 3
    ) -> str:
        """
        Get surrounding text context for a field.
        
        Args:
            field_name: Name of the field
            raw_text: Raw OCR text
            context_lines: Number of context lines to include
            
        Returns:
            Context string for display
        """
        lines = raw_text.split('\n')
        
        # Field-specific context keywords
        keywords = {
            'total_amount': ['total', 'amount', 'sum', 'pay'],
            'date': ['date', 'dated'],
            'vendor': [],  # Use first few lines
            'currency': ['kes', 'usd', 'eur', 'ksh', '$', '€'],
        }
        
        field_keywords = keywords.get(field_name, [])
        
        if not field_keywords:
            # Return first few lines for vendor
            if field_name == 'vendor':
                return '\n'.join(lines[:5])
            return '\n'.join(lines[:context_lines])
        
        # Find lines containing keywords
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(kw in line_lower for kw in field_keywords):
                start = max(0, i - 1)
                end = min(len(lines), i + context_lines)
                return '\n'.join(lines[start:end])
        
        return '\n'.join(lines[:context_lines])
    
    def process_confirmation(
        self,
        document_id: str,
        response: ConfirmationResponse,
        extracted_fields: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Process user confirmation response and update fields.
        
        Args:
            document_id: Document identifier
            response: User's confirmation response
            extracted_fields: Current extracted fields
            
        Returns:
            Updated extracted fields with corrections applied
        """
        logger.info(f"ConfirmationManager: Processing confirmation for {document_id}")
        
        updated_fields = extracted_fields.copy()
        
        for correction in response.corrections:
            field_name = correction.field_name
            old_value = correction.original_value
            new_value = correction.corrected_value
            
            logger.info(f"ConfirmationManager: Correcting {field_name}: "
                       f"{old_value} -> {new_value}")
            
            updated_fields[field_name] = new_value
        
        # Remove from pending
        if document_id in self.pending_confirmations:
            del self.pending_confirmations[document_id]
        
        return updated_fields
    
    def get_pending_confirmation(
        self,
        document_id: str
    ) -> Optional[ConfirmationRequest]:
        """Get pending confirmation request for a document."""
        return self.pending_confirmations.get(document_id)


def request_user_confirmation(
    document_id: str,
    document_type: str,
    extracted_fields: dict[str, Any],
    consensus_results: dict[str, Any],
    overall_confidence: float,
    raw_text: str
) -> ConfirmationRequest:
    """
    Convenience function to evaluate if confirmation is needed.
    
    Args:
        document_id: Unique document identifier
        document_type: Type of document
        extracted_fields: Extracted field values
        consensus_results: Consensus extraction results
        overall_confidence: Overall confidence score
        raw_text: Raw OCR text
        
    Returns:
        ConfirmationRequest with confirmation details
    """
    manager = ConfirmationManager()
    return manager.evaluate_extraction(
        document_id=document_id,
        document_type=document_type,
        extracted_fields=extracted_fields,
        consensus_results=consensus_results,
        overall_confidence=overall_confidence,
        raw_text=raw_text
    )
