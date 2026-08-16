# Value Chain AI Opportunity Intelligence

A persistent, multi-stage pipeline that analyzes any given industry's value chain to discover, score, and interrogate AI opportunities. Built to satisfy the MODUS Assignment 8 requirements.

## Features

- **Surprise Record Test:** Type *any* industry name. The system independently researches the industry, structures the value chain, and discovers AI opportunities.
- **Traceability:** Every AI claim is backed by a specific evidence snippet with a clickable source URL.
- **Formula-Driven Prioritization:** Opportunities are ranked via a strict mathematical formula, not LLM vibes.
- **Persistent Knowledge:** Data is stored in SQLite (relational) and ChromaDB (vector). Restarting the server does not lose knowledge.

## Architecture

1. **UI Layer:** React + Tailwind CSS (Vite)
2. **API/Backend:** FastAPI (Python) orchestrating the workflow async.
3. **AI Intelligence Layer:** Groq (Llama 3.1 8B for cheap structuring, Llama 3.3 70B for synthesis).
4. **Data & Knowledge Layer:** SQLite for structured data (schema in `backend/models.py`), ChromaDB for vector evidence retrieval. Embedded `sentence-transformers` for local embeddings.
5. **External Research:** Tavily API (free tier) for agentic web search.

### Fallback Logic (Service Unavailability)
- **Web Search (Tavily):** If the Tavily API fails or runs out of credits, the system catches the exception and falls back to a simulated mock-research block (or could be easily swapped to DuckDuckGo/Serper with a 1-line change).
- **LLM Inference (Groq):** If Groq is unavailable, the system safely catches the error and logs it. The architecture wraps the LLM calls in independent functions, making it trivial to swap the `groq_client` with an `OpenAI` client or a local `Ollama` instance without changing the core logic.

## Setup Instructions

### 1. Backend

```bash
cd backend
python -m venv venv
# Activate virtual env:
# Windows: .\venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

pip install -r requirements.txt # (Or manually pip install fastapi uvicorn sqlalchemy pydantic groq tavily-python chromadb sentence-transformers python-dotenv)

# Set API Keys
# Create a .env file in the backend directory:
# GROQ_API_KEY=your_key
# TAVILY_API_KEY=your_key

# Run the backend
uvicorn main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Navigate to the provided localhost URL (typically `http://localhost:5173`).

## Model & Library Inventory

- **LLM Inference:** Groq API (Llama-3.1-8b-instant, Llama-3.3-70b-versatile) - Commercial/Open-Weights
- **Web Research:** Tavily API - Commercial Free Tier
- **Embeddings:** `sentence-transformers` (`all-MiniLM-L6-v2`) - Apache 2.0
- **Vector DB:** ChromaDB (Local Embedded) - Apache 2.0
- **Relational DB:** SQLite - Public Domain
- **Backend Framework:** FastAPI - MIT
- **Frontend Framework:** React (Vite) - MIT
- **Styling:** Tailwind CSS - MIT

## Research Sources
The system utilizes the Tavily Search API, which aggregates data from a wide variety of public web sources including:
- Industry reports (McKinsey, Gartner, etc.)
- News articles
- B2B case studies
- General encyclopedic knowledge (Wikipedia)

## Disclosure
This project was implemented with the assistance of an AI coding agent (Antigravity), following strict architectural constraints and build guides provided by the user. The core 5-step pipeline logic, database schemas, and mathematical prioritization models were designed manually via the provided specification.
