# The Property Scout — System Architecture

> **Derived from:** [context.md](file:///c:/Users/Ritk%20Gaur/Desktop/The%20Property%20Scout/Docs/context.md)
> **Last Updated:** 2026-08-14

---

## Table of Contents

1. [High-Level System Topology](#1-high-level-system-topology)
2. [Service Decomposition](#2-service-decomposition)
3. [Data Models & Schema Design](#3-data-models--schema-design)
4. [API Layer & Route Contracts](#4-api-layer--route-contracts)
5. [Data Ingestion Pipeline](#5-data-ingestion-pipeline)
6. [Amenity Enrichment via OpenStreetMap MCP](#6-amenity-enrichment-via-openstreetmap-mcp)
7. [RAG Pipeline — Neighborhood Guidance](#7-rag-pipeline--neighborhood-guidance)
8. [Voice Processing Architecture](#8-voice-processing-architecture)
9. [Conversation State Machine](#9-conversation-state-machine)
10. [Booking System & Concurrency Control](#10-booking-system--concurrency-control)
11. [Notification System (N8N)](#11-notification-system-n8n)
12. [Frontend Architecture & UI Layout](#12-frontend-architecture--ui-layout)
13. [Evaluation Harness](#13-evaluation-harness)
14. [Deployment Architecture](#14-deployment-architecture)
15. [Security & Privacy](#15-security--privacy)
16. [Proposed Directory Structure](#16-proposed-directory-structure)

---

## 1. High-Level System Topology

```mermaid
graph TB
    subgraph "Client Layer"
        UI["Web Frontend<br/>(Vercel / Netlify)"]
    end

    subgraph "API Gateway"
        API["Backend API Server<br/>(Render / Railway / Docker)"]
    end

    subgraph "Core Services"
        VOICE["Voice Processing<br/>Service"]
        LLM["LLM Orchestrator<br/>(Conversation + Reasoning)"]
        RAG["RAG Retrieval<br/>Service"]
        BOOKING["Booking<br/>Service"]
        NOTIF["Notification<br/>Trigger"]
    end

    subgraph "Data Stores"
        PG["Relational DB<br/>(Properties + Bookings)"]
        VDB["Vector DB<br/>(Neighborhood Chunks)"]
    end

    subgraph "External Integrations"
        OSM["OpenStreetMap MCP<br/>(Amenities)"]
        N8N["N8N Workflow<br/>(Email Dispatch)"]
        SCRAPER["GitHub Actions<br/>(Daily Scraper)"]
        BRENT["bengaluru.rent"]
    end

    UI <-->|WebSocket / REST| API
    API --> VOICE
    API --> LLM
    API --> BOOKING
    API --> NOTIF

    LLM <--> RAG
    LLM <--> PG
    LLM <--> OSM
    RAG <--> VDB

    BOOKING <--> PG
    NOTIF -->|Webhook| N8N
    SCRAPER -->|Cron: Daily| BRENT
    SCRAPER -->|Upsert| PG
```

### Data Flow Summary

```
User speaks → Voice Service (STT) → LLM Orchestrator
  ├─ Queries Relational DB (property search)
  ├─ Calls OpenStreetMap MCP (amenity enrichment)
  ├─ Queries Vector DB via RAG (neighborhood guidance)
  └─ Generates grounded response → Voice Service (TTS) → User hears
                                  → API → Frontend (property cards)
```

---

## 2. Service Decomposition

The backend follows a **modular monolith** pattern with clear domain boundaries. Each module can be extracted into a microservice later if needed.

| Module | Responsibility | Dependencies |
|---|---|---|
| **`voice/`** | Speech-to-Text (STT), Text-to-Speech (TTS), audio streaming | External STT/TTS API |
| **`llm/`** | LLM orchestration, prompt construction, tool calling, state management | RAG module, DB module, MCP module |
| **`rag/`** | Vector DB queries, chunk retrieval, relevance scoring | Vector DB |
| **`mcp/`** | OpenStreetMap MCP tool invocation, amenity geocoding | OSM MCP server |
| **`scraper/`** | bengaluru.rent crawling, HTML parsing, PII scrubbing, data normalization | GitHub Actions (runner) |
| **`booking/`** | Visit CRUD, concurrency locking, unique ID generation | Relational DB |
| **`notification/`** | N8N webhook trigger, email payload construction | N8N workflow |
| **`db/`** | ORM models, migrations, connection pooling, query builders | Relational DB |
| **`api/`** | Route handlers, request validation, response serialization | All modules |
| **`evals/`** | Golden dataset runner, rule-based + LLM-as-Judge evaluations | LLM API, mock DB |

---

## 3. Data Models & Schema Design

### 3.1 Properties Table

```sql
CREATE TABLE properties (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id       VARCHAR(255) UNIQUE NOT NULL,     -- ID from bengaluru.rent
    accommodation_type  VARCHAR(50) NOT NULL,          -- 'whole_flat' | 'room_in_flat'
    rent            INTEGER NOT NULL,                  -- Monthly rent in INR
    rooms           INTEGER NOT NULL,                  -- Number of rooms / BHK
    move_in_time    VARCHAR(100),                      -- e.g. "Immediately", "1st Sept"
    gender_openness VARCHAR(50),                       -- 'male' | 'female' | 'any'
    parking_available   BOOLEAN DEFAULT FALSE,
    parking_count       INTEGER DEFAULT 0,
    flatmate_food_pref  VARCHAR(50),                   -- 'veg' | 'non_veg' | 'any' (nullable)
    flatmate_smoking_pref VARCHAR(50),                 -- 'smoker' | 'non_smoker' | 'any' (nullable)
    address         TEXT NOT NULL,
    locality        VARCHAR(255),                      -- Extracted neighborhood name
    latitude        DECIMAL(10, 8),
    longitude       DECIMAL(11, 8),
    source_url      TEXT,
    status          VARCHAR(20) DEFAULT 'available',   -- 'available' | 'unavailable'
    scraped_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_properties_locality ON properties(locality);
CREATE INDEX idx_properties_rent ON properties(rent);
CREATE INDEX idx_properties_rooms ON properties(rooms);
CREATE INDEX idx_properties_status ON properties(status);
```

### 3.2 Amenities Table

```sql
CREATE TABLE amenities (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id     UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    category        VARCHAR(100) NOT NULL,             -- 'daily_essentials' | 'health_education' | 'transport' | 'recreation'
    name            VARCHAR(255) NOT NULL,
    type            VARCHAR(100),                      -- e.g. 'pharmacy', 'metro_station', 'gym'
    distance_meters INTEGER,
    latitude        DECIMAL(10, 8),
    longitude       DECIMAL(11, 8),
    fetched_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_amenities_property ON amenities(property_id);
CREATE INDEX idx_amenities_category ON amenities(category);
```

### 3.3 Bookings Table

```sql
CREATE TABLE bookings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id      VARCHAR(20) UNIQUE NOT NULL,       -- Human-readable unique ID (e.g. "BK-A3F7X2")
    user_id         VARCHAR(20) NOT NULL,              -- Generated unique user ID
    property_id     UUID NOT NULL REFERENCES properties(id),
    user_email      VARCHAR(255) NOT NULL,
    visit_date      DATE NOT NULL,
    visit_time      TIME NOT NULL,
    status          VARCHAR(20) DEFAULT 'confirmed',   -- 'confirmed' | 'rescheduled' | 'cancelled'
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Prevent double-booking: one property, one date+time slot
    CONSTRAINT unique_property_slot UNIQUE (property_id, visit_date, visit_time)
);

CREATE INDEX idx_bookings_user ON bookings(user_id);
CREATE INDEX idx_bookings_property ON bookings(property_id);
CREATE INDEX idx_bookings_status ON bookings(status);
```

### 3.4 Conversation Sessions Table

```sql
CREATE TABLE sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         VARCHAR(20),                       -- Linked after first booking
    preferences     JSONB DEFAULT '{}',                -- Current filter/preference state
    shortlist       JSONB DEFAULT '[]',                -- Current shortlisted property IDs
    transcript      JSONB DEFAULT '[]',                -- Conversation history
    status          VARCHAR(20) DEFAULT 'active',      -- 'active' | 'completed'
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### 3.5 Vector DB Schema (Neighborhood Chunks)

Each document stored in the Vector DB follows this structure:

```json
{
  "chunk_id": "uuid",
  "locality": "Indiranagar",
  "theme": "safety_security | daily_life | transport | culture",
  "content": "Indiranagar's 100 Feet Road is well-lit and safe for walking until 11 PM...",
  "source_url": "https://reddit.com/r/bangalore/...",
  "source_type": "reddit | blog | news",
  "scraped_at": "2026-08-01T00:00:00Z",
  "embedding": [0.012, -0.034, ...]
}
```

---

## 4. API Layer & Route Contracts

### 4.1 Conversation Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/session` | Create a new conversation session |
| `GET` | `/api/session/:id` | Retrieve session state (preferences, shortlist, transcript) |
| `POST` | `/api/session/:id/message` | Send a user message (text or transcribed voice) |
| `WS` | `/api/session/:id/stream` | WebSocket for real-time voice streaming + bot responses |

### 4.2 Property Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/properties` | Search properties with query params (locality, rent range, BHK, etc.) |
| `GET` | `/api/properties/:id` | Get full property details with amenities |
| `GET` | `/api/properties/:id/amenities` | Get amenities for a specific property |
| `GET` | `/api/properties/:id/neighborhood` | Get RAG-sourced neighborhood guidance |

### 4.3 Booking Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/bookings` | Create a new booking (returns booking_id + user_id) |
| `GET` | `/api/bookings/:booking_id` | Get booking details |
| `PATCH` | `/api/bookings/:booking_id` | Reschedule a booking (update date/time) |
| `DELETE` | `/api/bookings/:booking_id` | Cancel a booking |

### 4.4 Notification Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/notify/shortlist` | Email the current shortlist to the user |

### 4.5 Request/Response Examples

#### POST `/api/session/:id/message`

**Request:**
```json
{
  "type": "text",
  "content": "I'm looking for a 2BHK in Indiranagar under 35k",
  "audio_base64": null
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "bot_response": {
    "text": "I found 4 listings in Indiranagar within your budget...",
    "audio_url": "/api/audio/response-uuid.mp3"
  },
  "updated_preferences": {
    "locality": "Indiranagar",
    "max_budget": 35000,
    "bhk": 2,
    "amenities": []
  },
  "shortlist": [
    {
      "property_id": "uuid",
      "rent": 28000,
      "rooms": 2,
      "accommodation_type": "whole_flat",
      "address": "...",
      "reasoning": "This property is within your 35k budget at ₹28,000/month...",
      "amenities": { ... },
      "neighborhood": { ... },
      "sources": [
        { "claim": "Area is well-connected to metro", "source_url": "https://..." }
      ]
    }
  ]
}
```

---

## 5. Data Ingestion Pipeline

### 5.1 Architecture

```mermaid
flowchart LR
    subgraph "GitHub Actions (Daily Cron)"
        TRIGGER["Cron Trigger<br/>06:00 IST Daily"]
        SCRAPE["Scraper Script<br/>(Python)"]
        PARSE["HTML Parser<br/>+ Data Extractor"]
        SCRUB["PII Scrubber"]
        NORM["Data Normalizer"]
    end

    subgraph "Database"
        UPSERT["Upsert Logic<br/>(Insert / Update / Deactivate)"]
        DB[(Relational DB)]
    end

    BRENT["bengaluru.rent"]

    TRIGGER --> SCRAPE
    SCRAPE -->|HTTP GET| BRENT
    BRENT -->|HTML| PARSE
    PARSE --> SCRUB
    SCRUB --> NORM
    NORM --> UPSERT
    UPSERT --> DB
```

### 5.2 Scraper Logic

1. **Fetch** all listing pages from bengaluru.rent.
2. **Filter** — exclude any listings marked *"Not for rent"* or flagged for transparency.
3. **Extract** all required fields (see §3.1 schema).
4. **Scrub PII** — remove owner/agent names, phone numbers, email addresses using regex + NER.
5. **Normalize** — standardize field values (e.g. "2 BHK" → `rooms: 2`, rent strings → integers).
6. **Geocode** — extract latitude/longitude from address for amenity lookup.
7. **Upsert** — insert new listings, update changed fields, mark removed listings as `status = 'unavailable'`.

### 5.3 GitHub Actions Workflow

```yaml
# .github/workflows/daily-scraper.yml
name: Daily Property Scraper

on:
  schedule:
    - cron: '30 0 * * *'   # 06:00 IST (00:30 UTC)
  workflow_dispatch:         # Manual trigger

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r scraper/requirements.txt
      - run: python scraper/main.py
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

---

## 6. Amenity Enrichment via OpenStreetMap MCP

### 6.1 Architecture

```mermaid
flowchart LR
    PROP["Property<br/>(lat, lng)"] --> MCP["OpenStreetMap<br/>MCP Server"]
    MCP -->|Overpass API| OSM["OpenStreetMap<br/>Data"]
    OSM -->|JSON| ENRICH["Amenity<br/>Enrichment"]
    ENRICH -->|Categorized| DB[(Amenities Table)]
```

### 6.2 Enrichment Strategy

Amenity enrichment happens **on-demand** when a property is first shortlisted (with results cached in the amenities table).

| Step | Detail |
|---|---|
| **1. Geocode** | Use property's latitude/longitude from the properties table |
| **2. Query MCP** | Call OSM MCP with the coordinates and a configurable radius (default: 2 km) |
| **3. Categorize** | Map OSM tags to the 4 amenity categories (Daily Essentials, Health & Education, Transport, Recreation) |
| **4. Compute distances** | Calculate straight-line distance from property to each amenity |
| **5. Store** | Insert into amenities table linked by `property_id` |
| **6. Cache TTL** | Re-fetch only if `fetched_at` is older than 7 days |

### 6.3 Category → OSM Tag Mapping

```json
{
  "daily_essentials": [
    "shop=supermarket", "shop=convenience", "shop=grocery",
    "amenity=pharmacy", "amenity=restaurant", "amenity=cafe",
    "amenity=fast_food", "shop=marketplace"
  ],
  "health_education": [
    "amenity=hospital", "amenity=clinic", "amenity=doctors",
    "amenity=school", "amenity=kindergarten", "amenity=college",
    "amenity=university"
  ],
  "transport": [
    "railway=station", "highway=bus_stop", "amenity=bus_station",
    "amenity=taxi", "amenity=charging_station", "amenity=fuel"
  ],
  "recreation": [
    "leisure=park", "leisure=garden", "leisure=playground",
    "leisure=sports_centre", "leisure=fitness_centre",
    "amenity=bank", "amenity=atm", "amenity=post_office"
  ]
}
```

---

## 7. RAG Pipeline — Neighborhood Guidance

### 7.1 Architecture

```mermaid
flowchart TB
    subgraph "Ingestion (Monthly)"
        SOURCES["Public Sources<br/>(Reddit, Blogs, News)"]
        CRAWL["Web Crawler"]
        CHUNK["Text Chunker<br/>(~500 tokens / chunk)"]
        EMBED["Embedding Model"]
        STORE["Vector DB Upsert"]
    end

    subgraph "Retrieval (Real-Time)"
        QUERY["User Query +<br/>Property Locality"]
        SEARCH["Semantic Search<br/>(Top-K Chunks)"]
        RERANK["Relevance Reranker"]
        LLM["LLM Synthesis<br/>(Cited Response)"]
    end

    SOURCES --> CRAWL --> CHUNK --> EMBED --> STORE
    STORE -.-> VDB[(Vector DB)]
    QUERY --> SEARCH
    VDB -.-> SEARCH
    SEARCH --> RERANK --> LLM
```

### 7.2 Ingestion Pipeline

1. **Crawl** — Scrape public sources (Reddit threads about Bengaluru neighborhoods, blogs like blrexplorer, local news). Run once initially, then **monthly updates**.
2. **Clean** — Remove HTML, ads, navigation elements. Keep substantive text.
3. **Chunk** — Split into ~500-token chunks with 50-token overlap. Tag each chunk with:
   - `locality` (neighborhood name)
   - `theme` (safety, daily life, transport, culture)
   - `source_url` and `source_type`
4. **Embed** — Generate vector embeddings locally using **BGE-large** (`BAAI/bge-large-en-v1.5`, 1024 dimensions) via the `sentence-transformers` Python library. Free, open-source, no API key required.
5. **Upsert** — Store in Vector DB with deduplication by `source_url + chunk_offset`.

### 7.3 Retrieval Pipeline

1. **Query Construction** — Combine the property's locality with the user's question context (e.g. "Is Indiranagar safe at night?").
2. **Semantic Search** — Retrieve top-K (K=10) chunks from Vector DB filtered by `locality`.
3. **Rerank** — Score chunks by relevance and recency, select top 5.
4. **LLM Synthesis** — Feed chunks to LLM with instructions to:
   - Only use information present in the chunks.
   - Cite the source URL for each claim.
   - Explicitly say "I don't have information on this" if no relevant chunk exists.

### 7.4 Source Citation Format

```json
{
  "claim": "Indiranagar has a metro station on the Purple Line with direct connectivity to MG Road.",
  "source_url": "https://reddit.com/r/bangalore/comments/abc123",
  "source_type": "reddit",
  "confidence": "high"
}
```

---

## 8. Voice Processing Architecture

### 8.1 Audio Pipeline

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant STT as STT Service
    participant LLM as LLM Orchestrator
    participant TTS as TTS Service

    User->>Frontend: Speaks (microphone)
    Frontend->>API: Audio stream (WebSocket)
    API->>STT: Audio chunks
    STT-->>API: Transcribed text
    API->>LLM: User message + session state
    LLM-->>API: Bot response text + updated state
    API->>TTS: Response text
    TTS-->>API: Audio stream
    API-->>Frontend: Audio + text + UI updates
    Frontend-->>User: Plays audio + renders cards
```

### 8.2 Component Responsibilities

| Component | Technology Options | Role |
|---|---|---|
| **STT (Speech-to-Text)** | Whisper API, Deepgram, Google Cloud STT | Convert user's speech to text in real-time |
| **TTS (Text-to-Speech)** | ElevenLabs, Google Cloud TTS, OpenAI TTS | Convert bot's text response to natural speech |
| **Audio Streaming** | WebSocket | Bidirectional real-time audio between frontend and backend |
| **VAD (Voice Activity Detection)** | Client-side VAD | Detect when user starts/stops speaking for turn management |

### 8.3 Latency Budget

| Stage | Target | Notes |
|---|---|---|
| Audio capture → STT result | < 500ms | Streaming transcription |
| STT result → LLM response | < 2s | Includes DB + RAG queries |
| LLM response → TTS audio start | < 300ms | Streaming TTS |
| **Total end-to-end** | **< 3s** | User-perceived response time |

---

## 9. Conversation State Machine

### 9.1 States & Transitions

```mermaid
stateDiagram-v2
    [*] --> Greeting: Session created
    Greeting --> PreferenceCollection: Bot greets user
    PreferenceCollection --> SearchExecution: Sufficient preferences collected
    SearchExecution --> ShortlistPresentation: Results enriched & ready
    ShortlistPresentation --> ShortlistRefinement: User asks to filter
    ShortlistRefinement --> ShortlistPresentation: Updated results
    ShortlistPresentation --> BookingFlow: User wants to book visit
    ShortlistPresentation --> EmailFlow: User wants to mail shortlist
    BookingFlow --> BookingConfirmed: Booking successful
    BookingConfirmed --> ShortlistPresentation: Continue browsing
    BookingConfirmed --> [*]: User ends session
    EmailFlow --> ShortlistPresentation: Email sent
    ShortlistPresentation --> [*]: User ends session

    note right of PreferenceCollection
        Collects: locality, budget,
        BHK, amenities, move-in date,
        gender, parking, food/smoking pref
    end note

    note right of ShortlistRefinement
        Only affected listings change.
        Unrelated state preserved.
    end note
```

### 9.2 Preference State Object

```typescript
interface UserPreferences {
  locality?: string;
  max_budget?: number;
  min_budget?: number;
  bhk?: number;
  accommodation_type?: 'whole_flat' | 'room_in_flat';
  gender?: 'male' | 'female' | 'any';
  move_in_time?: string;
  parking_required?: boolean;
  food_preference?: 'veg' | 'non_veg' | 'any';
  smoking_preference?: 'smoker' | 'non_smoker' | 'any';
  custom_filters?: string[];        // e.g. ["pet-friendly", "balcony"]
  max_commute_minutes?: number;
  commute_destination?: string;     // e.g. "Koramangala"
}
```

### 9.3 State Update Rules (Critical)

When the user makes a conversational edit:

1. **Parse** the user's utterance to identify which keys are being modified.
2. **Apply** changes to ONLY the targeted keys.
3. **Preserve** ALL un-targeted keys exactly as they were — no nulling, no resetting, no dropping.
4. **Re-query** the database with the updated preference set.
5. **Diff** the new results against the previous shortlist — only modify affected entries.

---

## 10. Booking System & Concurrency Control

### 10.1 Booking Flow

```mermaid
sequenceDiagram
    participant User
    participant API
    participant DB
    participant N8N

    User->>API: Book visit (property_id, date, time, email)
    API->>DB: BEGIN TRANSACTION
    API->>DB: SELECT ... FOR UPDATE (check slot availability)
    
    alt Slot Available
        API->>DB: INSERT booking (generate booking_id + user_id)
        API->>DB: COMMIT
        API->>N8N: Trigger booking_created webhook
        N8N-->>User: Confirmation email
        API-->>User: { booking_id, user_id, status: "confirmed" }
    else Slot Taken
        API->>DB: ROLLBACK
        API-->>User: { error: "Slot unavailable", alternatives: [...] }
    end
```

### 10.2 Concurrency Strategy

| Mechanism | Implementation |
|---|---|
| **Row-level locking** | `SELECT ... FOR UPDATE` on the property+slot combination within a transaction |
| **Unique constraint** | `UNIQUE (property_id, visit_date, visit_time)` prevents duplicate inserts at the DB level |
| **Optimistic retry** | If lock fails, suggest alternative time slots to the user |

### 10.3 ID Generation

| ID | Format | Example | Purpose |
|---|---|---|---|
| **Booking ID** | `BK-` + 6 alphanumeric chars | `BK-A3F7X2` | Human-readable booking reference |
| **User ID** | `USR-` + 6 alphanumeric chars | `USR-K9M2P1` | Assigned at first booking, reused for all subsequent operations |

---

## 11. Notification System (N8N)

### 11.1 Webhook Architecture

```mermaid
flowchart LR
    subgraph "Backend"
        BOOK["Booking Service"]
        SHORT["Shortlist Service"]
    end

    subgraph "N8N"
        HOOK["Webhook Receiver"]
        ROUTER["Event Router"]
        TPL["Email Template<br/>Engine"]
        SEND["SMTP Sender"]
    end

    BOOK -->|POST /webhook/booking| HOOK
    SHORT -->|POST /webhook/shortlist| HOOK
    HOOK --> ROUTER
    ROUTER --> TPL
    TPL --> SEND
    SEND -->|Email| USER["User Inbox"]
```

### 11.2 Webhook Payloads

#### Booking Created / Rescheduled / Cancelled

```json
{
  "event": "booking_created",
  "booking_id": "BK-A3F7X2",
  "user_email": "user@example.com",
  "property": {
    "address": "3rd Cross, Indiranagar",
    "rent": 28000,
    "rooms": 2
  },
  "visit_date": "2026-08-20",
  "visit_time": "10:00",
  "previous_date": null,
  "previous_time": null
}
```

#### Shortlist Mailed

```json
{
  "event": "shortlist_mailed",
  "user_email": "user@example.com",
  "shortlist": [
    {
      "property_id": "uuid",
      "address": "...",
      "rent": 28000,
      "rooms": 2,
      "amenities_summary": "Metro 500m, Hospital 1.2km, Park 300m",
      "neighborhood_summary": "...",
      "reasoning": "..."
    }
  ]
}
```

### 11.3 Email Templates

| Event | Subject Line Pattern | Content |
|---|---|---|
| **Booking Created** | `✅ Visit Confirmed — BK-A3F7X2` | Property details, date/time, booking ID, user ID for future reference |
| **Booking Rescheduled** | `🔄 Visit Rescheduled — BK-A3F7X2` | Old vs. new date/time, property details |
| **Booking Cancelled** | `❌ Visit Cancelled — BK-A3F7X2` | Cancellation confirmation, property details |
| **Shortlist Mailed** | `🏠 Your Property Shortlist — The Property Scout` | Full enriched property cards with amenities, neighborhood data, and sources |

---

## 12. Frontend Architecture & UI Layout

### 12.1 Layout States

#### State 1: Initial Conversation (Full-Width)

```
┌──────────────────────────────────────────────────────┐
│                    HEADER / BRANDING                  │
├──────────────────────────────────────────────────────┤
│                                                      │
│              🎤  Voice Bot Interface                  │
│              (Full-width, centered)                   │
│                                                      │
│         Greeting + Preference Collection              │
│                                                      │
│              [ Transcript Area ]                      │
│                                                      │
├──────────────────────────────────────────────────────┤
│          🎙️ Mic Button  |  💬 Text Input              │
└──────────────────────────────────────────────────────┘
```

#### State 2: Post-Shortlist (Split Pane)

```
┌──────────────────────────────────────────────────────┐
│                    HEADER / BRANDING                  │
├─────────────────────┬────────────────────────────────┤
│                     │                                │
│  🎤 Voice Bot       │  🏠 Property Cards             │
│  (Left Pane)        │  (Right Pane)                  │
│                     │                                │
│  [Transcript]       │  [Filters Bar]                 │
│                     │  ┌─────────────────────────┐   │
│                     │  │ Property Card 1          │   │
│                     │  │  Rent · Rooms · Address  │   │
│                     │  │  Amenities · Sources     │   │
│                     │  │  [📧 Mail] [📅 Book]     │   │
│                     │  └─────────────────────────┘   │
│                     │  ┌─────────────────────────┐   │
│                     │  │ Property Card 2          │   │
│                     │  └─────────────────────────┘   │
│                     │                                │
├─────────────────────┴────────────────────────────────┤
│          🎙️ Mic Button  |  💬 Text Input              │
└──────────────────────────────────────────────────────┘
```

### 12.2 Component Hierarchy

```
App
├── Header
├── ConversationPane
│   ├── TranscriptList
│   │   └── MessageBubble (user / bot)
│   ├── VoiceControls
│   │   ├── MicButton
│   │   └── AudioVisualizer
│   └── TextInput
├── PropertyPane (shown after shortlist generated)
│   ├── FilterBar
│   │   ├── BudgetFilter
│   │   ├── BHKFilter
│   │   ├── LocalityFilter
│   │   └── CustomFilterChips
│   ├── PropertyCardList
│   │   └── PropertyCard
│   │       ├── PropertyDetails
│   │       ├── AmenityGrid
│   │       ├── NeighborhoodInsights
│   │       ├── SourcesCitation
│   │       └── ActionButtons (Mail / Book Visit)
│   └── ShortlistActions
│       └── MailAllButton
└── BookingModal
    ├── DateTimePicker
    ├── EmailInput
    └── ConfirmationView
```

### 12.3 Key UI Behaviors

| Behavior | Detail |
|---|---|
| **Layout transition** | Smooth animated split when shortlist is first generated |
| **Missing data disclosure** | Gray badge with "Data unavailable" rather than hiding or guessing |
| **Source citations** | Collapsible "References" section on each card showing source URLs |
| **Filter chips** | Active filters shown as removable chips above the property list |
| **Real-time transcript** | Auto-scrolling transcript with distinct styling for user vs. bot messages |
| **Booking modal** | Overlay with date/time picker; shows confirmation with booking ID |

---

## 13. Evaluation Harness

### 13.1 Architecture

```mermaid
flowchart TB
    GOLDEN["golden_dataset.json<br/>(12-15 test cases)"]
    RUNNER["run_evals.py"]
    
    subgraph "Eval Modules"
        FEAS["Feasibility Eval"]
        EDIT["Edit Correctness Eval"]
        GROUND["Grounding &<br/>Hallucination Eval"]
    end
    
    subgraph "Eval Methods"
        RULE["Rule-Based<br/>Assertions"]
        JUDGE["LLM-as-Judge<br/>API Calls"]
    end
    
    LOG["eval_log_v{N}.json<br/>(Timestamped Report)"]

    GOLDEN --> RUNNER
    RUNNER --> FEAS
    RUNNER --> EDIT
    RUNNER --> GROUND
    FEAS --> RULE
    FEAS --> JUDGE
    EDIT --> RULE
    GROUND --> RULE
    GROUND --> JUDGE
    RULE --> LOG
    JUDGE --> LOG
```

### 13.2 Eval Module → Check Mapping

| Module | Check | Method | Pass Criteria |
|---|---|---|---|
| **Feasibility** | Budget & Must-Haves | Rule-based | `price <= max_budget` AND `bhk == required_bhk` for every property |
| **Feasibility** | Commute Claims | LLM Judge | Judge deems commute claim "realistic" for Bengaluru geography |
| **Edit Correctness** | State Tracking | Rule-based | Targeted key changed correctly; all other keys byte-identical |
| **Grounding** | Listing Validity | Rule-based | Every `property_id` exists in mock DB with `status == "available"` |
| **Grounding** | RAG Source Grounding | LLM Judge | Score ≥ 4 out of 5 for claim support |
| **Grounding** | Uncertainty Handling | Rule-based | Response contains uncertainty keywords when RAG context is empty |

### 13.3 CLI Usage

```bash
# Run all evals
python evals/run_evals.py

# Run specific eval module
python evals/run_evals.py --module feasibility

# Run with pytest
pytest evals/ -v --tb=short

# Output report
python evals/run_evals.py --output evals/logs/eval_log_v1.json
```

---

## 14. Deployment Architecture

### 14.1 Infrastructure Diagram

```mermaid
flowchart TB
    subgraph "CDN / Edge"
        VERCEL["Vercel / Netlify<br/>(Frontend)"]
    end

    subgraph "Compute"
        RENDER["Render / Railway<br/>(Backend API)"]
    end

    subgraph "Data"
        PG["PostgreSQL<br/>(Properties + Bookings)"]
        VECTOR["Vector DB<br/>(Pinecone / Qdrant / Weaviate)"]
    end

    subgraph "Automation"
        GHA["GitHub Actions<br/>(Daily Scraper)"]
        N8N["N8N Cloud / Self-Hosted<br/>(Email Workflows)"]
    end

    subgraph "External APIs"
        LLM_API["LLM API<br/>(OpenAI / Anthropic)"]
        STT_API["STT API<br/>(Whisper / Deepgram)"]
        TTS_API["TTS API<br/>(ElevenLabs / OpenAI)"]
        OSM_MCP["OpenStreetMap MCP"]
    end

    VERCEL <-->|HTTPS| RENDER
    RENDER <--> PG
    RENDER <--> VECTOR
    RENDER <--> LLM_API
    RENDER <--> STT_API
    RENDER <--> TTS_API
    RENDER <--> OSM_MCP
    RENDER <-->|Webhook| N8N
    GHA -->|Cron| PG
```

### 14.2 Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:pass@host:5432/property_scout

# Vector DB
VECTOR_DB_URL=https://...
VECTOR_DB_API_KEY=...

# LLM
LLM_API_KEY=...
LLM_MODEL=gpt-4o

# Voice
STT_API_KEY=...
TTS_API_KEY=...

# N8N
N8N_WEBHOOK_BASE_URL=https://n8n.example.com/webhook
N8N_BOOKING_WEBHOOK_PATH=/booking
N8N_SHORTLIST_WEBHOOK_PATH=/shortlist

# Email
SENDER_EMAIL=noreply@thepropertyscout.in

# OpenStreetMap MCP
OSM_MCP_ENDPOINT=...
```

---

## 15. Security & Privacy

### 15.1 PII Handling

| Stage | Measure |
|---|---|
| **Scraping** | Regex + NER-based removal of owner/agent names, phone numbers, emails before DB insert |
| **Storage** | No PII columns exist in the properties table |
| **User data** | Only email collected (for booking notifications); no passwords, no login |
| **Audit** | Scraper logs record PII detection counts (but not the PII itself) |

### 15.2 API Security

| Measure | Detail |
|---|---|
| **HTTPS** | All traffic encrypted in transit |
| **Rate limiting** | Per-session and per-IP rate limits on API endpoints |
| **Input validation** | Schema validation on all request bodies (e.g. Zod, Pydantic) |
| **CORS** | Restricted to frontend domain only |
| **Secrets** | All credentials in `.env`, never committed to version control |
| **WebSocket auth** | Session-token-based authentication for WS connections |

### 15.3 Data Integrity

| Concern | Mitigation |
|---|---|
| **Double booking** | DB-level unique constraint + row-level locking |
| **Stale listings** | Daily scraper marks removed listings as `unavailable` |
| **RAG hallucination** | Explicit uncertainty handling when no relevant chunks exist |
| **State corruption** | Immutable state diffing — edits create new state versions |

---

## 16. Proposed Directory Structure

```
the-property-scout/
├── .github/
│   └── workflows/
│       └── daily-scraper.yml          # GitHub Actions cron job
│
├── frontend/                           # Frontend application
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header/
│   │   │   ├── ConversationPane/
│   │   │   │   ├── TranscriptList/
│   │   │   │   ├── VoiceControls/
│   │   │   │   └── TextInput/
│   │   │   ├── PropertyPane/
│   │   │   │   ├── FilterBar/
│   │   │   │   ├── PropertyCard/
│   │   │   │   └── ShortlistActions/
│   │   │   └── BookingModal/
│   │   ├── hooks/                      # Custom React hooks
│   │   ├── services/                   # API client functions
│   │   ├── styles/                     # Global CSS / design tokens
│   │   ├── types/                      # TypeScript interfaces
│   │   ├── utils/                      # Shared utilities
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── backend/                            # Backend API server
│   ├── api/
│   │   ├── routes/
│   │   │   ├── session.py
│   │   │   ├── properties.py
│   │   │   ├── bookings.py
│   │   │   └── notifications.py
│   │   ├── middleware/
│   │   │   ├── rate_limiter.py
│   │   │   └── validation.py
│   │   └── app.py                      # Application entry point
│   ├── voice/
│   │   ├── stt.py                      # Speech-to-Text integration
│   │   ├── tts.py                      # Text-to-Speech integration
│   │   └── streaming.py               # WebSocket audio handler
│   ├── llm/
│   │   ├── orchestrator.py             # Main LLM conversation engine
│   │   ├── prompts.py                  # System prompts & templates
│   │   ├── state_manager.py            # Preference state machine
│   │   └── tools.py                    # LLM tool definitions
│   ├── rag/
│   │   ├── retriever.py                # Vector DB query logic
│   │   ├── reranker.py                 # Chunk relevance scoring
│   │   └── synthesizer.py             # Cited response generation
│   ├── mcp/
│   │   ├── osm_client.py              # OpenStreetMap MCP integration
│   │   └── amenity_mapper.py          # OSM tag → category mapping
│   ├── booking/
│   │   ├── service.py                  # Booking CRUD logic
│   │   ├── id_generator.py            # Booking/User ID generation
│   │   └── concurrency.py            # Locking & slot management
│   ├── notification/
│   │   ├── webhook.py                  # N8N webhook trigger
│   │   └── payloads.py                # Email payload builders
│   ├── db/
│   │   ├── models.py                   # ORM models
│   │   ├── migrations/                 # Database migrations
│   │   ├── connection.py              # Connection pool
│   │   └── queries.py                 # Query builders
│   ├── config.py                       # Environment & settings
│   ├── requirements.txt
│   └── Dockerfile
│
├── scraper/                            # Daily scraper (runs in GitHub Actions)
│   ├── main.py                         # Entry point
│   ├── parser.py                       # HTML → structured data
│   ├── pii_scrubber.py                # PII detection & removal
│   ├── normalizer.py                  # Data standardization
│   ├── geocoder.py                    # Address → lat/lng
│   └── requirements.txt
│
├── rag_ingestion/                      # Monthly RAG data pipeline
│   ├── crawler.py                      # Web crawler for blogs/Reddit/news
│   ├── chunker.py                      # Text → chunks
│   ├── embedder.py                     # Chunks → vectors
│   ├── upserter.py                    # Vector DB upsert
│   └── sources.json                   # List of source URLs to crawl
│
├── evals/                              # Evaluation suite
│   ├── run_evals.py                    # CLI entry point
│   ├── golden_dataset.json            # Static test cases (12-15)
│   ├── modules/
│   │   ├── feasibility.py             # Budget, BHK, commute checks
│   │   ├── edit_correctness.py        # State tracking assertions
│   │   └── grounding.py              # Listing validity, RAG grounding, uncertainty
│   ├── judges/
│   │   └── llm_judge.py              # LLM-as-Judge API wrapper
│   ├── logs/                           # Timestamped eval reports
│   └── conftest.py                    # pytest fixtures
│
├── Docs/
│   ├── problemstatement.txt
│   ├── context.md
│   └── architecture.md                 # This file
│
├── .env.example                        # Template for environment variables
├── .gitignore
├── docker-compose.yml                  # Local dev: backend + DB + vector DB
├── README.md
└── package.json                        # Root-level scripts (if monorepo)
```

---

## Appendix: Technology Decision Matrix

| Concern | Recommended | Alternatives | Rationale |
|---|---|---|---|
| **Relational DB** | PostgreSQL | MySQL, SQLite | JSONB support for preferences, robust locking, free tier on Render/Railway |
| **Vector DB** | Qdrant | Pinecone, Weaviate, ChromaDB | Self-hostable, good filtering, generous free tier |
| **LLM** | GPT-4o | Claude, Gemini | Strong tool-calling, widely available |
| **STT** | Deepgram | Whisper API, Google STT | Low-latency streaming, good accuracy for Indian English |
| **TTS** | ElevenLabs | OpenAI TTS, Google TTS | Natural-sounding voice, streaming support |
| **Frontend** | React + Vite | Next.js | SPA sufficient (no SSR needed), fast dev iteration |
| **Backend** | FastAPI (Python) | Express (Node) | Async support, Pydantic validation, strong LLM ecosystem |
| **Embedding Model** | `bge-large-en-v1.5` (BAAI) | `text-embedding-3-small`, `all-MiniLM-L6-v2` | 100% free, runs locally via sentence-transformers, top leaderboard accuracy, 1024 dimensions |
| **Workflow Engine** | N8N | Zapier, Make | Self-hostable, visual workflow builder, webhook support |
