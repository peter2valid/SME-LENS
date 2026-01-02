"""Enterprise Confidence Scoring for SMELens

Confidence that NEVER LIES - earned, not guessed.

Factors:
- OCR clarity
- Consensus strength
- Layout consistency
- Business-rule validation
- User confirmation history
- Learning memory matches

Rules:
- Missing irrelevant fields → NO penalty
- Conflicting values → HEAVY penalty
- Confirmed fields → boost
- Never fake percentages

Every confidence score is explainable.
"""
import logging
from typing import Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ConfidenceLevel(Enum):
    """Human-readable confidence levels with strict definitions."""
    VERIFIED = "verified"      # 0.95+ User confirmed or perfect match
    HIGH = "high"              # 0.80-0.95 Strong consensus, good OCR
    MEDIUM = "medium"          # 0.60-0.80 Moderate consensus, usable
    LOW = "low"                # 0.40-0.60 Weak consensus, verify
    VERY_LOW = "very_low"      # 0.20-0.40 Many issues, manual review
    UNRELIABLE = "unreliable"  # <0.20 Should not trust
    
    @classmethod
    def from_score(cls, score: float) -> 'ConfidenceLevel':
        """Convert numeric score to level."""
        if score >= 0.95:
            return cls.VERIFIED
        elif score >= 0.80:
            return cls.HIGH
        elif score >= 0.60:
            return cls.MEDIUM
        elif score >= 0.40:
            return cls.LOW
        elif score >= 0.20:
            return cls.VERY_LOW
        else:
            return cls.UNRELIABLE


@dataclass
class ConfidenceFactor:
    """
    A single factor contributing to confidence.
    
    Each factor is transparent and explainable.
    """
    name: str
    category: str  # "ocr", "consensus", "layout", "business", "memory"
    score: float  # 0.0 - 1.0
    weight: float  # Importance (0.0 - 1.0)
    evidence: str  # Human-readable explanation
    is_penalty: bool = False  # True if this reduces confidence


@dataclass
class ConfidenceBreakdown:
    """
    Complete breakdown of confidence calculation.
    
    Shows exactly how confidence was computed.
    """
    overall_score: float
    level: ConfidenceLevel
    factors: list[ConfidenceFactor]
    
    # Summary
    primary_reason: str
    warnings: list[str]
    suggestions: list[str]
    
    # Detailed explanation
    explanation: str
    confidence_explanation: str  # For API output
    
    # Metadata
    calculation_method: str
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "confidence": round(self.overall_score, 3),
            "confidence_level": self.level.value,
            "confidence_explanation": self.confidence_explanation,
            "factors": [
                {
                    "name": f.name,
                    "category": f.category,
                    "score": round(f.score, 3),
                    "weight": round(f.weight, 3),
                    "evidence": f.evidence,
                    "is_penalty": f.is_penalty
                }
                for f in self.factors
            ],
            "warnings": self.warnings,
            "suggestions": self.suggestions
        }


