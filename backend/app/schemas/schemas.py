from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List, Any, Dict
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


# Basic Document Intelligence Response (backward compatible)
class DocumentIntelligenceResponse(BaseModel):
    document_type: str
    raw_text: str
    cleaned_text: str
    extracted_data: dict
    confidence: float
    explanation: str
    
    # Extra fields for frontend/debugging
    confidence_level: Optional[str] = None
    confidence_reason: Optional[str] = None
    notes: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    suggestions: Optional[List[str]] = None
    currency: Optional[str] = None
    success: Optional[bool] = None
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Enterprise Document Intelligence Response
class ConsensusDetail(BaseModel):
    """Details about consensus extraction for a field."""
    field_name: str
    value: Optional[Any] = None
    consensus_level: str
    agreement: str  # e.g., "3/4"
    agreeing_detectors: List[str] = []
    needs_confirmation: bool = False
    confirmation_reason: Optional[str] = None


class ConfidenceBreakdown(BaseModel):
    """Detailed confidence breakdown."""
    confidence: float
    confidence_level: str
    confidence_explanation: str
    factors: List[Dict[str, Any]] = []
    warnings: List[str] = []
    suggestions: List[str] = []


class ConfirmationField(BaseModel):
    """A field requiring user confirmation."""
    field_name: str
    display_name: str
    current_value: Optional[Any] = None
    candidates: List[Dict[str, Any]] = []
    reason: str
    reason_text: str
    priority: str
    context: str


class ConfirmationRequest(BaseModel):
    """Request for user confirmation."""
    needs_confirmation: bool
    fields: List[ConfirmationField] = []
    document_id: str
    document_type: str
    overall_confidence: float
    summary: str


class MemoryMatch(BaseModel):
    """Learning memory match result."""
    found: bool
    score: float
    explanation: str


class EnterpriseExtractionResponse(BaseModel):
    """
    Enterprise-grade extraction response.
    
    Includes:
    - Consensus-validated fields
    - Honest confidence scoring
    - Human-in-the-loop confirmation
    - Learning memory feedback
    """
    # Core extraction
    document_type: str
    raw_text: str
    cleaned_text: str
    extracted_data: dict
    
    # Confidence (enterprise-grade, never lies)
    confidence: float
    confidence_level: str
    explanation: str
    confidence_reason: Optional[str] = None
    
    # Human-in-the-loop
    needs_confirmation: Optional[bool] = False
    confirmation_request: Optional[Dict] = None
    
    # Learning memory
    memory_match: Optional[Dict] = None
    
    # Warnings and suggestions
    warnings: Optional[List[str]] = []
    suggestions: Optional[List[str]] = []
    notes: Optional[List[str]] = []
    
    # Metadata
    currency: Optional[str] = None
    success: bool = True
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserCorrectionRequest(BaseModel):
    """Request to apply user corrections."""
    document_id: str
    corrections: Dict[str, Any]  # field_name -> corrected_value

