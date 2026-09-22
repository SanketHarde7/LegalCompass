# LegalCompass Backend API Service

High-performance, 100% free-tier AI backend service for **LegalCompass**.

## Features

- **FastAPI & Uvicorn:** Asynchronous REST API with OpenAPI interactive documentation (`/docs`).
- **Dynamic Model IDs & Multi-Provider Failover:** Configurable `GEMINI_MODEL_ID` and `GROQ_MODEL_ID` via `.env`. Implements automatic failover (tries Gemini first, falls back to Groq if rate-limited or key disabled).
- **Zero-API-Cost Vector Search (RAG):** Uses `fastembed` (BGE-small-en-v1.5) on local CPU with cosine similarity (`np.dot`).
- **Intelligent Clause Segmentation:** `pdfplumber` text extraction with regex-based legal heading detection and semantic windowing fallback.
- **Server-Sent Events (SSE) Streaming:** Real-time token streaming with interactive clause citations (`citation`) and structured counter-amendments (`suggestion`).
- **Attorney Brief PDF Export:** Generates print-ready legal memoranda via ReportLab.

---

## Getting Started

### 1. Prerequisites
- Python 3.10+ (Recommended: Python 3.11 or 3.13)

### 2. Environment Setup
Inside `legalcompass-backend/`:
```bash
# Create virtual environment
py -3.11 -m venv .venv
# or on Linux/macOS:
python3 -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Edit `.env` with your preferred API keys and model IDs:
```env
# Google Gemini (Primary)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL_ID=gemini-1.5-flash

# Groq Cloud (Automatic Failover)
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL_ID=llama-3.3-70b-versatile
```

> **Note:** Neither model ID is hardcoded in the codebase. You can swap to any supported model ID (e.g., `gemini-2.0-flash`, `gemini-1.5-pro`, `llama-3.1-8b-instant`) directly in `.env`.

### 4. Run the Server
```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at:
- **API Base:** `http://localhost:8000/api`
- **Interactive Swagger Docs:** `http://localhost:8000/docs`
- **Health Check:** `http://localhost:8000/health`

---

## API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Server health and configured AI provider status |
| `POST` | `/api/upload` | Upload PDF/DOCX contract, extract clauses, evaluate risks |
| `POST` | `/api/chat` | Conversational legal copilot with SSE token streaming |
| `POST` | `/api/simulate-scenario` | What-If outcome simulation against contract terms |
| `POST` | `/api/export-brief` | Generates 1-page attorney consultation brief in PDF format |
