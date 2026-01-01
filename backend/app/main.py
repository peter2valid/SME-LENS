"""SMELens Backend - FastAPI Application

This is the main entry point for the SMELens OCR backend.
Run with: uvicorn app.main:app --reload --port 8000
"""
import logging
import shutil
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth, upload
from .database import engine, Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create database tables on startup
Base.metadata.create_all(bind=engine)
logger.info("Database tables created/verified")

# Initialize FastAPI app
app = FastAPI(
    title="SMELens API",
    description="Backend for SMELens OCR Tool - Extracts text from receipts and invoices",
    version="1.0.0"
)

# CORS - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(upload.router, prefix="/upload", tags=["Upload"])
logger.info("Routers registered: /auth, /upload")


@app.get("/", tags=["Root"])
def read_root():
    """Root endpoint - API welcome message"""
    return {
        "message": "Welcome to SMELens API",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint - Returns service status and OCR engine info"""
    # Check if Tesseract is available
    tesseract_available = shutil.which("tesseract") is not None
    
    return {
        "status": "running",
        "service": "SMELens Backend",
        "ocr_engine": "tesseract",
        "ocr_available": tesseract_available,
        "version": "1.0.0"
    }
