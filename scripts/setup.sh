#!/usr/bin/env bash
# Quickstart setup script for Semantic PYQ Analyzer & Study Heatmap
set -e

echo "=========================================================="
echo "  Setting up Semantic PYQ Analyzer & Study Heatmap"
echo "=========================================================="

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed. Please install Python 3.10+."
    exit 1
fi

# 2. Check Node
if ! command -v npm &> /dev/null; then
    echo "Node.js and npm are required for frontend. Please install Node.js 18+."
    exit 1
fi

# 3. Setup Backend
echo "[1/4] Setting up Backend dependencies..."
cd backend
python3 -m pip install -r requirements.txt
cd ..

# 4. Setup Frontend
echo "[2/4] Setting up Frontend dependencies..."
cd frontend
npm install
npm run build
cd ..

# 5. Environment configuration
if [ ! -f .env ]; then
    echo "[3/4] Creating .env file from template..."
    cp .env.example .env
fi

echo "[4/4] Setup complete!"
echo ""
echo "To run backend:"
echo "  cd backend && uvicorn app.main:app --reload --port 8000"
echo ""
echo "To run frontend:"
echo "  cd frontend && npm run dev"
echo ""
echo "To seed sample data:"
echo "  python3 scripts/seed_sample_data.py"
echo "=========================================================="
