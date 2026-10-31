FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for build tools and PDF processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Attempt pre-download of Sentence Transformer model for local Docker use (non-blocking)
RUN python -c "try:\n    from sentence_transformers import SentenceTransformer\n    SentenceTransformer('all-MiniLM-L6-v2')\nexcept Exception as e:\n    print('Model pre-download skipped:', e)"

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
