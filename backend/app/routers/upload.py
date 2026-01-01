"""Upload Router - Handles image uploads and OCR processing

Endpoints:
- POST /upload/ - Upload and process an image with Document Intelligence
- POST /upload/simple - Simple OCR without full intelligence pipeline
- GET /upload/ - Get upload history
- GET /upload/{doc_id} - Get specific document
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session
import shutil
import os
import uuid

from ..database import get_db
from ..models.definitions import Document, OCRResult
from ..schemas.schemas import DocumentResponse
from ..services.document_intelligence import process_document, DocumentIntelligenceResult

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


@router.post("/", response_model=DocumentResponse)
async def upload_image(
    file: UploadFile = File(...),
    document_type: Optional[str] = Query(
        default="unknown",
        description="Document type hint: receipt, invoice, handwritten, form, unknown"
    ),
    db: Session = Depends(get_db)
):
    """
    Upload an image for intelligent OCR processing.
    
    Uses the Document Intelligence Engine which:
    - Preprocesses image for optimal OCR quality
    - Runs multi-pass OCR with different configurations
    - Cleans and corrects OCR text errors
    - Extracts structured fields (vendor, total, date, currency)
    - Provides confidence scoring with reasoning
    
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
        result: DocumentIntelligenceResult = process_document(
            image_path=file_path,
            document_hint=document_type
        )
        
        if result.success and result.raw_text.strip():
            # Build structured data for storage
            structured_data = {
                **result.extracted_data,
                "document_type": result.document_type,
                "cleaned_text": result.cleaned_text,
                "all_amounts": result.all_amounts,
                "all_dates": result.all_dates,
                "confidence_reason": result.confidence_reason,
                "warnings": result.warnings,
                "notes": result.notes
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
                f"vendor={result.extracted_data.get('vendor')}, "
                f"total={result.extracted_data.get('total_amount')}, "
                f"confidence={result.confidence:.2f}"
            )
        else:
            new_doc.status = "failed"
            error_msg = result.error or "No text extracted"
            logger.warning(f"Upload: Processing failed for doc {new_doc.id} - {error_msg}")
            
    except Exception as e:
        logger.error(f"Upload: Document Intelligence failed - {type(e).__name__}: {e}")
        new_doc.status = "failed"
        
    db.commit()
    db.refresh(new_doc)
    
    return new_doc


@router.post("/analyze")
async def analyze_image(
    file: UploadFile = File(...),
    document_type: Optional[str] = Query(default="unknown")
):
    """
    Analyze an image without saving to database.
    
    Returns full Document Intelligence result for debugging
    and development purposes.
    """
    logger.info(f"Analyze: Received '{file.filename}', hint={document_type}")
    
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    # Save temporarily
    file_path = _save_upload(file)
    
    try:
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
