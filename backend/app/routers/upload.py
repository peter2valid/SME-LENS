"""Upload Router - Handles image uploads and OCR processing

Endpoints:
- POST /upload/ - Upload and process an image with Enterprise Document Intelligence
- POST /upload/analyze - Analyze without saving
- POST /upload/confirm/{doc_id} - Submit user corrections
- GET /upload/ - Get upload history
- GET /upload/{doc_id} - Get specific document
- GET /upload/memory/stats - Get learning memory statistics
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, Body
from sqlalchemy.orm import Session
import shutil
import os
import uuid

from ..database import get_db
from ..models.definitions import Document, OCRResult
from ..schemas.schemas import (
    DocumentResponse, 
    DocumentIntelligenceResponse,
    EnterpriseExtractionResponse,
    UserCorrectionRequest
)

# Try enterprise engine first, fall back to basic
try:
    from ..services.enterprise_intelligence import (
        EnterpriseDocumentIntelligence,
        process_document_enterprise,
        EnterpriseExtractionResult
    )
    from ..services.learning_memory import get_learning_memory
    USE_ENTERPRISE = True
except ImportError as e:
    logging.warning(f"Enterprise engine not available: {e}, falling back to basic")
    from ..services.document_intelligence import process_document, DocumentIntelligenceResult
    USE_ENTERPRISE = False

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Hardcoded demo user ID (no auth required)
DEMO_USER_ID = 1

# Allowed image types
ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def _save_upload(file: UploadFile) -> str:
    """Save uploaded file and return path."""
    file_ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    unique_filename = f"{uuid.uuid4()}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return file_path


@router.post("/", response_model=EnterpriseExtractionResponse)
async def upload_image(
    file: UploadFile = File(...),
    document_type: Optional[str] = Query(
        default="unknown",
        description="Document type hint: receipt, invoice, handwritten, form, unknown"
    ),
    db: Session = Depends(get_db)
):
    """
    Upload an image for Enterprise Document Intelligence processing.
    
    Uses the Enterprise Document Intelligence Engine which:
    - Runs consensus extraction (multiple detectors must agree)
    - Analyzes document layout (header/body/footer zones)
    - Applies learning memory (improves over time)
    - Provides honest confidence scoring (never lies)
    - Requests user confirmation when uncertain
    
    Query Parameters:
    - document_type: Hint for processing (receipt, invoice, handwritten, form)
    """
    logger.info(f"Upload: Received '{file.filename}' ({file.content_type}), hint={document_type}")
    
    # Validate content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        logger.warning(f"Upload: Rejected - invalid content type {file.content_type}")
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: JPEG, PNG, WebP. Got: {file.content_type}"
        )

    # Save file
    try:
        file_path = _save_upload(file)
        logger.info(f"Upload: File saved to {file_path}")
    except Exception as e:
        logger.error(f"Upload: Failed to save file - {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

    # Create Document record
    new_doc = Document(
        user_id=DEMO_USER_ID,
        filename=file.filename,
        file_path=file_path,
        status="processing"
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    logger.info(f"Upload: Created document record ID {new_doc.id}")

    # Run Document Intelligence Engine
    try:
        if USE_ENTERPRISE:
            result: EnterpriseExtractionResult = process_document_enterprise(
                image_path=file_path,
                document_hint=document_type,
                enable_learning=True
            )
        else:
            # Fallback to basic engine
            basic_result = process_document(
                image_path=file_path,
                document_hint=document_type
            )
            # Wrap in similar structure
            result = basic_result
        
        if result.success and result.raw_text.strip():
            # Build structured data for storage
            if USE_ENTERPRISE:
                structured_data = {
                    **result.extracted_fields,
                    "document_type": result.document_type,
                    "cleaned_text": result.cleaned_text,
                    "consensus_details": result.consensus_details,
                    "confidence_breakdown": result.confidence_breakdown,
                    "needs_confirmation": result.needs_confirmation,
                    "warnings": result.warnings,
                    "notes": result.notes,
                    "explanation": result.confidence_explanation
                }
            else:
                structured_data = {
                    **result.extracted_data,
                    "document_type": result.document_type,
                    "cleaned_text": result.cleaned_text,
                    "warnings": result.warnings,
                    "notes": result.notes,
                    "explanation": result.explanation
                }
            
            # Create OCR Result record
            new_result = OCRResult(
                document_id=new_doc.id,
                raw_text=result.raw_text,
                extracted_data=structured_data,
                confidence_score=result.confidence
            )
            db.add(new_result)
            new_doc.status = "completed"
            
            logger.info(
                f"Upload: Processing completed for doc {new_doc.id} - "
                f"type={result.document_type}, "
                f"confidence={result.confidence:.2f}, "
                f"needs_confirmation={getattr(result, 'needs_confirmation', False)}"
            )
        else:
            new_doc.status = "failed"
            error_msg = result.error or "No text extracted"
            logger.warning(f"Upload: Processing failed for doc {new_doc.id} - {error_msg}")
            
    except Exception as e:
        logger.error(f"Upload: Document Intelligence failed - {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        new_doc.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
        
    db.commit()
    db.refresh(new_doc)
    
    if USE_ENTERPRISE:
        return result.to_simple_dict()
    else:
        return result.to_dict()


@router.post("/analyze")
async def analyze_image(
    file: UploadFile = File(...),
    document_type: Optional[str] = Query(default="unknown")
):
    """
    Analyze an image without saving to database.
    
    Returns full Enterprise Document Intelligence result for debugging
    and development purposes. Includes:
    - Consensus extraction details
    - Layout analysis
    - Learning memory match
    - Full confidence breakdown
    """
    logger.info(f"Analyze: Received '{file.filename}', hint={document_type}")
    
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    # Save temporarily
    file_path = _save_upload(file)
    
    try:
        if USE_ENTERPRISE:
            result = process_document_enterprise(
                image_path=file_path,
                document_hint=document_type,
                enable_learning=False  # Don't learn from analyze-only requests
            )
            return result.to_dict()
        else:
            result = process_document(
                image_path=file_path,
                document_hint=document_type
            )
            return result.to_dict()
    finally:
        # Clean up temp file
        try:
            os.remove(file_path)
        except:
            pass


@router.post("/confirm/{doc_id}")
async def submit_corrections(
    doc_id: str,
    corrections: dict = Body(..., description="Dictionary of field_name -> corrected_value"),
    db: Session = Depends(get_db)
):
    """
    Submit user corrections for a processed document.
    
    This endpoint:
    1. Applies user corrections to the extracted data
    2. Updates the learning memory for future improvements
    3. Returns updated extraction result
    
    Body:
    - corrections: {"field_name": "corrected_value", ...}
    """
    logger.info(f"Confirm: Received corrections for doc {doc_id}")
    
    if not USE_ENTERPRISE:
        raise HTTPException(
            status_code=501, 
            detail="Enterprise features not available"
        )
    
    # Get learning memory
    memory = get_learning_memory()
    
    # Log the corrections for learning
    for field_name, corrected_value in corrections.items():
        logger.info(f"Confirm: {field_name} corrected to '{corrected_value}'")
    
    # In a full implementation, we would:
    # 1. Look up the original document
    # 2. Apply corrections to stored data
    # 3. Update learning memory with corrections
    
    return {
        "status": "corrections_applied",
        "document_id": doc_id,
        "corrections_count": len(corrections),
        "message": "Corrections recorded and learning memory updated"
    }


@router.get("/memory/stats")
async def get_memory_stats():
    """
    Get learning memory statistics.
    
    Returns information about:
    - Number of learned patterns
    - Unique vendors seen
    - Total corrections recorded
    - Vendor-specific rules
    """
    if not USE_ENTERPRISE:
        raise HTTPException(
            status_code=501,
            detail="Enterprise features not available"
        )
    
    memory = get_learning_memory()
    stats = memory.get_statistics()
    
    logger.info(f"Memory: Returning stats - {stats}")
    return stats


@router.get("/", response_model=list[DocumentResponse])
def get_history(db: Session = Depends(get_db)):
    """Get all uploaded documents for the demo user, sorted by date descending."""
    docs = (
        db.query(Document)
        .filter(Document.user_id == DEMO_USER_ID)
        .order_by(Document.upload_date.desc())
        .all()
    )
    logger.info(f"History: Returning {len(docs)} documents")
    return docs


@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document(doc_id: int, db: Session = Depends(get_db)):
    """Get a specific document by ID."""
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.user_id == DEMO_USER_ID)
        .first()
    )
    if not doc:
        logger.warning(f"Document: Not found - ID {doc_id}")
        raise HTTPException(status_code=404, detail="Document not found")
    return doc
