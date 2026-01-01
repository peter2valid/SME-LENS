from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
import shutil
import os
import uuid
from ..database import get_db
from ..models.definitions import Document, OCRResult
from ..schemas.schemas import DocumentResponse
from ..services.ocr import process_image

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Hardcoded demo user ID
DEMO_USER_ID = 1

@router.post("/", response_model=DocumentResponse)
async def upload_image(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Only JPEG and PNG images supported")

    # Generate unique filename
    file_ext = file.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Create Document record (No Auth - All assigned to Demo User)
    new_doc = Document(
        user_id=DEMO_USER_ID,
        filename=file.filename,
        file_path=file_path,
        status="processing"
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    # Run OCR (Sync for now, should be background task in specific production)
    ocr_data = process_image(file_path)
    
    if ocr_data:
        # Create OCR Result
        new_result = OCRResult(
            document_id=new_doc.id,
            raw_text=ocr_data.get("raw_text", ""),
            extracted_data=ocr_data.get("structured_data", {}),
            confidence_score=ocr_data.get("confidence", 0.0)
        )
        db.add(new_result)
        new_doc.status = "completed"
    else:
        new_doc.status = "failed"
        
    db.commit()
    db.refresh(new_doc)
    
    return new_doc

@router.get("/", response_model=list[DocumentResponse])
def get_history(db: Session = Depends(get_db)):
    # Return all documents for demo user
    return db.query(Document).filter(Document.user_id == DEMO_USER_ID).order_by(Document.upload_date.desc()).all()

@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == DEMO_USER_ID).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc
