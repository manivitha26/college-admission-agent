# Setup Guide

## Prerequisites
- Python 3.11+
- Node.js 20+
- An IBM Cloud account with watsonx.ai access

## Backend Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env          # Fill in your credentials
uvicorn main:app --reload
```

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

## Adding Knowledge Documents

Upload PDF files through the UI sidebar **or** via the API:

```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@college_brochure.pdf"
```

## Environment Variables

| Variable              | Description                          |
|-----------------------|--------------------------------------|
| `WATSONX_API_KEY`     | IBM Cloud API key                    |
| `WATSONX_PROJECT_ID`  | watsonx.ai project ID                |
| `WATSONX_URL`         | Regional endpoint URL                |
| `CHROMA_PERSIST_DIR`  | Path for the ChromaDB data directory |
| `PDF_UPLOAD_DIR`      | Path where uploaded PDFs are stored  |
