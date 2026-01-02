"""Document Intelligence Engine for SMELens

The main orchestrator that combines all OCR components into
an intelligent document processing pipeline.

Pipeline:
1. Preprocess image (enhance for OCR)
2. Run multi-pass OCR (extract text)
3. Clean and correct text
4. Extract structured fields
5. Score confidence
6. Return unified result

This is the "brain" layer that transforms raw OCR into
actionable SME business data.
"""
import logging
from typing import Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
from PIL import Image

from .preprocessing import (
    ImagePreprocessor, 
    DocumentType, 
    PreprocessingResult,
    preprocess_image
)
from .ocr_engine import (
    MultiPassOCREngine,
    MultiPassOCRResult,
    run_ocr
)
from .text_cleaner import (
    OCRTextCleaner,
    TextCorrector,
    CleaningResult,
    clean_text
)
from .field_extractor import (
    FieldExtractor,
    ExtractionResult,
    extract_fields
)
from .confidence_scorer import (
    ConfidenceScorer,
    ConfidenceResult,
    score_confidence
)

logger = logging.getLogger(__name__)


@dataclass
class DocumentIntelligenceResult:
    """
    Complete result from the Document Intelligence Engine.
    
    Contains all extracted data, confidence scoring, and
    processing metadata for transparency and debugging.
    """
    # Core extracted data
    raw_text: str
    cleaned_text: str
    extracted_data: dict[str, Any]
    
    # Confidence information
    confidence: float
    confidence_level: str
    confidence_reason: str
    
    # User explanation (Task 6)
    explanation: str
    
    # Processing notes
    notes: list[str]
    warnings: list[str]
    suggestions: list[str]
    
    # Detailed extraction info (for advanced use)
    all_amounts: list[dict]
    all_dates: list[dict]
    
    # Processing metadata
    document_type: str
    currency: str
    processing_steps: list[str]
    ocr_config_used: str
    
    # Error information (if any)
    success: bool
    error: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "document_type": self.document_type,
            "raw_text": self.raw_text,
            "cleaned_text": self.cleaned_text,
            "extracted_data": self.extracted_data,
            "confidence": round(self.confidence, 2),
            "explanation": self.explanation,
            # Extra fields for debugging/frontend
            "confidence_level": self.confidence_level,
            "confidence_reason": self.confidence_reason,
            "notes": self.notes,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "currency": self.currency,
            "success": self.success,
            "error": self.error
        }
    
    def to_simple_dict(self) -> dict[str, Any]:
        """Return simplified output for API response."""
        return self.to_dict()


