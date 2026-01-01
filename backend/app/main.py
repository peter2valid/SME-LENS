from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth, upload
from .database import engine, Base

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SMELens API", description="Backend for SMELens OCR Tool", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(upload.router, prefix="/upload", tags=["Upload"])

@app.get("/")
def read_root():
    return {"message": "Welcome to SMELens API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
