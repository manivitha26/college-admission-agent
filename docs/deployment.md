# Deploying to IBM Cloud (Code Engine) — Step-by-Step Guide

This guide deploys the College Admission Agent to **IBM Cloud Code Engine**
(the container-as-a-service offering available on the IBM Cloud Lite / free tier).

## Architecture on IBM Cloud

```
Internet
    │
    ▼
IBM Code Engine
  ┌─────────────────────────────┐
  │  frontend app (nginx)       │  ← public HTTPS endpoint
  │  port 8080                  │
  │  proxies /api/* →           │
  └─────────────┬───────────────┘
                │ internal traffic
                ▼
  ┌─────────────────────────────┐
  │  backend app (uvicorn)      │  ← private (or public) endpoint
  │  port 8080                  │
  │  reads IBM watsonx secrets  │
  └─────────────────────────────┘
```

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| IBM Cloud CLI | latest | https://cloud.ibm.com/docs/cli |
| IBM Cloud CLI Code Engine plugin | latest | `ibmcloud plugin install code-engine` |
| IBM Cloud Container Registry plugin | latest | `ibmcloud plugin install container-registry` |
| Docker Desktop | 24+ | https://docs.docker.com/get-docker/ |
| IBM Cloud account | Lite (free) | https://cloud.ibm.com/registration |

---

## Step 1 — IBM Cloud Account Setup

### 1.1 Create an IBM Cloud account
Go to https://cloud.ibm.com/registration and sign up (Lite plan is free).

### 1.2 Create a watsonx.ai project
1. Open https://dataplatform.cloud.ibm.com
2. Click **New project → Create an empty project**
3. Name it `college-admission-agent`
4. Click **Create**
5. Go to **Manage → General** and copy the **Project ID** — you will need it later

### 1.3 Get your IBM Cloud API Key
> ⚠ Your API key is a secret. Never commit it to version control.

1. Go to https://cloud.ibm.com/iam/apikeys
2. Click **Create an IBM Cloud API key**
3. Name it `college-admission-agent-key`
4. Click **Create**, then **Copy** or **Download** the key immediately
5. Store it securely (e.g. a password manager) — IBM will not show it again

### 1.4 Verify Granite access
1. In your watsonx.ai project, open the **Assets** tab
2. Click **New asset → Work with models**
3. Confirm you can see `ibm/granite-3-8b-instruct` in the model list
4. If prompted to associate a Watson Machine Learning service, do so (Lite tier is free)

---

## Step 2 — Local Smoke Test with Docker Compose

Before deploying to the cloud, verify the containers work locally.

```bash
# 1. Clone / open the project root
cd college-admission-agent

# 2. Create backend/.env from the example
cp backend/.env.example backend/.env
#    Open backend/.env and fill in:
#      WATSONX_API_KEY=<your key>
#      WATSONX_PROJECT_ID=<your project id>

# 3. Build and start both containers
docker compose up --build

# 4. Open http://localhost:3000 — the UI should load
# 5. Open http://localhost:8080/api/health — should return {"status":"ok",...}

# 6. Ingest a test PDF
docker compose exec backend python ingest.py --file /path/to/sample.pdf

# 7. Ask a question in the chat tab — verify you get a Granite answer

# 8. Stop everything
docker compose down
```

---

## Step 3 — Push Images to IBM Cloud Container Registry

IBM Code Engine pulls images from IBM Cloud Container Registry (ICR).

```bash
# 3.1  Log in to IBM Cloud
ibmcloud login --apikey <YOUR_IBM_CLOUD_API_KEY> -r us-south

# 3.2  Target your resource group (use "Default" on Lite)
ibmcloud target -g Default

# 3.3  Log in to ICR
ibmcloud cr login

# 3.4  Create a namespace in ICR (once only; pick a unique name)
ibmcloud cr namespace-add college-admission-agent

# 3.5  Build and push the BACKEND image
docker build -t us.icr.io/college-admission-agent/backend:latest ./backend
docker push  us.icr.io/college-admission-agent/backend:latest

# 3.6  Build and push the FRONTEND image
docker build -t us.icr.io/college-admission-agent/frontend:latest ./frontend
docker push  us.icr.io/college-admission-agent/frontend:latest
```

