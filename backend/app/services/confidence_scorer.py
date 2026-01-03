"""Confidence Scoring System for SMELens OCR

Generates real, explainable confidence scores based on:
- OCR quality metrics
- Pattern match strength  
- Field consistency
- Cross-field validation

Returns scores with reasoning, not arbitrary percentages.
"""
import logging
from typing import Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ConfidenceLevel(Enum):
    """Human-readable confidence levels."""
    VERY_HIGH = "very_high"    # 0.9 - 1.0
    HIGH = "high"              # 0.75 - 0.9
    MEDIUM = "medium"          # 0.5 - 0.75
    LOW = "low"                # 0.25 - 0.5
    VERY_LOW = "very_low"      # 0.0 - 0.25
    
    @classmethod
    def from_score(cls, score: float) -> "ConfidenceLevel":
        """Convert numeric score to level."""
        if score >= 0.9:
            return cls.VERY_HIGH
        elif score >= 0.75:
            return cls.HIGH
        elif score >= 0.5:
            return cls.MEDIUM
        elif score >= 0.25:
            return cls.LOW
        else:
            return cls.VERY_LOW


@dataclass
class ConfidenceFactor:
    """A single factor contributing to overall confidence."""
    name: str
    score: float  # 0.0 - 1.0
    weight: float  # How much this factor matters
    reason: str
    

@dataclass
class ConfidenceResult:
    """Complete confidence assessment."""
    overall_score: float  # 0.0 - 1.0
    level: ConfidenceLevel
    factors: list[ConfidenceFactor]
    primary_reason: str
    warnings: list[str]
    suggestions: list[str]
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "confidence": round(self.overall_score, 2),
            "level": self.level.value,
            "reason": self.primary_reason,
            "factors": [
                {
                    "name": f.name,
                    "score": round(f.score, 2),
                    "weight": f.weight,
                    "reason": f.reason
                }
                for f in self.factors
            ],
            "warnings": self.warnings,
            "suggestions": self.suggestions
        }


