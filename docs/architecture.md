# Architecture

## Request Flow

```
User types question
      │
      ▼
React ChatWindow
      │  POST /api/chat  { question }
      ▼
FastAPI  /api/chat  (chat.py router)
      │
      ▼
rag_chain.ask()
  ├─ vectorstore.similarity_search(question, k=4)
  │        └─ ChromaDB  (persisted embeddings)
  ├─ admission_prompt  (system + human template)
  └─ WatsonxLLM  (IBM Granite)
      │
      ▼
ChatResponse  { answer, sources: [{ file_name, page }] }
      │
      ▼
React renders answer + SourceList citations
```

## Ingestion Flow

```
PDF file uploaded
      │
      ▼
ingestion.ingest_pdf()
  ├─ PyPDFLoader          → list of Document objects (one per page)
  ├─ RecursiveCharacterTextSplitter → smaller chunks with metadata
  └─ vectorstore.add_documents()
           └─ HuggingFaceEmbeddings → ChromaDB (persisted)
```
