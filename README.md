# SMELens

AI-powered OCR tool for SMEs. Uses Google Cloud Vision to extract data from invoices and receipts.

## Setup

### Backend
1. `cd backend`
2. `python -m venv venv`
3. `source venv/bin/activate`
4. `pip install -r requirements.txt`
5. `uvicorn app.main:app --reload`

### Frontend
1. `cd frontend`
2. `npm install`
3. `npm run dev`

## Features
- Drag & Drop Image Upload
- Automated Text Extraction
- Dashboard Analytics
