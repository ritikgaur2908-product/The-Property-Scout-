# The Property Scout

> An AI-powered voice assistant that helps you find the perfect rental flat or room in Bengaluru — in a single conversation.

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-teal?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-blue?logo=react)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-green?logo=supabase)](https://supabase.com)
[![Qdrant](https://img.shields.io/badge/Vector_DB-Qdrant-red)](https://qdrant.tech)

---

## What It Does

1. **Voice-first search** — Speak your preferences (BHK, budget, locality, gender) and the AI extracts structured filters.
2. **Real listings** — Searches a live PostgreSQL database of scraped Bengaluru properties.
3. **Neighbourhood insights** — RAG pipeline pulls verified resident opinions from Qdrant, reranked by relevance.
4. **Amenity intelligence** — OpenStreetMap MCP server fetches live nearby amenities (metro, hospitals, gyms) within 1.5 km.
5. **One-tap booking** — Book a site visit by voice; confirmation sent via N8N → email.
6. **Shortlist email** — Email your shortlisted properties in a single command.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Frontend (React + Vite)                                                  │
│  ConversationPane  PropertyPane  BookingModal  VoiceControls              │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │ WebSocket /api/voice/stream
                             │ REST  /api/session  /api/bookings
                             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Backend (FastAPI + Uvicorn)                                              │
│  ┌───────────────┐  ┌─────────────────┐  ┌──────────────────────────┐   │
│  │ Rate Limiter  │  │  CORS Middleware │  │ Input Validation (Pydantic)│  │
│  └───────────────┘  └─────────────────┘  └──────────────────────────┘   │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  LLM Orchestrator (Groq)                                            │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │  │
│  │  │  STT          │ │ Tool Calling │ │  TTS          │               │  │
│  │  │  (Deepgram)   │ │ search_props │ │  (Edge-TTS)   │               │  │
│  │  └──────────────┘ │ book_visit   │ └──────────────┘               │  │
│  │                   │ get_rag_info │                                  │  │
│  │                   │ get_amenities│                                  │  │
│  │                   └──────────────┘                                  │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌──────────────┐  ┌─────────────┐  ┌───────────────┐  ┌─────────────┐  │
│  │  PostgreSQL  │  │  Qdrant     │  │  OSM MCP      │  │  N8N        │  │
│  │  (Supabase)  │  │  (Vector DB)│  │  (Amenities)  │  │  (Webhooks) │  │
│  └──────────────┘  └─────────────┘  └───────────────┘  └─────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
The Property Scout/
├── backend/
│   ├── api/
│   │   ├── app.py                      # FastAPI app, CORS, middleware wiring
│   │   ├── middleware/
│   │   │   ├── rate_limiter.py         # Per-IP + per-session sliding window
│   │   │   ├── validation.py           # Pydantic schemas for all request bodies
│   │   │   └── graceful_degradation.py # Timeout wrappers for external services
│   │   └── routes/
│   │       ├── session.py              # /api/session — chat + filter management
│   │       ├── bookings.py             # /api/bookings — CRUD
│   │       ├── properties.py           # /api/properties — search
│   │       └── notifications.py        # /api/notify — email shortlist
│   ├── booking/
│   │   └── service.py                  # Booking business logic
│   ├── db/
│   │   ├── models.py                   # SQLAlchemy ORM models
│   │   ├── queries.py                  # Property search with soft-filter fallback
│   │   └── connection.py               # Engine + session factory
│   ├── llm/
│   │   ├── orchestrator.py             # Main LLM loop, tool dispatch, retries
│   │   ├── tools.py                    # Tool definitions for Groq function-calling
│   │   ├── state_manager.py            # Conversation + preferences state
│   │   └── prompts.py                  # System prompt builder
│   ├── rag/
│   │   ├── retriever.py                # Qdrant + local chunk fallback
│   │   ├── reranker.py                 # Score-based reranker
│   │   └── synthesizer.py              # RAG context formatter for LLM + UI
│   ├── voice/
│   │   ├── streaming.py                # WebSocket handler (STT→LLM→TTS)
│   │   ├── stt.py                      # Deepgram speech-to-text
│   │   └── tts.py                      # Edge-TTS text-to-speech
│   ├── mcp/
│   │   ├── osm_client.py               # OpenStreetMap amenity fetcher
│   │   └── amenity_mapper.py           # Maps OSM tags → display categories
│   ├── notification/
│   │   ├── webhook.py                  # N8N webhook trigger
│   │   └── payloads.py                 # Booking + shortlist payload builders
│   ├── config.py                       # Pydantic Settings (reads .env)
│   └── requirements.txt
├── frontend/
│   ├── index.html                      # SEO meta + OG tags + JSON-LD
│   └── src/
│       ├── App.tsx
│       ├── index.css                   # Design tokens + animation system
│       ├── components/
│       │   ├── Header/
│       │   ├── LandingPage/
│       │   ├── ConversationPane/
│       │   ├── PropertyPane/           # Cards + filter bar + compare
│       │   ├── VoiceControls/
│       │   └── BookingModal/
│       ├── hooks/
│       │   ├── useConversation.ts      # WebSocket state + message handling
│       │   └── useVoiceActivityDetection.ts
│       └── api/
├── evals/
│   ├── run_evals.py                    # CLI eval runner
│   ├── golden_dataset.json             # 15 test cases
│   ├── conftest.py                     # Pytest fixtures (SQLite mock DB)
│   ├── modules/
│   │   ├── feasibility.py              # Budget + BHK + commute checks
│   │   ├── edit_correctness.py         # Multi-turn state preservation
│   │   └── grounding.py                # Hallucination + RAG grounding
│   ├── judges/
│   │   └── llm_judge.py                # Groq-based LLM judge
│   └── logs/
│       └── eval_log_v1.json            # Baseline evaluation results
├── rag_ingestion/
│   ├── scraper.py                      # Neighbourhood data scraper
│   ├── embedder.py                     # Gemini embedding wrapper
│   ├── ingestor.py                     # Qdrant upload pipeline
│   ├── chunks.json                     # Raw scraped chunks
│   └── embeddings.json                 # Embedded chunks (local fallback)
├── scraper/
│   └── scraper.py                      # Property listing scraper
├── Docs/
│   └── implementation_plan.md
├── .env                                # Environment variables (see below)
└── README.md
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- A `.env` file (see [Environment Variables](#environment-variables))

### 1. Clone & Install

```bash
git clone https://github.com/your-org/the-property-scout.git
cd "The Property Scout"

# Backend
pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install && cd ..
```

### 2. Configure Environment

Copy and fill in your credentials:

```bash
cp .env.example .env
```

See [Environment Variables](#environment-variables) for the full list.

### 3. Run the Backend

```bash
uvicorn backend.api.app:app --reload --port 8000
```

API docs available at: `http://localhost:8000/docs`

### 4. Run the Frontend

```bash
cd frontend
npm run dev
```

Opens at: `http://localhost:5173`

### 5. (Optional) Ingest RAG Data

```bash
python rag_ingestion/ingestor.py
```

---

## Environment Variables

All variables are loaded from `.env` in the project root via `backend/config.py`.

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | PostgreSQL connection string (e.g. Supabase URI) |
| `VECTOR_DB_URL` | ✅ | Qdrant Cloud cluster URL |
| `VECTOR_DB_API_KEY` | ✅ | Qdrant API key |
| `GROQ_API_KEY` | ✅ | Groq API key for LLM + eval judge |
| `LLM_MODEL` | ✅ | Groq model for orchestrator (e.g. `openai/gpt-oss-20b`) |
| `GEMINI_API_KEY` | ✅ | Google Gemini API key for embeddings |
| `DEEPGRAM_API_KEY` | ✅ | Deepgram API key for speech-to-text |
| `TTS_API_KEY` | ❌ | ElevenLabs API key (optional — falls back to Edge-TTS) |
| `N8N_WEBHOOK_BASE_URL` | ✅ | Base URL for N8N Cloud webhooks |
| `N8N_BOOKING_WEBHOOK_PATH` | ✅ | Path for booking confirmation webhook |
| `N8N_SHORTLIST_WEBHOOK_PATH` | ✅ | Path for shortlist email webhook |
| `SENDER_EMAIL` | ✅ | From address for outbound emails |
| `FRONTEND_URL` | ❌ | Production frontend URL for CORS (e.g. `https://thepropertyscout.in`). Defaults to `http://localhost:5173` |
| `OSM_MCP_ENDPOINT` | ❌ | OpenStreetMap MCP server endpoint (default: `http://localhost:8080`) |
| `DEBUG` | ❌ | Set to `true` to enable debug logging and skip WS auth. Default: `false` |
| `RATE_LIMIT_IP_MAX` | ❌ | Max requests per IP per window (default: 60) |
| `RATE_LIMIT_IP_WINDOW_S` | ❌ | IP rate limit window in seconds (default: 60) |
| `RATE_LIMIT_SES_MAX` | ❌ | Max requests per session per window (default: 30) |
| `RATE_LIMIT_SES_WINDOW_S` | ❌ | Session rate limit window in seconds (default: 60) |

---

## Running Evaluations

```bash
# Run all eval modules against the golden dataset
python evals/run_evals.py --verbose

# Run a specific module
python evals/run_evals.py --module feasibility
python evals/run_evals.py --module edit_correctness
python evals/run_evals.py --module grounding

# Save to a custom path
python evals/run_evals.py --output evals/logs/my_run.json

# Run as pytest
pytest evals/ -v
```

Reports are saved to `evals/logs/eval_log_<timestamp>.json`.

---

## WebSocket Protocol

Connect to `ws://localhost:8000/api/voice/stream?session_id=<uuid>&session_token=<uuid>`

> In production (`DEBUG=false`), the `session_token` query param (your session UUID from `POST /api/session`) is required. In development (`DEBUG=true`) it is optional.

### Sending

| Type | Payload | Description |
|---|---|---|
| JSON `{"type":"greeting"}` | — | Triggers initial bot greeting |
| JSON `{"type":"text","content":"..."}` | — | Send a text message |
| Binary (bytes) | Raw WAV audio | Streams audio for STT → LLM → TTS |

### Receiving

| Type | Description |
|---|---|
| `{"type":"user_text","content":"..."}` | STT transcript echo |
| `{"type":"text","content":"..."}` | Bot text response |
| `{"type":"shortlist","properties":[...],"preferences":{...}}` | Updated property shortlist |
| `{"type":"property_update","property_id":"...","amenities":[...],"neighborhoodInsights":"..."}` | Enriched property data (async) |
| Binary bytes | TTS audio stream |

---

## API Reference

Full interactive docs at `http://localhost:8000/docs` (Swagger UI) or `/redoc`.

### Key Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/session` | Create a new conversation session |
| `GET` | `/api/session/{id}` | Get session state |
| `POST` | `/api/session/{id}/message` | Send a text message |
| `POST` | `/api/session/{id}/remove-filter` | Remove a specific preference filter |
| `POST` | `/api/bookings` | Create a property visit booking |
| `GET` | `/api/bookings/{booking_id}` | Get booking details |
| `PATCH` | `/api/bookings/{booking_id}` | Reschedule a booking |
| `DELETE` | `/api/bookings/{booking_id}` | Cancel a booking |
| `POST` | `/api/notify/shortlist` | Email the shortlist to a user |
| `GET` | `/api/health` | Liveness probe |
| `WS` | `/api/voice/stream` | Voice + text WebSocket |

---

## Evaluation Results (Baseline — v1)

| Module | Pass | Fail | Skip |
|---|---|---|---|
| Feasibility | 15 | 0 | 0 |
| Edit Correctness | 6 | 0 | 9* |
| Grounding | 15 | 0 | 0 |

*9 cases correctly skipped (no prior state — not multi-turn edit scenarios).

LLM judge (RAG grounding score) requires `GROQ_API_KEY` to be set and produces scores 1–5 (≥4 required to pass).

---

## Contributing

1. Fork the repo and create a feature branch.
2. Follow the existing module structure — don't add top-level scripts.
3. Run evaluations before submitting a PR: `python evals/run_evals.py`
4. All eval modules must remain at 100% rule-based pass rate.

---

## License

MIT — see [LICENSE](LICENSE).
