# Complete Cloud Deployment Guide: Semantic PYQ Analyzer & Study Heatmap

This guide walks you step-by-step through deploying your **Semantic PYQ Analyzer & Study Heatmap** project to the public internet using 100% free-tier cloud services. Once deployed, anyone with your public URL can access and use every feature without needing your laptop powered on or local Ollama running.

---

## 1. Complete System Architecture

```mermaid
flowchart TD
    User["Student / Faculty Browser"] -->|HTTPS| Frontend["Render Static Site\n(React 19 + TypeScript + Vite)"]
    Frontend -->|REST API / HTTPS| Backend["Render Web Service\n(FastAPI + Uvicorn)"]
    
    subgraph "Cloud Backend & Persistence"
        Backend -->|pgvector Cosine & Relational| NeonDB["Neon PostgreSQL\n(Persistent + pgvector 384-dim)"]
        Backend -->|Store & Retrieve Files| Supabase["Supabase Storage\n(PDF, DOCX, TXT Documents)"]
        Backend -->|RAG Grounding & Chat| Gemini["Google Gemini API\n(gemini-2.5-flash / text-embedding-004)"]
    end
```

### Component Details
1. **Frontend (Render Static Site):** Compiled React 19 SPA served via global CDN with client-side SPA routing rewrite.
2. **Backend (Render Web Service):** FastAPI containerized API running with Uvicorn, bound to dynamic cloud port `$PORT` with auto-TLS.
3. **Database (Neon Serverless PostgreSQL):** Managed PostgreSQL database supporting native `vector` extension and persistent HNSW cosine distance indexes.
4. **Document Storage (Supabase Storage):** Persistent cloud bucket for uploaded syllabi, lecture slides, and notes (bypasses Render's ephemeral disk).
5. **AI Assistant & Embeddings (Google Gemini API):** Official `gemini-2.5-flash` model for contextual study Q&A and `text-embedding-004` (384 dims) for semantic search.

---

## 2. Cloud Services & Free-Tier Specifications

| Service | Provider | Free Tier Limits | Purpose |
| :--- | :--- | :--- | :--- |
| **Frontend Site** | [Render](https://render.com) | Unlimited static builds, 100 GB bandwidth/mo | Hosting React UI |
| **Backend Web Service** | [Render](https://render.com) | 512 MB RAM, spins down after 15m of inactivity | FastAPI backend API |
| **Vector Database** | [Neon](https://neon.tech) | 0.5 GB storage, pgvector extension included | Relational data & embeddings |
| **File Storage** | [Supabase](https://supabase.com) | 1 GB storage, 50MB per file limit | Note uploads (PDF/DOCX/TXT) |
| **LLM & Embeddings** | [Google AI Studio](https://aistudio.google.com) | 15 RPM, 1M TPM, 1,500 requests/day | Study Assistant & Semantic Search |

---

## 3. Step 1: Create a Neon PostgreSQL Database & Enable pgvector

Neon provides a free serverless PostgreSQL database with native `pgvector` support.

1. Go to **[https://console.neon.tech](https://console.neon.tech)** and sign up (or sign in with GitHub).
2. Click **Create Project**:
   - **Project Name:** `pyq-analyzer-db`
   - **Database Name:** `neondb` (default)
   - **Region:** Choose **US East (Ohio)** or **Oregon** (to match Render region for lowest latency).
3. Once created, click on the **SQL Editor** tab in the Neon dashboard.
4. Run this SQL command to verify `pgvector` is ready:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
5. Return to the **Dashboard** page and find your **Connection Details**:
   - Select **Connection string** -> choose **Pooled connection** or direct connection.
   - It will look like:
     ```
     postgresql://neondb_owner:npg_abcdef123@ep-sample-123.us-east-2.aws.neon.tech/neondb?sslmode=require
     ```
   - Copy this entire connection string. We will use it as `DATABASE_URL`.
   > **Note:** The backend automatically normalizes `postgres://` or `postgresql://` into `postgresql+psycopg://` so standard Neon URLs work immediately!

---

## 4. Step 2: Get a Free Google Gemini API Key

1. Go to **[https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)** and sign in with your Google account.
2. Click **Create API Key**.
3. Select your Google Cloud project (or create a new default project).
4. Copy the generated API key (e.g., `AIzaSy...`).
5. Save this key securely. We will use it as `GEMINI_API_KEY`.

---

## 5. Step 3: Configure Cloud Storage on Supabase (Free 1GB)

To ensure uploaded PDFs, DOCX files, and TXT notes persist when Render sleeps or restarts:

1. Go to **[https://supabase.com](https://supabase.com)** and sign in (with GitHub).
2. Click **New Project**:
   - **Name:** `pyq-storage`
   - **Database Password:** (Generate a strong password and save it)
   - **Region:** US East or Oregon
3. Once the project dashboard is ready:
   - In the left sidebar, click **Storage** -> **New Bucket**.
   - **Bucket Name:** `documents` (all lowercase)
   - **Public Bucket:** Toggle to **ON** (Public) or OFF (authenticated download supported).
   - Click **Save Bucket**.
4. Get your API credentials:
   - In the left sidebar, click **Project Settings** (gear icon) -> **API**.
   - Copy the **Project URL** (e.g., `https://xyzabcdef.supabase.co`). This is your `SUPABASE_URL`.
   - Under **Project API Keys**, copy the **`service_role`** secret key (revealed by clicking Reveal). This is your `SUPABASE_SERVICE_ROLE_KEY`.

---

## 6. Step 4: Deploy to Render Using Blueprint (render.yaml)

The repository includes a `render.yaml` blueprint that deploys both the backend and frontend automatically.

1. Go to **[https://dashboard.render.com](https://dashboard.render.com)** and sign in.
2. Click the **New +** button in the top navigation bar and select **Blueprint**.
3. Connect your GitHub repository:
   - **Repository:** `https://github.com/keshavjayaprakash2006-hash/DBMS-.git`
   - Branch: `main`
4. Render will parse `render.yaml` and discover two services:
   - `semantic-pyq-backend` (Web Service)
   - `semantic-pyq-frontend` (Static Site)
5. Fill in the required environment variables prompted by the Render setup screen:

### Backend Service Variables:
| Variable Name | Value Source | Example Value |
| :--- | :--- | :--- |
| `DATABASE_URL` | Neon Connection String | `postgresql+psycopg://neondb_owner:pass@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require` |
| `GEMINI_API_KEY` | Google AI Studio Key | `AIzaSy...` |
| `GEMINI_MODEL` | Default | `gemini-2.5-flash` |
| `EMBEDDING_PROVIDER`| Default | `gemini` |
| `EMBEDDING_MODEL_NAME`| Default | `text-embedding-004` |
| `EMBEDDING_DIMENSION`| Default | `384` |
| `SUPABASE_URL` | Supabase Project URL | `https://xyzabcdef.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase Service Role Key | `eyJhbGciOi...` |
| `SUPABASE_STORAGE_BUCKET` | Default | `documents` |
| `CORS_ORIGINS` | Wildcard or Frontend URL | `*` |

6. Click **Apply**.
7. Render will build and deploy the backend first. Copy the public backend URL assigned by Render:
   - Example: `https://semantic-pyq-backend.onrender.com`

---

## 7. Step 5: Configure Frontend API Connection

1. In the Render Dashboard, click on your **`semantic-pyq-frontend`** Static Site.
2. Navigate to **Environment**.
3. Add / verify the environment variable:
   - **Key:** `VITE_API_URL`
   - **Value:** Your live Render backend URL (e.g., `https://semantic-pyq-backend.onrender.com` without a trailing slash).
4. Click **Save Changes** and click **Manual Deploy** -> **Deploy latest commit** to trigger a frontend build with the production API URL injected.
5. Once deployment completes, your public website URL will be live:
   - Example: `https://semantic-pyq-frontend.onrender.com`

---

## 8. Verifying the Deployment

### 1. Test Backend Health Check
Open in your browser:
```
https://YOUR-BACKEND.onrender.com/health
```
Expected output:
```json
{"status": "ok", "service": "Semantic PYQ Analyzer"}
```

### 2. Test Aggregated System Health
Open:
```
https://YOUR-BACKEND.onrender.com/api/health/system
```
Verify that `database.status` is `"ok"`, `pgvector` is `"ok"`, `embedding.status` is `"ok"`, and `ai.status` is `"ok"`.

### 3. Test Interactive Swagger API Documentation
Open:
```
https://YOUR-BACKEND.onrender.com/docs
```
You will see the complete interactive OpenAPI documentation.

---

## 9. End-to-End Feature Testing Checklist

Open your public frontend URL in an incognito browser window:

1. **Dashboard:**
   - Verify all stats load from the database without any crash.
2. **Subjects:**
   - Click **Add Subject** (e.g. `Operating Systems`, `CS204`).
   - Edit the subject description and verify updates reflect immediately.
3. **Notes Upload & Text Extraction:**
   - Select the subject and upload a sample note (`.pdf`, `.docx`, or `.txt`).
   - Verify status transitions from `Queued` -> `Processing` -> `Ready`.
   - Click the **Eye icon** to inspect generated chunks and embeddings.
   - Click the **Download icon** to verify the document can be retrieved and downloaded directly from cloud storage.
4. **PYQ Library:**
   - Add sample questions or import a CSV (columns: `question,exam_year,marks`).
   - Filter by year or marks.
5. **Study Heatmap:**
   - Click **Generate Heatmap** on the Heatmap page.
   - Verify priority categories (High Priority, Moderate Priority, Low Priority, Unmatched) populate using real database calculation.
6. **Semantic Search:**
   - Search for a concept (e.g., `"deadlock avoidance"` or `"B+ tree index"`).
   - Verify the top-k chunks are retrieved with cosine similarity match percentages.
7. **AI Study Assistant (RAG):**
   - Ask a question based on your uploaded notes.
   - Verify the response is structured, cited to the note chunks, and grounded in uploaded materials.
8. **Settings:**
   - Check the **System Status & Cloud Configuration** page.
   - All 4 cards (Database, Embedding, AI Assistant, Storage) should report green active statuses.

---

## 10. Troubleshooting Common Issues

### Issue 1: Backend takes 40-50 seconds to open on first visit
* **Cause:** Render free-tier web services sleep after 15 minutes of inactivity to conserve resources.
* **Resolution:** This is standard Render free-tier behavior. The first request wakes up the container within 30-50 seconds; all subsequent requests are instantaneous.

### Issue 2: Frontend shows "Cannot connect to backend server"
* **Check:** Did you set `VITE_API_URL` on the frontend static site in Render?
* **Resolution:** Set `VITE_API_URL` to `https://your-backend.onrender.com` (no trailing slash) and trigger a manual rebuild of the static site.

### Issue 3: pgvector extension not found
* **Resolution:** Open the **SQL Editor** in your Neon dashboard and execute:
  ```sql
  CREATE EXTENSION IF NOT EXISTS vector;
  ```

### Issue 4: AI Assistant shows "Gemini API key is not configured"
* **Resolution:** Add `GEMINI_API_KEY` in the Render Backend Web Service settings under **Environment Variables**. Restart the service.

---

## 11. Free-Tier Usage Tips

1. **Keep embeddings lightweight:** The project uses `EMBEDDING_PROVIDER=gemini` with `text-embedding-004` (384 dimensions) in production. This avoids PyTorch's 400MB RAM overhead, keeping backend memory at ~60MB (well below Render's 512MB limit).
2. **Neon Database:** The free tier includes 0.5 GB of storage, which is more than enough for thousands of questions and documents.
3. **Supabase Storage:** The free tier includes 1 GB of file storage.
4. **Gemini API:** The free tier offers 15 requests per minute, which is generous for personal projects and college evaluations.