> **Lite tier note:** ICR gives you 500 MB of free storage. The backend image
> is ~1.5 GB because of PyTorch / sentence-transformers. Use the multi-stage
> Dockerfile (already in place) which keeps the final image as small as possible.
> If storage is a concern, consider using `intfloat/multilingual-e5-small` for
> the embedding model (only ~120 MB).

---

## Step 4 — Create a Code Engine Project

```bash
# 4.1  Install the Code Engine plugin if not already done
ibmcloud plugin install code-engine

# 4.2  Create a Code Engine project (once only)
ibmcloud ce project create --name college-admission-agent

# 4.3  Select the project for subsequent commands
ibmcloud ce project select --name college-admission-agent
```

---

## Step 5 — Create the Registry Access Secret

Code Engine needs credentials to pull from your ICR namespace.

```bash
ibmcloud ce secret create \
  --name icr-secret \
  --format registry \
  --server us.icr.io \
  --username iamapikey \
  --password <YOUR_IBM_CLOUD_API_KEY>
```

---

## Step 6 — Store IBM watsonx Credentials as Code Engine Secrets

> ⚠ Secrets are encrypted at rest in Code Engine.
>   Never pass credentials as plain `--env` flags — use `--env-from-secret`.

```bash
# 6.1  Create a secret that holds the two required watsonx credentials
ibmcloud ce secret create \
  --name watsonx-credentials \
  --from-literal WATSONX_API_KEY=<YOUR_IBM_CLOUD_API_KEY> \
  --from-literal WATSONX_PROJECT_ID=<YOUR_WATSONX_PROJECT_ID>

# 6.2  (Optional) Override the model or region if needed
#      The defaults (ibm/granite-3-8b-instruct, us-south) work for most accounts.
#      If your watsonx.ai project is in a different region, add:
#
# ibmcloud ce secret create \
#   --name watsonx-config \
#   --from-literal WATSONX_URL=https://eu-de.ml.cloud.ibm.com \
#   --from-literal GRANITE_MODEL_ID=ibm/granite-3-8b-instruct
```

---

## Step 7 — Deploy the Backend Application

```bash
ibmcloud ce application create \
  --name college-backend \
  --image us.icr.io/college-admission-agent/backend:latest \
  --registry-secret icr-secret \
  --port 8080 \
  --cpu 1 \
  --memory 4G \
  --min-scale 0 \
  --max-scale 1 \
  --env-from-secret watsonx-credentials \
  --env PORT=8080 \
  --env CHROMA_PERSIST_DIR=/app/data/vectorstore \
  --env PDF_UPLOAD_DIR=/app/data/pdfs \
  --env HF_HOME=/app/data/hf_cache \
  --env GRANITE_MODEL_ID=ibm/granite-3-8b-instruct \
  --visibility private
```

> **`--visibility private`** — the backend is not directly accessible from the
> internet; only other apps in the same Code Engine project (the frontend) can
> reach it. This is the secure default.
>
> **`--min-scale 0`** — the app scales to zero when idle (Lite tier free quota).
> The first request after idle takes ~30–60 s (cold start) because the embedding
> model must be loaded. Set `--min-scale 1` to avoid cold starts (uses Lite quota).

Get the backend's internal URL:

```bash
ibmcloud ce application get --name college-backend --output url
# Example output: https://college-backend.<hash>.private.us-south.codeengine.appdomain.cloud
```

---

## Step 8 — Deploy the Frontend Application

Replace `<BACKEND_INTERNAL_URL>` with the URL from Step 7.

```bash
ibmcloud ce application create \
  --name college-frontend \
  --image us.icr.io/college-admission-agent/frontend:latest \
  --registry-secret icr-secret \
  --port 8080 \
  --cpu 0.25 \
  --memory 0.5G \
  --min-scale 0 \
  --max-scale 1 \
  --visibility public
```

> The frontend's `nginx.conf` proxies `/api/*` to `http://backend:8080`.
> In Code Engine, services in the same project can reach each other by their
> application name. Update `nginx.conf`'s `proxy_pass` line if the backend
> application is named differently:
>
> ```nginx
> proxy_pass http://college-backend:8080;
> ```

Get the public frontend URL:

```bash
ibmcloud ce application get --name college-frontend --output url
# Example: https://college-frontend.<hash>.us-south.codeengine.appdomain.cloud
```

Open this URL in a browser — the app is live.

---

## Step 9 — Ingest PDF Documents