class DocumentIntelligenceEngine:
    """
    Main orchestrator for intelligent document processing.
    
    Combines preprocessing, OCR, text cleaning, field extraction,
    and confidence scoring into a unified pipeline.
    """
    
    def __init__(self, lang: str = "eng"):
        """
        Initialize the Document Intelligence Engine.
        
        Args:
            lang: Tesseract language code (default: English)
        """
        self.lang = lang
        self.processing_steps: list[str] = []
        
        logger.info("DocumentIntelligenceEngine: Initialized")
    
    def process_image(
        self, 
        image_path: str,
        document_hint: str = "unknown"
    ) -> DocumentIntelligenceResult:
        """
        Process an image through the complete intelligence pipeline.
        
        Args:
            image_path: Path to the image file
            document_hint: Hint about document type (receipt, invoice, etc.)
            
        Returns:
            DocumentIntelligenceResult with all extracted data
        """
        self.processing_steps = []
        
        logger.info(f"DIE: Starting processing for {image_path}")
        
        try:
            # Step 1: Load and preprocess image
            self.processing_steps.append("preprocess")
            preprocess_result = self._preprocess(image_path, document_hint)
            
            # Step 2: Run multi-pass OCR
            self.processing_steps.append("ocr")
            ocr_result = self._run_ocr(preprocess_result.image, document_hint)
            
            if not ocr_result.primary_text.strip():
                logger.warning("DIE: No text extracted from image")
                return self._empty_result("No text could be extracted from image")
            
            # Step 3: Clean and correct text
            self.processing_steps.append("clean")
            cleaning_result = self._clean_text(ocr_result.primary_text)
            
            # Step 4: Extract structured fields
            self.processing_steps.append("extract")
            extraction_result = self._extract_fields(cleaning_result.cleaned_text)
            
            # Step 5: Score confidence
            self.processing_steps.append("score")
            confidence_result = self._score_confidence(
                ocr_result=ocr_result,
                preprocessing_quality=preprocess_result.estimated_quality,
                extraction_result=extraction_result,
                raw_text=ocr_result.primary_text
            )
            
            # Build final result
            return self._build_result(
                raw_text=ocr_result.primary_text,
                cleaned_text=cleaning_result.cleaned_text,
                extraction_result=extraction_result,
                confidence_result=confidence_result,
                ocr_result=ocr_result,
                cleaning_result=cleaning_result
            )
            
        except FileNotFoundError:
            logger.error(f"DIE: File not found - {image_path}")
            return self._error_result(f"File not found: {image_path}")
            
        except Exception as e:
            logger.error(f"DIE: Processing failed - {type(e).__name__}: {e}")
            return self._error_result(f"Processing failed: {str(e)}")
    
    def _preprocess(
        self, 
        image_path: str, 
        document_hint: str
    ) -> PreprocessingResult:
        """Preprocess the image for optimal OCR."""
        # Map hint to document type
        doc_type_map = {
            "receipt": DocumentType.RECEIPT,
            "invoice": DocumentType.INVOICE,
            "handwritten": DocumentType.HANDWRITTEN,
            "form": DocumentType.FORM,
        }
        doc_type = doc_type_map.get(document_hint, DocumentType.UNKNOWN)
        
        # Load image
        image = Image.open(image_path)
        
        # Run preprocessing
        preprocessor = ImagePreprocessor(document_type=doc_type)
        result = preprocessor.preprocess(image)
        
        logger.info(f"DIE: Preprocessing complete - quality={result.estimated_quality:.2f}, "
                   f"transforms={result.applied_transforms}")
        
        return result
    
    def _run_ocr(
        self, 
        image: Image.Image, 
        document_hint: str
    ) -> MultiPassOCRResult:
        """Run multi-pass OCR on the preprocessed image."""
        engine = MultiPassOCREngine(lang=self.lang)
        result = engine.run_multi_pass(image, document_hint=document_hint)
        
        logger.info(f"DIE: OCR complete - {len(result.primary_text)} chars, "
                   f"confidence={result.best_confidence:.1f}%, "
                   f"passes={len(result.all_passes)}")
        
        return result
    
    def _clean_text(self, text: str) -> CleaningResult:
        """Clean and correct OCR text."""
        cleaner = OCRTextCleaner()
        result = cleaner.clean(text)
        
        logger.info(f"DIE: Text cleaning complete - {result.correction_count} corrections")
        
        return result
    
    def _extract_fields(self, text: str) -> ExtractionResult:
        """Extract structured fields from cleaned text."""
        extractor = FieldExtractor()
        result = extractor.extract_all(text)
        
        logger.info(f"DIE: Field extraction complete - "
                   f"type={result.document_type}")
        
        return result
    
    def _score_confidence(
        self,
        ocr_result: MultiPassOCRResult,
        preprocessing_quality: float,
        extraction_result: ExtractionResult,
        raw_text: str
    ) -> ConfidenceResult:
        """Calculate confidence score."""
        # Build fields dict for scorer
        fields_dict = extraction_result.to_dict()
        
        scorer = ConfidenceScorer()
        result = scorer.score(
            ocr_confidence=ocr_result.best_confidence,
            preprocessing_quality=preprocessing_quality,
            extracted_fields=fields_dict,
            raw_text=raw_text,
            low_confidence_words=ocr_result.low_confidence_words
        )
        
        logger.info(f"DIE: Confidence scoring complete - {result.overall_score:.2f} ({result.level.value})")
        
        return result
    
    def _build_result(
        self,
        raw_text: str,
        cleaned_text: str,
        extraction_result: ExtractionResult,
        confidence_result: ConfidenceResult,
        ocr_result: MultiPassOCRResult,
        cleaning_result: CleaningResult
    ) -> DocumentIntelligenceResult:
        """Build the final result object."""
        # Compile notes from all stages
        notes = []
        notes.extend(extraction_result.extraction_notes)
        
        if cleaning_result.correction_count > 0:
            notes.append(f"Applied {cleaning_result.correction_count} text corrections")
        
        # Generate explanation (Task 6)
        explanation = self._generate_explanation(
            extraction_result.document_type,
            confidence_result.overall_score,
            confidence_result.warnings
        )
        
        return DocumentIntelligenceResult(
            raw_text=raw_text,
            cleaned_text=cleaned_text,
            extracted_data=extraction_result.to_dict(),
            confidence=confidence_result.overall_score,
            confidence_level=confidence_result.level.value,
            confidence_reason=confidence_result.primary_reason,
            explanation=explanation,
            notes=notes,
            warnings=confidence_result.warnings,
            suggestions=confidence_result.suggestions,
            all_amounts=[
                {"value": a.value, "currency": a.currency, "confidence": a.confidence}
                for a in extraction_result.all_amounts
            ],
            all_dates=[
                {"value": d.value, "original": d.original}
                for d in extraction_result.all_dates
            ],
            document_type=extraction_result.document_type,
            currency=extraction_result.currency,
            processing_steps=self.processing_steps.copy(),
            ocr_config_used=ocr_result.config_summary,
            success=True
        )
    
    def _generate_explanation(self, doc_type: str, confidence: float, warnings: list[str]) -> str:
        """Generate a human-friendly explanation."""
        if doc_type == "unknown":
            return "Could not determine the document type. Please ensure the image is clear."
            
        base = f"This appears to be a {doc_type}."
        
        if confidence > 0.85:
            return f"{base} The data was extracted with high confidence."
        elif confidence > 0.6:
            if warnings:
                return f"{base} Some fields may require review: {warnings[0].lower()}."
            return f"{base} Please review the extracted fields."
        else:
            return f"{base} The image quality or handwriting made extraction difficult. Please verify all fields."

    def _empty_result(self, message: str) -> DocumentIntelligenceResult:
        """Return an empty result when no text is extracted."""
        return DocumentIntelligenceResult(
            raw_text="",
            cleaned_text="",
            extracted_data={},
            confidence=0.0,
            confidence_level="very_low",
            confidence_reason=message,
            explanation="No text could be found in the image.",
            notes=[message],
            warnings=["No text could be extracted"],
            suggestions=["Try re-scanning with better lighting or higher resolution"],
            all_amounts=[],
            all_dates=[],
            document_type="unknown",
            currency="UNKNOWN",
            processing_steps=self.processing_steps.copy(),
            ocr_config_used="",
            success=False,
            error=message
        )
    
    def _error_result(self, error_message: str) -> DocumentIntelligenceResult:
        """Return an error result when processing fails."""
        return DocumentIntelligenceResult(
            raw_text="",
            cleaned_text="",
            extracted_data={},
            confidence=0.0,
            confidence_level="very_low",
            confidence_reason=f"Processing error: {error_message}",
            explanation="An error occurred while processing the document.",
            notes=[],
            warnings=[error_message],
            suggestions=["Check the image file and try again"],
            all_amounts=[],
            all_dates=[],
            document_type="unknown",
            currency="UNKNOWN",
            processing_steps=self.processing_steps.copy(),
            ocr_config_used="",
            success=False,
            error=error_message
        )


def process_document(
    image_path: str, 
    document_hint: str = "unknown",
    lang: str = "eng"
) -> DocumentIntelligenceResult:
    """
    Convenience function to process a document image.
    
    This is the main entry point for the Document Intelligence Engine.
    
    Args:
        image_path: Path to the image file
        document_hint: Hint about document type (receipt, invoice, handwritten, form)
        lang: Tesseract language code
        
    Returns:
        DocumentIntelligenceResult with all extracted data and confidence scoring
    """
    engine = DocumentIntelligenceEngine(lang=lang)
    return engine.process_image(image_path, document_hint=document_hint)
