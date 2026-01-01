from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List, Any
from datetime import datetime

# User Schemas
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserLogin(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# OCR/Document Schemas
class OCRData(BaseModel):
    total: Optional[float] = None
    vendor: Optional[str] = None
    date: Optional[str] = None
    raw_text: Optional[str] = None

class OCRResultResponse(BaseModel):
    id: int
    document_id: int
    raw_text: Optional[str] = None
    extracted_data: Optional[dict] = None
    confidence_score: Optional[float] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class DocumentBase(BaseModel):
    filename: str

class DocumentCreate(DocumentBase):
    pass

class DocumentResponse(DocumentBase):
    id: int
    user_id: int
    file_path: str
    status: str
    upload_date: datetime
    ocr_result: Optional[OCRResultResponse] = None

    model_config = ConfigDict(from_attributes=True)
