# Complete Installation & Deployment Guide

This guide covers running the **Semantic PYQ Analyzer & Study Heatmap** using either **Docker Compose** (recommended, zero-configuration) or **Local Native Setup** (Windows, Linux, macOS).

---

## Method 1: Docker Compose (Recommended)

Docker Compose starts PostgreSQL with pgvector, compiles the frontend, and runs the backend in isolated containers.

### Prerequisites
- Docker Engine 24+ & Docker Compose v2.

### Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/keshavjayaprakash2006-hash/DBMS-.git
   cd DBMS-
   ```

2. Start all services:
   ```bash
   docker compose up -d --build
   ```

3. Populate sample data:
   ```bash
   python scripts/seed_sample_data.py
   ```

4. Open your browser:
   - **Web UI**: `http://localhost:3000`
   - **Backend API & Swagger Docs**: `http://localhost:8000/docs`

---

## Method 2: Local Native Setup

### Prerequisites
- **Python**: 3.10, 3.11, 3.12, or 3.13
- **Node.js**: 18+ and `npm`
- **PostgreSQL**: 15+ with the `pgvector` extension

### 1. Database Setup (PostgreSQL with pgvector)

#### Windows
1. Download and install PostgreSQL from [EnterpriseDB](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads).
2. Install `pgvector` for Windows:
   - Download the precompiled binary from [pgvector releases](https://github.com/pgvector/pgvector/releases).
   - Copy `vector.dll` into PostgreSQL's `lib` directory (e.g. `C:\Program Files\PostgreSQL\16\lib\`).
   - Copy `vector.control` and `vector--*.sql` into PostgreSQL's `share/extension` directory.
3. Open `psql` or pgAdmin and run:
   ```sql
   CREATE DATABASE pyq_analyzer;
   \c pyq_analyzer;
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

#### macOS (Homebrew)
```bash
brew install postgresql@16
brew install pgvector
brew services start postgresql@16
psql -d postgres -c "CREATE DATABASE pyq_analyzer;"
psql -d pyq_analyzer -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

#### Ubuntu / Debian
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib postgresql-server-dev-all
git clone --branch v0.6.0 https://github.com/pgvector/pgvector.git
cd pgvector && make && sudo make install
sudo -u postgres psql -c "CREATE DATABASE pyq_analyzer;"
sudo -u postgres psql -d pyq_analyzer -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

---

### 2. Backend Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   Ensure `DATABASE_URL` matches your local credentials:
   ```env
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/pyq_analyzer
   EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2
   EMBEDDING_DIMENSION=384
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=mistral
   ```

2. Install Python dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. Run database migrations:
   ```bash
   alembic upgrade head
   ```

4. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

---

### 3. Frontend Setup

1. Open a new terminal and navigate to `frontend`:
   ```bash
   cd frontend
   npm install
   ```

2. Start the Vite development server:
   ```bash
   npm run dev
   ```
   Open `http://localhost:5173` in your browser.

---

### 4. Optional: Local Ollama LLM Setup (For AI Assistant)

1. Download Ollama from [ollama.ai](https://ollama.ai).
2. Pull your preferred language model:
   ```bash
   ollama pull mistral
   ```
3. Start the Ollama server:
   ```bash
   ollama serve
   ```
   *Note: If Ollama is not running, the application continues to operate fully—notes, chunking, vector search, and heatmaps work 100% offline. The AI Assistant displays clear offline status instructions.*

---

### 5. Seeding Sample Data

Populate Operating Systems and Database Management Systems lecture notes and previous year questions:
```bash
python scripts/seed_sample_data.py
```