After deployment you must load knowledge documents before the chatbot can answer.

```bash
# Option A: via the UI
# Open the app → click the 📁 Documents tab → drag and drop a PDF

# Option B: via the backend API (using curl)
curl -X POST https://<BACKEND_PUBLIC_URL>/api/upload \
  -F "file=@/path/to/admission_brochure.pdf"

# Option C: run the batch ingest script inside the container
ibmcloud ce job run \
  --name ingest-pdfs \
  --image us.icr.io/college-admission-agent/backend:latest \
  --registry-secret icr-secret \
  --env-from-secret watsonx-credentials \
  --env CHROMA_PERSIST_DIR=/app/data/vectorstore \
  --env PDF_UPLOAD_DIR=/app/data/pdfs \
  --env HF_HOME=/app/data/hf_cache \
  --command python \
  --argument ingest.py
```

> **Lite tier persistence note:** Code Engine applications are stateless.
> ChromaDB data and uploaded PDFs stored inside the container are lost when
> the container restarts. For persistent storage on Lite tier:
>
> - Use **IBM Cloud Object Storage** (free 25 GB) to store PDFs and sync them
>   at startup, **or**
> - Pre-build the ChromaDB index into the Docker image (`COPY data/ /app/data/`)
>   and rebuild the image whenever documents change.
>
> The simplest zero-cost approach for a demo is to bake the pre-ingested
> ChromaDB data into the image (see `docs/deployment-persistence.md`).

---

## Step 10 — Update a Deployment

After a code change, rebuild and push the image, then redeploy:

```bash
# Backend change
docker build -t us.icr.io/college-admission-agent/backend:latest ./backend
docker push  us.icr.io/college-admission-agent/backend:latest
ibmcloud ce application update --name college-backend --image us.icr.io/college-admission-agent/backend:latest

# Frontend change
docker build -t us.icr.io/college-admission-agent/frontend:latest ./frontend
docker push  us.icr.io/college-admission-agent/frontend:latest
ibmcloud ce application update --name college-frontend --image us.icr.io/college-admission-agent/frontend:latest
```

---

## Environment Variables Reference

### Backend (required)

| Variable | Where to set | Description |
|----------|-------------|-------------|
| `WATSONX_API_KEY` | Code Engine secret `watsonx-credentials` | IBM Cloud API key |
| `WATSONX_PROJECT_ID` | Code Engine secret `watsonx-credentials` | watsonx.ai project ID |

### Backend (optional — safe defaults shown)

| Variable | Default | Description |
|----------|---------|-------------|
| `WATSONX_URL` | `https://us-south.ml.cloud.ibm.com` | Regional endpoint |
| `GRANITE_MODEL_ID` | `ibm/granite-3-8b-instruct` | Model to use |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | HuggingFace embedding model |
| `CHROMA_PERSIST_DIR` | `/app/data/vectorstore` | ChromaDB storage path |
| `PDF_UPLOAD_DIR` | `/app/data/pdfs` | Uploaded PDF storage path |
| `HF_HOME` | `/app/data/hf_cache` | HuggingFace model cache path |
| `CHUNK_SIZE` | `800` | Text chunk size (characters) |
| `CHUNK_OVERLAP` | `150` | Chunk overlap (characters) |
| `RETRIEVAL_TOP_K` | `4` | Chunks retrieved per question |
| `PORT` | `8080` | Uvicorn listen port |

### Frontend (build-time only)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | *(empty)* | Backend URL; leave empty when nginx proxies `/api/*` |

---

## Troubleshooting

### "IBM watsonx credentials not configured" in startup logs
→ Check the secret was created correctly:
```bash
ibmcloud ce secret get --name watsonx-credentials
```

### Chat returns HTTP 503
→ Credentials are missing or wrong. Verify `WATSONX_API_KEY` and `WATSONX_PROJECT_ID`.

### "ChromaDB collection is empty" warning
→ No PDFs have been ingested yet. Upload via the 📁 Documents tab.

### Cold start takes 60+ seconds
→ The embedding model is being loaded. Set `--min-scale 1` to keep one instance warm.

### Container fails to start (OOM)
→ The embedding model + ChromaDB requires ~1.5 GB RAM. Ensure `--memory 4G` is set.

### ICR image push: "unauthorized"
→ Re-run `ibmcloud cr login` — the Docker credential token expires after 1 hour.
