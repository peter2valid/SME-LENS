"""SMELens OCR Services Package

This package contains the Document Intelligence Engine components:

- preprocessing: Image enhancement for optimal OCR
- ocr_engine: Multi-pass Tesseract OCR with adaptive configurations
- text_cleaner: OCR error correction and text normalization
- field_extractor: Deterministic structured data extraction
- confidence_scorer: Explainable confidence scoring
- document_intelligence: Main orchestrator combining all components

Usage:
    from app.services.document_intelligence import process_document
    
    result = process_document("receipt.jpg", document_hint="receipt")
    print(result.extracted_data)
    print(result.confidence)
"""

from .document_intelligence import (
    process_document,
    DocumentIntelligenceEngine,
    DocumentIntelligenceResult
)

from .preprocessing import (
    preprocess_image,
    ImagePreprocessor,
    DocumentType,
    PreprocessingResult
)

from .ocr_engine import (
    run_ocr,
    MultiPassOCREngine,
    MultiPassOCRResult
)

from .text_cleaner import (
    clean_text,
    OCRTextCleaner,
    CleaningResult
)

from .field_extractor import (
    extract_fields,
    FieldExtractor,
    ExtractionResult
)

from .confidence_scorer import (
    score_confidence,
    ConfidenceScorer,
    ConfidenceResult
)

__all__ = [
    # Main entry point
    "process_document",
    "DocumentIntelligenceEngine",
    "DocumentIntelligenceResult",
    
    # Preprocessing
    "preprocess_image",
    "ImagePreprocessor",
    "DocumentType",
    "PreprocessingResult",
    
    # OCR Engine
    "run_ocr",
    "MultiPassOCREngine", 
    "MultiPassOCRResult",
    
    # Text Cleaning
    "clean_text",
    "OCRTextCleaner",
    "CleaningResult",
    
    # Field Extraction
    "extract_fields",
    "FieldExtractor",
    "ExtractionResult",
    
    # Confidence Scoring
    "score_confidence",
    "ConfidenceScorer",
    "ConfidenceResult",
]
