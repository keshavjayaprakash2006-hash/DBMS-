# System Architecture & Technical Specifications

## 1. Executive Overview

**Semantic PYQ Analyzer & Study Heatmap** is an offline-first, vector-database-driven academic analytics platform. It bridges the gap between raw syllabus notes and recurring Previous Year Questions (PYQs) using local dense vector embeddings, vector similarity matching, and interactive heatmaps.

```
┌────────────────────────────────────────────────────────────────────────┐
│                          PRESENTATION LAYER                            │
│           React 19 + TypeScript + Vite + Tailwind CSS (SPA)            │
│  - Dashboard  - Subjects  - Notes  - PYQs  - Heatmap  - Search  - Chat │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / JSON
┌───────────────────────────────────▼────────────────────────────────────┐
│                           API & SERVICE LAYER                          │
│                      FastAPI (Python 3.10+)                            │
│  - Document Extractor (PDF/DOCX/TXT)   - Chunking Engine (300w / 50ov) │
│  - Vector Embedding Service (all-MiniLM-L6-v2, 384-d dense vectors)    │
│  - Cosine Distance Matcher (<=>)       - Importance Scoring Engine     │
│  - RAG Context Retriever               - Local Ollama LLM Connector    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ SQL / pgvector
┌───────────────────────────────────▼────────────────────────────────────┐
│                           PERSISTENCE LAYER                            │
│                   PostgreSQL 16 + pgvector Extension                   │
│  - Relational Schema (Subjects, Documents, Chunks, PYQs, Scores)       │
│  - HNSW Vector Indexes (Cosine Distance `vector_cosine_ops`)           │
│  - B-Tree Relational Indexes (Foreign Keys, Year, Marks)               │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Subsystems

### 2.1 Document Extraction & Chunking Subsystem
- **Supported Formats**: `.pdf` (PyMuPDF / fitz), `.docx` (python-docx), `.txt` (UTF-8).
- **Chunking Strategy**: Paragraph-aware sliding window.
  - Chunk Target Size: 300 words.
  - Overlap: 50 words to preserve cross-boundary context.
  - Metadata Tracked: position index, character length, word count, document ID, subject ID.

### 2.2 Dense Vector Embedding Subsystem
- **Model**: `sentence-transformers/all-MiniLM-L6-v2`.
- **Dimensions**: 384-dimensional dense floating-point vector.
- **Offline Guarantee**: Model weights are downloaded and cached locally on first load (or bundled in Docker image). Zero external API calls are made for embedding generation.
- **Embedding Pipeline**: Asynchronous background workers vectorize note chunks and imported PYQ text without blocking the REST API.

### 2.3 Importance Scoring & Heatmap Generation Algorithm
The heatmap score measures how heavily a paragraph is tested across previous year exam papers:

1. **Cosine Similarity**: For each PYQ $q$, we find the top-$k$ nearest note chunks $c$ using the pgvector cosine distance operator:
   $$\text{Similarity}(c, q) = 1 - (\vec{c} \Leftrightarrow \vec{q})$$
   Matches with similarity $\ge 0.40$ are recorded as hits.

2. **Hit Count Aggregation**: Each chunk $c$ accumulates:
   $$\text{HitCount}(c) = |\{q \in \text{PYQs} \mid \text{Matched}(c, q)\}|$$
   $$\text{WeightedMarks}(c) = \sum_{q \in \text{Matched}(c)} \text{Marks}(q) \times \text{Similarity}(c, q)$$

3. **Normalized Importance Score**:
   $$\text{ImportanceScore}(c) = \frac{\text{HitCount}(c)}{\max_{k}(\text{HitCount}(k))}$$
   Yield classification:
   - **High Yield (Red)**: $\text{Score} \ge 0.70$
   - **Medium Yield (Amber)**: $0.40 \le \text{Score} < 0.70$
   - **Low Yield (Yellow)**: $0.10 \le \text{Score} < 0.40$
   - **Unmatched (Slate)**: $\text{Score} < 0.10$

### 2.4 Retrieval-Augmented Generation (RAG) & Chat Subsystem
- **Context Construction**: When a student asks a question, the query is vectorized and the top-5 note chunks and top-3 related PYQs are retrieved using pgvector.
- **Inference Runtime**: Queries local **Ollama** (`mistral` or `llama3`) running on `localhost:11434`.
- **Honest Graceful Fallback**: If Ollama is offline, the system clearly presents the retrieved source citations and diagnostic steps rather than crashing or faking an answer.

---

## 3. Technology Stack Rationale

| Layer | Chosen Technology | Architectural Justification |
| :--- | :--- | :--- |
| **Database** | PostgreSQL 16 + pgvector | Combines relational integrity (ACID, foreign keys) with native HNSW vector similarity search. Eliminates the need for separate standalone vector stores. |
| **Backend** | FastAPI + SQLAlchemy 2.0 | High-performance asynchronous REST API with automatic OpenAPI documentation and native Pydantic schema validation. |
| **Embeddings** | all-MiniLM-L6-v2 | 384-d dense embeddings with exceptional balance of semantic accuracy (MTEB leaderboard) and CPU inference speed (~15ms per paragraph). |
| **LLM Runtime** | Ollama | 100% offline, privacy-first local LLM inference without recurring API token costs. |
| **Frontend** | React 19 + TypeScript + Vite | Type-safe, blazing fast client-side rendering with Tailwind CSS modern aesthetic. |
| **Analytics** | Recharts | Composable SVG data visualizations for year trends, marks distribution, and yield rankings. |