class ConfidenceScorer:
    """
    Calculates confidence scores for OCR extraction results.
    
    Uses multiple weighted factors to produce an explainable
    confidence score that reflects actual reliability.
    """
    
    # Factor weights (must sum to ~1.0)
    WEIGHT_OCR_QUALITY = 0.25
    WEIGHT_FIELD_EXTRACTION = 0.30
    WEIGHT_PATTERN_MATCH = 0.20
    WEIGHT_CONSISTENCY = 0.15
    WEIGHT_COMPLETENESS = 0.10
    
    def __init__(self):
        """Initialize the scorer."""
        self.factors: list[ConfidenceFactor] = []
        self.warnings: list[str] = []
        self.suggestions: list[str] = []
    
    def score(
        self,
        ocr_confidence: float,
        preprocessing_quality: float,
        extracted_fields: dict[str, Any],
        raw_text: str,
        low_confidence_words: list[str]
    ) -> ConfidenceResult:
        """
        Calculate overall confidence score.
        
        Args:
            ocr_confidence: Average word confidence from Tesseract (0-100)
            preprocessing_quality: Image quality score from preprocessing (0-1)
            extracted_fields: Dictionary of extracted field values
            raw_text: Original OCR text
            low_confidence_words: Words flagged as low confidence
            
        Returns:
            ConfidenceResult with score, factors, and reasoning
        """
        self.factors = []
        self.warnings = []
        self.suggestions = []
        
        logger.info("ConfidenceScorer: Calculating confidence")
        
        # Factor 1: OCR Quality
        ocr_score = self._score_ocr_quality(ocr_confidence, preprocessing_quality)
        
        # Factor 2: Field Extraction Success
        extraction_score = self._score_field_extraction(extracted_fields)
        
        # Factor 3: Pattern Match Strength
        pattern_score = self._score_pattern_matches(extracted_fields, raw_text)
        
        # Factor 4: Field Consistency
        consistency_score = self._score_consistency(extracted_fields)
        
        # Factor 5: Completeness
        completeness_score = self._score_completeness(extracted_fields)
        
        # Factor 6: Low confidence word penalty
        if low_confidence_words:
            penalty = min(len(low_confidence_words) * 0.05, 0.2)
            self.warnings.append(
                f"{len(low_confidence_words)} words with low OCR confidence"
            )
        else:
            penalty = 0
        
        # Calculate weighted average
        overall = (
            ocr_score.score * self.WEIGHT_OCR_QUALITY +
            extraction_score.score * self.WEIGHT_FIELD_EXTRACTION +
            pattern_score.score * self.WEIGHT_PATTERN_MATCH +
            consistency_score.score * self.WEIGHT_CONSISTENCY +
            completeness_score.score * self.WEIGHT_COMPLETENESS -
            penalty
        )
        
        # Clamp to valid range
        overall = max(0.0, min(1.0, overall))
        
        # Determine primary reason
        primary_reason = self._get_primary_reason(overall)
        
        # Add suggestions based on scores
        self._add_suggestions(ocr_score.score, extraction_score.score)
        
        self.factors = [
            ocr_score, extraction_score, pattern_score, 
            consistency_score, completeness_score
        ]
        
        level = ConfidenceLevel.from_score(overall)
        
        logger.info(f"ConfidenceScorer: Final score {overall:.2f} ({level.value})")
        
        return ConfidenceResult(
            overall_score=overall,
            level=level,
            factors=self.factors,
            primary_reason=primary_reason,
            warnings=self.warnings,
            suggestions=self.suggestions
        )
    
    def _score_ocr_quality(
        self, 
        ocr_confidence: float, 
        image_quality: float
    ) -> ConfidenceFactor:
        """Score based on OCR and image quality."""
        # OCR confidence is 0-100, normalize to 0-1
        normalized_ocr = ocr_confidence / 100.0
        
        # Combined score (OCR matters more than preprocessing)
        score = (normalized_ocr * 0.7 + image_quality * 0.3)
        
        if score >= 0.85:
            reason = "Clear image with high OCR confidence"
        elif score >= 0.6:
            reason = "Acceptable image quality"
        elif score >= 0.4:
            reason = "Image quality affects accuracy"
            self.warnings.append("Low OCR quality may affect accuracy")
        else:
            reason = "Poor image quality significantly impacts accuracy"
            self.warnings.append("Very low OCR quality - results may be unreliable")
        
        return ConfidenceFactor(
            name="ocr_quality",
            score=score,
            weight=self.WEIGHT_OCR_QUALITY,
            reason=reason
        )
    
    def _score_field_extraction(
        self, 
        extracted_fields: dict[str, Any]
    ) -> ConfidenceFactor:
        """Score based on successful field extraction."""
        # Key fields we expect to extract
        key_fields = ['vendor', 'total_amount', 'date', 'currency']
        
        extracted_count = 0
        for field_name in key_fields:
            value = extracted_fields.get(field_name)
            if value is not None and value != "UNKNOWN":
                extracted_count += 1
        
        score = extracted_count / len(key_fields)
        
        if score >= 0.75:
            reason = f"Successfully extracted {extracted_count}/{len(key_fields)} key fields"
        elif score >= 0.5:
            reason = f"Extracted {extracted_count}/{len(key_fields)} key fields"
            self.warnings.append(f"Could not extract all key fields")
        else:
            reason = f"Only extracted {extracted_count}/{len(key_fields)} key fields"
            self.warnings.append("Many fields could not be extracted")
        
        return ConfidenceFactor(
            name="field_extraction",
            score=score,
            weight=self.WEIGHT_FIELD_EXTRACTION,
            reason=reason
        )
    
    def _score_pattern_matches(
        self, 
        extracted_fields: dict[str, Any],
        raw_text: str
    ) -> ConfidenceFactor:
        """Score based on pattern match quality."""
        score = 0.5  # Base score
        reasons = []
        
        # Check if total was found near a keyword
        total_info = extracted_fields.get('total_source', '')
        if 'keyword' in str(total_info).lower():
            score += 0.3
            reasons.append("Total found near keyword")
        elif extracted_fields.get('total_amount') is not None:
            score += 0.15
            reasons.append("Total identified by heuristic")
        
        # Check if vendor looks valid
        vendor = extracted_fields.get('vendor')
        if vendor and len(vendor) > 3:
            score += 0.1
            reasons.append("Vendor name identified")
        
        # Check if date format was recognized
        if extracted_fields.get('date'):
            score += 0.1
            reasons.append("Date format recognized")
        
        score = min(1.0, score)
        
        return ConfidenceFactor(
            name="pattern_match",
            score=score,
            weight=self.WEIGHT_PATTERN_MATCH,
            reason="; ".join(reasons) if reasons else "Pattern matching applied"
        )
    
    def _score_consistency(
        self, 
        extracted_fields: dict[str, Any]
    ) -> ConfidenceFactor:
        """Score based on cross-field consistency."""
        score = 0.8  # Start with high score, deduct for issues
        issues = []
        
        # Check: Total should be reasonable
        total = extracted_fields.get('total_amount')
        if total is not None:
            if total <= 0:
                score -= 0.3
                issues.append("Total is zero or negative")
            elif total > 10000000:  # 10 million
                score -= 0.2
                issues.append("Total seems unusually large")
        
        # Check: Date should be reasonable
        date = extracted_fields.get('date')
        if date:
            try:
                # Simple year check
                year = int(date.split('-')[0]) if '-' in date else None
                if year and (year < 2000 or year > 2030):
                    score -= 0.2
                    issues.append(f"Date year {year} seems unusual")
            except (ValueError, IndexError):
                pass
        
        # Check: Multiple amounts, was largest used?
        all_amounts = extracted_fields.get('all_amounts', [])
        if len(all_amounts) > 1 and total:
            max_amount = max(a.get('value', 0) for a in all_amounts)
            if total != max_amount:
                # Total is not the largest - might be correct or might be wrong
                score -= 0.1
                issues.append("Total is not the largest amount")
        
        score = max(0.0, score)
        
        return ConfidenceFactor(
            name="consistency",
            score=score,
            weight=self.WEIGHT_CONSISTENCY,
            reason="Field values are consistent" if not issues else "; ".join(issues)
        )
    
    def _score_completeness(
        self, 
        extracted_fields: dict[str, Any]
    ) -> ConfidenceFactor:
        """Score based on how complete the extraction is."""
        # Fields in priority order
        fields_priority = [
            ('total_amount', 0.4),
            ('vendor', 0.25),
            ('date', 0.2),
            ('currency', 0.1),
            ('document_type', 0.05)
        ]
        
        score = 0.0
        for field_name, weight in fields_priority:
            value = extracted_fields.get(field_name)
            if value is not None and value != 'unknown' and value != 'UNKNOWN':
                score += weight
        
        if score >= 0.9:
            reason = "All key fields extracted"
        elif score >= 0.6:
            reason = "Most key fields extracted"
        else:
            reason = "Missing important fields"
        
        return ConfidenceFactor(
            name="completeness",
            score=score,
            weight=self.WEIGHT_COMPLETENESS,
            reason=reason
        )
    
    def _get_primary_reason(self, score: float) -> str:
        """Generate the primary reason string based on score."""
        if score >= 0.9:
            return "High quality scan with clear text and all fields extracted"
        elif score >= 0.75:
            return "Good quality document with most fields identified"
        elif score >= 0.5:
            return "Moderate confidence - some fields may need verification"
        elif score >= 0.25:
            return "Low confidence - manual review recommended"
        else:
            return "Very low confidence - document may need re-scanning"
    
    def _add_suggestions(
        self, 
        ocr_score: float, 
        extraction_score: float
    ) -> None:
        """Add actionable suggestions based on scores."""
        if ocr_score < 0.5:
            self.suggestions.append(
                "Consider re-scanning with better lighting or higher resolution"
            )
        
        if extraction_score < 0.5:
            self.suggestions.append(
                "Manual entry may be needed for missing fields"
            )


def score_confidence(
    ocr_confidence: float,
    preprocessing_quality: float,
    extracted_fields: dict[str, Any],
    raw_text: str,
    low_confidence_words: Optional[list[str]] = None
) -> ConfidenceResult:
    """
    Convenience function to calculate confidence score.
    
    Args:
        ocr_confidence: Average OCR confidence (0-100)
        preprocessing_quality: Image quality score (0-1)
        extracted_fields: Dictionary of extracted fields
        raw_text: Original OCR text
        low_confidence_words: List of low-confidence words
        
    Returns:
        ConfidenceResult with score and reasoning
    """
    scorer = ConfidenceScorer()
    return scorer.score(
        ocr_confidence=ocr_confidence,
        preprocessing_quality=preprocessing_quality,
        extracted_fields=extracted_fields,
        raw_text=raw_text,
        low_confidence_words=low_confidence_words or []
    )
