from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="user")  # admin, user
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    uploads = relationship("Document", back_populates="owner")

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    filename = Column(String)
    file_path = Column(String)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    upload_date = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="uploads")
    ocr_result = relationship("OCRResult", back_populates="document", uselist=False)

class OCRResult(Base):
    __tablename__ = "ocr_results"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    raw_text = Column(Text)
    extracted_data = Column(JSON)  # Stores structured data: {total: 100, vendor: "ABC", date: "2023-01-01"}
    confidence_score = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="ocr_result")
