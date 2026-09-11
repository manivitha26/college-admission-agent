# College Admission Agent

A RAG-powered chatbot that answers college admission questions using IBM Granite
(via IBM watsonx.ai), LangChain, ChromaDB, FastAPI, and React.

## Stack

| Layer        | Technology                          |
|--------------|-------------------------------------|
| Frontend     | React 18 + Vite + nginx             |
| Backend      | Python FastAPI + Uvicorn            |
| RAG          | LangChain                           |
| Vector DB    | ChromaDB (local persistent)         |
| LLM          | IBM Granite via IBM watsonx.ai      |
| Embeddings   | sentence-transformers (local)       |
| Deployment   | IBM Cloud Code Engine (containers)  |

## Quick Start (local)

```bash
# 1. Backend
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows
# source .venv/bin/activate                       # macOS/Linux
pip install -r requirements.txt
cp .env.example .env   # fill in WATSONX_API_KEY and WATSONX_PROJECT_ID
uvicorn main:app --reload --port 8000

# 2. Frontend (new terminal)
cd frontend
npm install
npm run dev            # opens http://localhost:5173
```

## Docker (local smoke test)

```bash
cp backend/.env.example backend/.env   # fill in credentials
docker compose up --build              # http://localhost:3000
```

## IBM Cloud Deployment

See [`docs/deployment.md`](docs/deployment.md) for the full step-by-step guide.

## Documentation

| File | Contents |
|------|----------|
| `docs/setup.md` | Local development setup |
| `docs/deployment.md` | IBM Cloud Code Engine deployment |
| `docs/architecture.md` | System architecture and request flow |
| `backend/.env.example` | All backend environment variables |
| `frontend/.env.example` | Frontend build-time variables |
