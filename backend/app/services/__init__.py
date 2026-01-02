"""SMELens OCR Services Package

This package contains the Document Intelligence Engine components:

Core Components:
- preprocessing: Image enhancement for optimal OCR
- ocr_engine: Multi-pass Tesseract OCR with adaptive configurations
- text_cleaner: OCR error correction and text normalization
- field_extractor: Deterministic structured data extraction
- confidence_scorer: Explainable confidence scoring
- document_intelligence: Main orchestrator combining all components

Enterprise Components (NEW):
- consensus_engine: Multi-detector consensus extraction
- layout_analyzer: Layout-aware extraction with zones
- confirmation_flow: Human-in-the-loop confirmation
- learning_memory: Persistent learning from corrections
- enterprise_confidence: Honest confidence scoring
- enterprise_intelligence: Main enterprise orchestrator

Usage:
    # Basic usage
    from app.services.document_intelligence import process_document
    result = process_document("receipt.jpg", document_hint="receipt")
    
    # Enterprise usage (recommended)
    from app.services.enterprise_intelligence import process_document_enterprise
    result = process_document_enterprise("receipt.jpg", document_hint="receipt")
    print(result.extracted_fields)
    print(result.confidence)
    print(result.needs_confirmation)
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

# Enterprise modules
from .consensus_engine import (
    extract_with_consensus,
    ConsensusExtractor,
    ConsensusResult
)

from .layout_analyzer import (
    analyze_layout,
    LayoutAnalyzer,
    LayoutAnalysisResult,
    Zone
)

from .confirmation_flow import (
    request_user_confirmation,
    ConfirmationManager,
    ConfirmationRequest
)

from .learning_memory import (
    apply_learning_memory,
    get_learning_memory,
    LearningMemory,
    MemoryMatchResult
)

from .enterprise_confidence import (
    compute_confidence,
    EnterpriseConfidenceScorer,
    ConfidenceBreakdown,
    ConfidenceLevel
)

from .enterprise_intelligence import (
    process_document_enterprise,
    EnterpriseDocumentIntelligence,
    EnterpriseExtractionResult
)

__all__ = [
    # Main entry points
    "process_document",
    "process_document_enterprise",  # Recommended
    "DocumentIntelligenceEngine",
    "DocumentIntelligenceResult",
    "EnterpriseDocumentIntelligence",
    "EnterpriseExtractionResult",
    
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
    
    # Enterprise: Consensus
    "extract_with_consensus",
    "ConsensusExtractor",
    "ConsensusResult",
    
    # Enterprise: Layout
    "analyze_layout",
    "LayoutAnalyzer",
    "LayoutAnalysisResult",
    "Zone",
    
    # Enterprise: Confirmation
    "request_user_confirmation",
    "ConfirmationManager",
    "ConfirmationRequest",
    
    # Enterprise: Learning
    "apply_learning_memory",
    "get_learning_memory",
    "LearningMemory",
    "MemoryMatchResult",
    
    # Enterprise: Confidence
    "compute_confidence",
    "EnterpriseConfidenceScorer",
    "ConfidenceBreakdown",
    "ConfidenceLevel",
]
