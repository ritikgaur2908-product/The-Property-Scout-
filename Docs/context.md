# The Property Scout — Project Context

> **Source:** [problemstatement.txt](file:///c:/Users/Ritk%20Gaur/Desktop/The%20Property%20Scout/Docs/problemstatement.txt)
> **Generated:** 2026-08-14

---

## 1. Project Overview

**The Property Scout** is an AI-powered voice bot that helps users discover rental properties in Bengaluru. It operates as a conversational assistant that:

1. Collects user preferences via voice interaction.
2. Fetches and presents data-rich property listings (rent, amenities, neighborhood insights).
3. Lets users refine the shortlist conversationally.
4. Enables booking, rescheduling, and cancelling site visits.
5. Sends email notifications for all booking events and property shortlists.

---

## 2. Data Pipeline

### 2.1 Property Listings — Source & Ingestion

| Aspect | Detail |
|---|---|
| **Source** | [bengaluru.rent](https://bengaluru.rent/) |
| **Frequency** | Daily scrape via **GitHub Actions** |
| **Storage** | Relational database (updated daily) |
| **Scope** | **Active "for rent" listings only** — any listing marked *"Not for rent"* or flagged for transparency must be excluded |
| **PII** | All owner / agent personal details must be **scrubbed** before storage |

### 2.2 Property Data Fields

Each listing must capture:

- Accommodation type (Whole Flat / Room in Flat)
- Rent
- Number of rooms
- Move-in time
- Gender openness
- Parking availability (and count)
- Flatmate food preference *(Room in Flat only)*
- Flatmate smoking preference *(Room in Flat only)*
- Property address

### 2.3 Nearby Amenities — OpenStreetMap MCP

Amenity enrichment is powered by **OpenStreetMap MCP** and must cover:

| Category | Examples |
|---|---|
| **Daily Essentials & Retail** | Grocery stores, supermarkets, local markets, convenience shops, pharmacies, restaurants, cafes, fast-food chains |
| **Health & Education** | Hospitals, urgent care, clinics, schools, preschools, colleges, training centers |
| **Transport & Mobility** | Metro / bus / transit stops, taxi stands, auto-rickshaw stands, EV charging stations, fuel pumps |
| **Recreation & Community** | Parks, green spaces, walking tracks, playgrounds, sports facilities, gyms, banks, ATMs, post offices |

### 2.4 Neighborhood Practical Guidance — RAG Pipeline

Sourced from **public blogs, forums (e.g. Reddit threads), and news articles**. Scraped once and updated **monthly**, chunked and stored in a **Vector DB**.

Reference: [blrexplorer.littlemadcow.xyz](https://blrexplorer.littlemadcow.xyz/)

Must cover the following themes:

| Theme | Details |
|---|---|
| **Core Safety & Security** | Crime types & frequency, safe/unsafe zones, emergency contacts (police stations, hospitals, safe havens) |
| **Daily Life & Environment** | Noise levels, cleanliness & trash management, pest/stray animal/wildlife issues |
| **Getting Around & Access** | Walkability (sidewalks, crosswalks, hills), transit safety & reliability, parking rules & garage security |
| **Local Culture & Community** | Area vibe (quiet / loud / family / student), neighbor friendliness, noise curfews & social habits |

When the LLM processes a property (e.g. in *Indiranagar*), it retrieves the relevant RAG chunks for that neighborhood and provides **cited, practical guidance**.

### 2.5 Booking Data

All booking-related information is stored in a **database** to handle concurrency (prevent double-booking the same property at the same time).

---

## 3. Product Capabilities

### 3.1 Preference Collection (Voice-Based)

- Bot greets the user and initiates a conversational flow.
- Collects preferences via voice.
- Fetches matching listings, enriches them with amenities + neighborhood data.
- Provides **grounded reasoning** for why each listing was picked (no generic explanations).

### 3.2 Voice-Based Shortlist Refinement

Users refine results through natural language commands such as:

- *"Drop anything above 40k."*
- *"Only show me places within 15 minutes of a metro station."*
- *"I need something pet-friendly."*
- *"Add one more option with a balcony."*

> **Key constraint:** Only the affected part of the shortlist should change — unrelated listings must be preserved.

### 3.3 Site Visit Booking

| Feature | Detail |
|---|---|
| **Identification** | Unique Booking ID per visit (no login system) |
| **User tracking** | A unique user ID is assigned at first booking; reused for reschedule / cancel |
| **Concurrency** | Database-backed locking to prevent double-booking |
| **Operations** | Book / Reschedule / Cancel |

### 3.4 Notifications (Email via N8N)

Emails are triggered from a **dedicated sender address** through an **N8N workflow** on the following events:

| Event | Email Content |
|---|---|
| Booking created | Confirmation with booking details |
| Booking rescheduled | Updated schedule details |
| Booking cancelled | Cancellation acknowledgement |
| Shortlist mailed | Full enriched property list sent to user's inbox |

Each email must have a **descriptive subject line** and **contextual body** matching the intent.

---

## 4. UI & UX Requirements

### 4.1 Conversation Flow

1. System greets the user when they initiate a conversation.
2. Full **transcript** of every message is visible.
3. Once the initial shortlist is generated, the layout transitions:
   - **Left pane** — conversation / voice bot.
   - **Right pane** — property cards and data.

### 4.2 Property Cards

Each shortlist card must display:

- All enriched property data (rent, rooms, amenities, etc.)
- A **"Sources" / "References"** section showing provenance of neighborhood claims.
- If data is missing or unreliable, the system **must explicitly say so** — never guess.

### 4.3 Filters & Actions

- Inline filters to further refine the shortlist.
- Option to **mail the shortlist** to the user.
- Option to **book a site visit** for any property.

---

## 5. Evaluation Suite (Evals)

### 5.1 Overview

An **offline, automated evaluation suite** runnable via CLI (`pytest` or `run_evals.py`). Uses a **hybrid model**: rule-based programmatic assertions + LLM-as-a-Judge API calls.

Executed against a static **Golden Dataset** (`golden_dataset.json`) with 12–15 test cases.

### 5.2 Evaluation Dimensions

#### 5.2.1 Feasibility Eval

| Check | Type | Logic |
|---|---|---|
| **Budget & Must-Haves** | Rule-based | `property.price <= user.max_budget` AND `property.bhk == user.bhk` — FAIL if any property violates |
| **Commute Claims** | LLM-assisted | Judge whether the bot's commute claim is realistic given Bengaluru traffic geography |

#### 5.2.2 Edit Correctness Eval

| Check | Type | Logic |
|---|---|---|
| **State Tracking** | Rule-based | After a user edit (e.g. "Increase budget to 60k"), the targeted key is correctly modified AND all un-targeted keys remain **strictly identical** — FAIL if any key is wiped, nulled, or altered |

#### 5.2.3 Grounding & Hallucination Eval

| Check | Type | Logic |
|---|---|---|
| **Listing Validity** | Rule-based | Every `property_id` in bot output must exist in mock DB with `status == "available"` |
| **RAG Source Grounding** | LLM-assisted | Judge whether all neighborhood claims are fully supported by provided RAG chunks (score 1–5) |
| **Uncertainty Handling** | Rule-based | When RAG context is empty, response must contain explicit uncertainty keywords (e.g. *"I don't have information on"*, *"I am unsure"*) — FAIL if details are invented |

### 5.3 Golden Dataset Categories

| Category | Count | Description |
|---|---|---|
| **Happy Paths** | 3–4 | Standard searches in popular areas (HSR Layout, Indiranagar), straightforward bookings |
| **Multi-Turn Edit Edge Cases** | 3–4 | Budget changes mid-conversation, locality swaps, adding filters without losing state |
| **Adversarial & Out-of-Bounds** | 3 | Unrealistic requests (4BHK villa in Indiranagar for ₹15k), impossible commute claims, contradictory filters |
| **Failure Modes & RAG Edge Cases** | 3 | Missing neighborhood data, sold/unavailable property IDs, ambiguous inputs |

### 5.4 Test Case Schema

```json
{
  "test_id": "TC_001",
  "category": "edge_case_edit",
  "description": "User changes BHK requirement from 2 to 3 without dropping budget",
  "input_turns": [],
  "previous_state": {},
  "expected_state": {},
  "expected_behavior": {
    "must_contain_ids": [],
    "uncertainty_expected": false
  }
}
```

### 5.5 Logging

- `run_evals.py` saves timestamped JSON reports (e.g. `eval_log_v1.json`).
- Enables tracking score improvements (baseline vs. fine-tuned prompt performance) to demonstrate iteration depth.

---

## 6. Deployment & Code Quality

| Aspect | Requirement |
|---|---|
| **Frontend hosting** | Vercel / Netlify |
| **Backend hosting** | Render / Railway / Docker container |
| **Architecture** | Modular separation: RAG logic · Voice processing · MCP tools · Database models |
| **Secrets management** | `.env` for API keys, database credentials, webhook URLs |
| **Type safety** | Type-safe interfaces or clear schemas across all API routes |

---

## 7. Technology & Integration Summary

```
┌─────────────────────────────────────────────────────────┐
│                   THE PROPERTY SCOUT                    │
├─────────────┬───────────────────────────────────────────┤
│  Frontend   │  Vercel / Netlify                         │
│  Backend    │  Render / Railway / Docker                 │
│  Voice      │  AI Voice Bot (conversational)             │
│  Data       │  bengaluru.rent (daily scrape via GH Actions) │
│  Amenities  │  OpenStreetMap MCP                         │
│  RAG        │  Vector DB (blogs, Reddit, news — monthly) │
│  Booking DB │  Relational DB (concurrency-safe)          │
│  Email      │  N8N workflow (book/reschedule/cancel/mail)│
│  Evals      │  pytest / run_evals.py + LLM Judge         │
└─────────────┴───────────────────────────────────────────┘
```

---

## 8. Key Constraints & Non-Negotiables

1. **No PII** — Owner/agent details must be scrubbed from scraped data.
2. **No hallucinations** — If data is missing, the system must explicitly state uncertainty.
3. **Grounded explanations** — Every recommendation reason must cite real data, not generic filler.
4. **State preservation** — Conversational edits must not wipe unrelated filter state.
5. **Concurrency safety** — Booking system must prevent double-booking via database-level controls.
6. **Daily freshness** — Property data must be scraped and updated daily.
7. **Active listings only** — Exclude anything not currently for rent.