class EnterpriseConfidenceScorer:
    """
    Enterprise-grade confidence scoring that never lies.
    
    Every score is:
    - Earned through evidence
    - Explainable
    - Honest about uncertainty
    """
    
    # Category weights (must sum to 1.0)
    WEIGHTS = {
        "ocr": 0.20,        # OCR quality
        "consensus": 0.30,  # Detector agreement
        "layout": 0.15,     # Layout consistency
        "business": 0.20,   # Business rule validation
        "memory": 0.15      # Learning memory match
    }
    
    # Penalty configurations
    CONFLICTING_VALUES_PENALTY = 0.25
    MISSING_CRITICAL_FIELD_PENALTY = 0.15
    LOW_OCR_QUALITY_PENALTY = 0.10
    UNUSUAL_VALUE_PENALTY = 0.10
    
    # Boost configurations
    USER_CONFIRMED_BOOST = 0.20
    KNOWN_PATTERN_BOOST = 0.10
    STRONG_CONSENSUS_BOOST = 0.10
    
    def __init__(self):
        """Initialize the scorer."""
        self.factors: list[ConfidenceFactor] = []
        self.warnings: list[str] = []
        self.suggestions: list[str] = []
        self.penalties_applied: list[str] = []
        self.boosts_applied: list[str] = []
    
    def compute_confidence(
        self,
        # OCR factors
        ocr_confidence: float,  # 0-100 from Tesseract
        low_confidence_words: list[str] = None,
        
        # Consensus factors
        consensus_results: dict[str, Any] = None,
        
        # Layout factors
        layout_consistent: bool = True,
        fields_in_expected_zones: bool = True,
        
        # Business rule factors
        extracted_fields: dict[str, Any] = None,
        document_type: str = "unknown",
        
        # Memory factors
        memory_match_score: float = 0.0,
        user_confirmed: bool = False,
        
        # Raw text for validation
        raw_text: str = ""
    ) -> ConfidenceBreakdown:
        """
        Compute comprehensive confidence score.
        
        Args:
            ocr_confidence: Average Tesseract confidence (0-100)
            low_confidence_words: Words flagged as uncertain
            consensus_results: Results from consensus extraction
            layout_consistent: Whether layout matches expectations
            fields_in_expected_zones: Whether fields are in expected zones
            extracted_fields: Dictionary of extracted field values
            document_type: Type of document
            memory_match_score: Score from learning memory (0-1)
            user_confirmed: Whether user has confirmed this pattern
            raw_text: Original OCR text
            
        Returns:
            ConfidenceBreakdown with complete scoring
        """
        self.factors = []
        self.warnings = []
        self.suggestions = []
        self.penalties_applied = []
        self.boosts_applied = []
        
        logger.info("EnterpriseConfidenceScorer: Computing confidence")
        
        # Initialize category scores
        category_scores = {
            "ocr": 0.0,
            "consensus": 0.0,
            "layout": 0.0,
            "business": 0.0,
            "memory": 0.0
        }
        
        # 1. Score OCR quality
        category_scores["ocr"] = self._score_ocr(
            ocr_confidence,
            low_confidence_words or []
        )
        
        # 2. Score consensus strength
        category_scores["consensus"] = self._score_consensus(
            consensus_results or {}
        )
        
        # 3. Score layout consistency
        category_scores["layout"] = self._score_layout(
            layout_consistent,
            fields_in_expected_zones
        )
        
        # 4. Score business rules
        category_scores["business"] = self._score_business_rules(
            extracted_fields or {},
            document_type,
            raw_text
        )
        
        # 5. Score memory/learning
        category_scores["memory"] = self._score_memory(
            memory_match_score,
            user_confirmed
        )
        
        # Calculate weighted average
        base_score = sum(
            category_scores[cat] * self.WEIGHTS[cat]
            for cat in category_scores
        )
        
        # Apply penalties
        total_penalty = sum(
            f.score for f in self.factors if f.is_penalty
        )
        
        # Calculate final score
        final_score = max(0.0, min(1.0, base_score - total_penalty))
        
        # Apply boosts (after penalties, capped at 1.0)
        for boost_name in self.boosts_applied:
            if "user_confirmed" in boost_name.lower():
                final_score = min(1.0, final_score + self.USER_CONFIRMED_BOOST)
            elif "known_pattern" in boost_name.lower():
                final_score = min(1.0, final_score + self.KNOWN_PATTERN_BOOST)
        
        level = ConfidenceLevel.from_score(final_score)
        
        # Generate explanations
        primary_reason = self._get_primary_reason(final_score, category_scores)
        explanation = self._build_explanation(final_score, category_scores)
        confidence_explanation = self._build_api_explanation(final_score, category_scores)
        
        # Add suggestions based on issues
        self._add_suggestions(category_scores)
        
        logger.info(f"EnterpriseConfidenceScorer: Final score {final_score:.3f} ({level.value})")
        
        return ConfidenceBreakdown(
            overall_score=final_score,
            level=level,
            factors=self.factors,
            primary_reason=primary_reason,
            warnings=self.warnings,
            suggestions=self.suggestions,
            explanation=explanation,
            confidence_explanation=confidence_explanation,
            calculation_method="weighted_consensus_v2"
        )
    
    def _score_ocr(
        self,
        ocr_confidence: float,
        low_confidence_words: list[str]
    ) -> float:
        """Score based on OCR quality."""
        # Normalize to 0-1
        normalized = ocr_confidence / 100.0
        
        # Penalty for many low-confidence words
        if len(low_confidence_words) > 10:
            word_penalty = 0.15
            self.penalties_applied.append("many_low_conf_words")
        elif len(low_confidence_words) > 5:
            word_penalty = 0.08
        else:
            word_penalty = 0.0
        
        score = max(0.0, normalized - word_penalty)
        
        # Add factor
        if score >= 0.85:
            evidence = f"High OCR quality ({ocr_confidence:.0f}%)"
        elif score >= 0.60:
            evidence = f"Acceptable OCR quality ({ocr_confidence:.0f}%)"
        else:
            evidence = f"Low OCR quality ({ocr_confidence:.0f}%) - may affect accuracy"
            self.warnings.append("OCR quality is low")
        
        self.factors.append(ConfidenceFactor(
            name="ocr_quality",
            category="ocr",
            score=score,
            weight=self.WEIGHTS["ocr"],
            evidence=evidence
        ))
        
        if low_confidence_words:
            self.factors.append(ConfidenceFactor(
                name="low_conf_words",
                category="ocr",
                score=word_penalty,
                weight=0.0,
                evidence=f"{len(low_confidence_words)} words with low OCR confidence",
                is_penalty=True
            ))
        
        return score
    
    def _score_consensus(
        self,
        consensus_results: dict[str, Any]
    ) -> float:
        """Score based on consensus extraction strength."""
        if not consensus_results:
            self.factors.append(ConfidenceFactor(
                name="consensus_unavailable",
                category="consensus",
                score=0.5,
                weight=self.WEIGHTS["consensus"],
                evidence="Consensus extraction not performed"
            ))
            return 0.5
        
        total_score = 0.0
        field_count = 0
        conflicts_found = 0
        
        for field_name, result in consensus_results.items():
            if hasattr(result, 'consensus_level'):
                level = str(result.consensus_level)
                
                if 'STRONG' in level:
                    field_score = 1.0
                    self.boosts_applied.append(f"strong_consensus_{field_name}")
                elif 'MODERATE' in level:
                    field_score = 0.7
                elif 'WEAK' in level:
                    field_score = 0.4
                    conflicts_found += 1
                else:
                    field_score = 0.2
                    conflicts_found += 1
                
                total_score += field_score
                field_count += 1
                
            elif isinstance(result, dict):
                agreement = result.get('agreement_count', 0)
                total = result.get('total_detectors', 4)
                
                if total > 0:
                    field_score = agreement / total
                else:
                    field_score = 0.5
                
                if result.get('needs_confirmation', False):
                    conflicts_found += 1
                
                total_score += field_score
                field_count += 1
        
        avg_score = total_score / field_count if field_count > 0 else 0.5
        
        # Add penalty for conflicts
        if conflicts_found > 0:
            conflict_penalty = min(conflicts_found * self.CONFLICTING_VALUES_PENALTY, 0.5)
            self.factors.append(ConfidenceFactor(
                name="conflicting_values",
                category="consensus",
                score=conflict_penalty,
                weight=0.0,
                evidence=f"{conflicts_found} field(s) have conflicting values",
                is_penalty=True
            ))
            self.warnings.append(f"{conflicts_found} field(s) have conflicting values")
        
        # Main consensus factor
        if avg_score >= 0.8:
            evidence = "Strong detector agreement across fields"
        elif avg_score >= 0.6:
            evidence = "Moderate detector agreement"
        else:
            evidence = "Weak detector agreement - results may be unreliable"
        
        self.factors.append(ConfidenceFactor(
            name="consensus_strength",
            category="consensus",
            score=avg_score,
            weight=self.WEIGHTS["consensus"],
            evidence=evidence
        ))
        
        return avg_score
    
    def _score_layout(
        self,
        layout_consistent: bool,
        fields_in_expected_zones: bool
    ) -> float:
        """Score based on layout consistency."""
        score = 0.5  # Base score
        
        if layout_consistent:
            score += 0.25
            evidence_parts = ["Layout is consistent"]
        else:
            evidence_parts = ["Layout inconsistencies detected"]
            self.warnings.append("Document layout is unusual")
        
        if fields_in_expected_zones:
            score += 0.25
            evidence_parts.append("fields in expected zones")
        else:
            evidence_parts.append("some fields in unexpected zones")
        
        self.factors.append(ConfidenceFactor(
            name="layout_consistency",
            category="layout",
            score=score,
            weight=self.WEIGHTS["layout"],
            evidence=", ".join(evidence_parts)
        ))
        
        return score
    
    def _score_business_rules(
        self,
        extracted_fields: dict[str, Any],
        document_type: str,
        raw_text: str
    ) -> float:
        """Score based on business rule validation."""
        score = 0.7  # Start with passing score
        issues = []
        
        # Rule 1: Total amount should be positive and reasonable
        total = extracted_fields.get('total_amount')
        if total is not None:
            if total <= 0:
                score -= 0.2
                issues.append("Total is zero or negative")
            elif total > 100000000:  # 100 million
                score -= 0.1
                issues.append("Total seems unusually large")
        
        # Rule 2: Date should be reasonable (not too old or future)
        date = extracted_fields.get('date')
        if date:
            try:
                year = int(date.split('-')[0]) if '-' in str(date) else None
                if year:
                    if year < 2010:
                        score -= 0.15
                        issues.append(f"Date year {year} is very old")
                    elif year > 2030:
                        score -= 0.2
                        issues.append(f"Date year {year} is in the future")
            except (ValueError, AttributeError):
                pass
        
        # Rule 3: Vendor should not look like noise
        vendor = extracted_fields.get('vendor')
        if vendor:
            if len(vendor) < 3:
                score -= 0.1
                issues.append("Vendor name too short")
            elif len(vendor) > 100:
                score -= 0.1
                issues.append("Vendor name too long")
        
        # Rule 4: Check for required fields based on document type
        if document_type in ['receipt', 'invoice']:
            required = ['total_amount', 'vendor']
            missing = [f for f in required if not extracted_fields.get(f)]
            if missing:
                score -= len(missing) * 0.1
                issues.append(f"Missing required fields: {', '.join(missing)}")
        
        score = max(0.0, min(1.0, score))
        
        if issues:
            evidence = f"Business rules: {'; '.join(issues)}"
            self.warnings.extend(issues)
        else:
            evidence = "All business rules passed"
        
        self.factors.append(ConfidenceFactor(
            name="business_rules",
            category="business",
            score=score,
            weight=self.WEIGHTS["business"],
            evidence=evidence
        ))
        
        return score
    
    def _score_memory(
        self,
        memory_match_score: float,
        user_confirmed: bool
    ) -> float:
        """Score based on learning memory match."""
        score = 0.5  # Base when no memory match
        
        if user_confirmed:
            score = 1.0
            evidence = "Previously confirmed by user"
            self.boosts_applied.append("user_confirmed")
        elif memory_match_score >= 0.9:
            score = 0.9
            evidence = "Matches known pattern with high confidence"
            self.boosts_applied.append("known_pattern_strong")
        elif memory_match_score >= 0.6:
            score = 0.7
            evidence = f"Matches known pattern ({memory_match_score:.0%})"
            self.boosts_applied.append("known_pattern")
        elif memory_match_score > 0:
            score = 0.5 + memory_match_score * 0.2
            evidence = f"Partial match to known pattern ({memory_match_score:.0%})"
        else:
            evidence = "No matching pattern in learning memory"
        
        self.factors.append(ConfidenceFactor(
            name="learning_memory",
            category="memory",
            score=score,
            weight=self.WEIGHTS["memory"],
            evidence=evidence
        ))
        
        return score
    
    def _get_primary_reason(
        self,
        score: float,
        category_scores: dict[str, float]
    ) -> str:
        """Generate the primary reason for the confidence level."""
        if score >= 0.95:
            return "Verified extraction with high confidence"
        
        # Find weakest category
        weakest = min(category_scores.items(), key=lambda x: x[1])
        
        if score >= 0.80:
            return f"High confidence extraction"
        elif score >= 0.60:
            if weakest[1] < 0.5:
                return f"Moderate confidence - {weakest[0]} quality affects score"
            return "Moderate confidence - some verification recommended"
        elif score >= 0.40:
            return f"Low confidence - {weakest[0]} issues detected"
        else:
            return "Very low confidence - manual review required"
    
    def _build_explanation(
        self,
        score: float,
        category_scores: dict[str, float]
    ) -> str:
        """Build detailed explanation of confidence calculation."""
        parts = [f"Overall confidence: {score:.1%}"]
        parts.append("")
        parts.append("Category breakdown:")
        
        for cat, cat_score in category_scores.items():
            parts.append(f"  - {cat}: {cat_score:.1%} (weight: {self.WEIGHTS[cat]:.0%})")
        
        if self.penalties_applied:
            parts.append("")
            parts.append(f"Penalties applied: {', '.join(self.penalties_applied)}")
        
        if self.boosts_applied:
            parts.append(f"Boosts applied: {', '.join(self.boosts_applied)}")
        
        return '\n'.join(parts)
    
    def _build_api_explanation(
        self,
        score: float,
        category_scores: dict[str, float]
    ) -> str:
        """Build user-friendly explanation for API response."""
        level = ConfidenceLevel.from_score(score)
        
        # Start with summary
        if level == ConfidenceLevel.VERIFIED:
            summary = "Strong consensus across layout and keyword detectors."
        elif level == ConfidenceLevel.HIGH:
            summary = "High agreement between multiple extraction methods."
        elif level == ConfidenceLevel.MEDIUM:
            summary = "Moderate extraction confidence."
        elif level == ConfidenceLevel.LOW:
            summary = "Some uncertainty in extracted values."
        else:
            summary = "Low confidence - verification recommended."
        
        # Add specific insights
        insights = []
        
        if category_scores.get("consensus", 0) >= 0.8:
            insights.append("Strong detector consensus.")
        elif category_scores.get("consensus", 0) < 0.5:
            insights.append("Detector disagreement on some fields.")
        
        if category_scores.get("memory", 0) >= 0.7:
            insights.append("Previously confirmed document layout.")
        
        if category_scores.get("ocr", 0) < 0.6:
            insights.append("OCR quality may affect accuracy.")
        
        if insights:
            return f"{summary} {' '.join(insights)}"
        
        return summary
    
    def _add_suggestions(self, category_scores: dict[str, float]) -> None:
        """Add actionable suggestions based on scores."""
        if category_scores.get("ocr", 1.0) < 0.5:
            self.suggestions.append(
                "Consider re-scanning with better lighting or higher resolution"
            )
        
        if category_scores.get("consensus", 1.0) < 0.5:
            self.suggestions.append(
                "Review flagged fields - multiple possible values detected"
            )
        
        if category_scores.get("business", 1.0) < 0.6:
            self.suggestions.append(
                "Some values may not match expected business rules"
            )


def compute_confidence(
    ocr_confidence: float = 80.0,
    consensus_results: dict = None,
    extracted_fields: dict = None,
    document_type: str = "unknown",
    memory_match_score: float = 0.0,
    user_confirmed: bool = False,
    raw_text: str = "",
    low_confidence_words: list = None
) -> ConfidenceBreakdown:
    """
    Convenience function to compute confidence.
    
    Args:
        ocr_confidence: OCR confidence (0-100)
        consensus_results: Consensus extraction results
        extracted_fields: Extracted field values
        document_type: Type of document
        memory_match_score: Learning memory match score
        user_confirmed: Whether user confirmed pattern
        raw_text: Original OCR text
        low_confidence_words: Low confidence words from OCR
        
    Returns:
        ConfidenceBreakdown with complete scoring
    """
    scorer = EnterpriseConfidenceScorer()
    return scorer.compute_confidence(
        ocr_confidence=ocr_confidence,
        low_confidence_words=low_confidence_words or [],
        consensus_results=consensus_results or {},
        extracted_fields=extracted_fields or {},
        document_type=document_type,
        memory_match_score=memory_match_score,
        user_confirmed=user_confirmed,
        raw_text=raw_text
    )
