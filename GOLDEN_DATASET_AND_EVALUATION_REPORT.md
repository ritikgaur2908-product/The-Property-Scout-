# 🏆 The Property Scout — Golden Dataset, Adversarial Tests & Evaluation Report

> **Comprehensive evaluation suite documentation, golden dataset specifications, adversarial stress tests, and automated LLM-as-a-Judge validation scores for The Property Scout.**

---

## 📊 Executive Summary & Model Scorecard

| Metric | Evaluation Module | Total Tests | Passed | Failed | Pass Rate | Score / Rating |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| 🎯 **Core Search & Execution** | `feasibility` | 15 | 15 | 0 | **100%** | **15 / 15** |
| 🔄 **Multi-Turn Shortlist Edits** | `edit_correctness` | 6 *(9 skipped)* | 6 | 0 | **100%** | **6 / 6** |
| 🛡️ **RAG Grounding & Hallucination** | `grounding` | 15 | 15 | 0 | **100%** | **5.0 / 5.0 (LLM Judge)** |
| ⚡ **Overall System Integrity** | **All Combined** | **36 checks** | **36** | **0** | **100%** | **GRADE: A+** |

* **Active Production LLM**: `openai/gpt-oss-20b` (Groq LPU Hardware Acceleration)
* **Embedding Model**: Google Gemini Embeddings (`text-embedding-004`)
* **Vector Database**: Qdrant Cloud (Cosine Metric, 768-dim)
* **Relational Database**: PostgreSQL (Supabase Cloud)
* **Evaluation Framework**: Custom Automated Test Suite (`evals/run_evals.py` + `pytest`)

---

## 🗂️ The Complete Golden Dataset (15 Benchmark Test Cases)

The Golden Dataset evaluates the AI assistant across **4 rigorous categories**:
1. **Happy Paths (`happy_path`)**: Standard voice queries, budget filters, room-in-flat matching, and site visit bookings.
2. **Multi-Turn Shortlist Edits (`edge_case_edit`)**: Contextual state manipulation (narrowing, expanding, filter replacement, constraint dropping) without losing existing session memory.
3. **Adversarial Attacks (`adversarial`)**: Economically impossible requests, cross-city queries, and contradictory constraints.
4. **Failure Modes & Hallucination Resistance (`failure_mode`)**: Missing RAG data, non-existent property bookings, and vague user inputs.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   GOLDEN DATASET MATRIX                                         │
├─────────────┬───────────────────┬───────────────────────────────────────────────────────────────┤
│ Test ID     │ Category          │ Scenario / Prompt Description                                 │
├─────────────┼───────────────────┼───────────────────────────────────────────────────────────────┤
│ TC_HP_001   │ happy_path        │ Standard search for 2BHK in Indiranagar under 45k             │
│ TC_HP_002   │ happy_path        │ Search for a male room in HSR Layout under 15k                │
│ TC_HP_003   │ happy_path        │ Book a visit for a specific property with email & time        │
│ TC_HP_004   │ happy_path        │ Search with specific amenities: parking near metro station    │
│ TC_MT_001   │ edge_case_edit    │ User updates BHK requirement (2BHK ➔ 3BHK) retaining budget  │
│ TC_MT_002   │ edge_case_edit    │ User swaps locality (HSR ➔ Bellandur) retaining all filters   │
│ TC_MT_003   │ edge_case_edit    │ User adds vegetarian filter mid-conversation for a room       │
│ TC_MT_004   │ edge_case_edit    │ User removes budget constraint entirely mid-conversation      │
│ TC_ADV_001  │ adversarial       │ Impossible ask: 4BHK luxury villa in Indiranagar for 15k      │
│ TC_ADV_002  │ adversarial       │ Out-of-scope city: Asking for flats in Bandra, Mumbai         │
│ TC_ADV_003  │ adversarial       │ Contradictory filters in one turn: Veg flat vs Non-veg tenant │
│ TC_FAIL_001 │ failure_mode      │ Obscure locality query with zero RAG data (Doddakallasandra)  │
│ TC_FAIL_002 │ failure_mode      │ Booking a non-existent property UUID (PROP-99999999)          │
│ TC_FAIL_003 │ failure_mode      │ Extremely vague input ("I want a cheap house somewhere nice") │
│ TC_FAIL_004 │ failure_mode      │ Commute query not covered in RAG data                         │
└─────────────┴───────────────────┴───────────────────────────────────────────────────────────────┘
```

---

## 🔍 Detailed Golden Test Cases & Expected Behaviors

### Category 1: Happy Path Tests (`happy_path`)

#### 1. `TC_HP_001`: Standard 2BHK Search in Indiranagar
* **Input Prompt**: `"I'm looking for a 2BHK in Indiranagar, my budget is around 45k per month."`
* **Expected State**: `{"min_bhk": 2, "localities": ["Indiranagar"], "max_budget": 45000, "accommodation_type": "whole_flat"}`
* **Evaluation Criteria**: Returns matching PostgreSQL listings; extracts parameters accurately; synthesizes voice summary pointing to screen.
* **Result**: **PASS** (Grounding Score: **5/5**)

#### 2. `TC_HP_002`: Flatmate / Room-in-Flat Search
* **Input Prompt**: `"I need a room in a pre-occupied flat in HSR Layout. I'm a guy, budget is 15k."`
* **Expected State**: `{"localities": ["HSR Layout"], "max_budget": 15000, "accommodation_type": "room_in_flat", "gender": "male"}`
* **Evaluation Criteria**: Distinguishes `room_in_flat` from `whole_flat`; filters by gender openness.
* **Result**: **PASS** (Grounding Score: **5/5**)

#### 3. `TC_HP_003`: Automated Site Visit Booking
* **Input Prompt**: `"Book a visit for property PROP-TEST-001 for tomorrow at 10 AM. My email is test@example.com."`
* **Expected Behavior**: Calls `book_visit` tool; validates slot availability; generates unique `BK-XXXXXX` booking reference.
* **Result**: **PASS**

#### 4. `TC_HP_004`: Specific Amenities & Metro Proximity
* **Input Prompt**: `"Find me a 3BHK in Whitefield with parking and near a metro station."`
* **Expected State**: `{"min_bhk": 3, "localities": ["Whitefield"], "parking": true}`
* **Evaluation Criteria**: Checks OpenStreetMap radius data; reports verified transit distances.
* **Result**: **PASS** (Grounding Score: **5/5**)

---

### Category 2: Multi-Turn Shortlist Edit Tests (`edge_case_edit`)

#### 5. `TC_MT_001`: Modifying BHK without Dropping Budget
* **Turn 1**: `"I want a 2BHK in Koramangala, budget 50k."` (Prior State: `min_bhk=2`, `budget=50000`)
* **Turn 2**: `"Actually, make that a 3BHK instead."`
* **Expected State**: `{"min_bhk": 3, "localities": ["Koramangala"], "max_budget": 50000, "accommodation_type": "whole_flat"}`
* **Evaluation Criteria**: Only `min_bhk` is mutated from 2 ➔ 3. Budget (`50000`) and locality (`Koramangala`) remain strictly intact.
* **Result**: **PASS** (Edit Correctness: **PASS**, Grounding: **5/5**)

#### 6. `TC_MT_002`: Swapping Locality without Losing Other Filters
* **Turn 1**: `"Show me 1BHKs in HSR Layout under 30k."` (Prior State: `locality=HSR`, `budget=30000`, `min_bhk=1`)
* **Turn 2**: `"Check in Bellandur instead of HSR."`
* **Expected State**: `{"localities": ["Bellandur"], "max_budget": 30000, "min_bhk": 1}`
* **Evaluation Criteria**: Replaces `HSR Layout` with `Bellandur`. Preserves `30000` budget and `1 BHK` configuration.
* **Result**: **PASS** (Edit Correctness: **PASS**)

#### 7. `TC_MT_003`: Incremental Preference Addition (Dietary Preference)
* **Turn 1**: `"I'm looking for a room in BTM Layout, I'm a female, budget 12k."`
* **Turn 2**: `"Oh, I forgot to mention — I need a vegetarian flat."`
* **Expected State**: `{"localities": ["BTM Layout"], "max_budget": 12000, "accommodation_type": "room_in_flat", "gender": "female", "food": "veg"}`
* **Evaluation Criteria**: Adds `food: "veg"` to active state without clearing female room or 12k budget.
* **Result**: **PASS** (Edit Correctness: **PASS**)

#### 8. `TC_MT_004`: Dropping Constraint Mid-Conversation
* **Turn 1**: `"Show me 2BHKs in Jayanagar under 40k."`
* **Turn 2**: `"You know what, forget the budget limit. Just show me the best 2BHKs in Jayanagar."`
* **Expected State**: `{"localities": ["Jayanagar"], "min_bhk": 2, "max_budget": null}`
* **Evaluation Criteria**: Correctly nullifies `max_budget` constraint while keeping locality and BHK active.
* **Result**: **PASS** (Edit Correctness: **PASS**)

---

### Category 3: Adversarial Tests (`adversarial`)

#### 9. `TC_ADV_001`: Economically Unrealistic Market Ask
* **Input Prompt**: `"I want a 4BHK independent house in Indiranagar for exactly 15 thousand per month."`
* **Adversarial Vector**: Indiranagar 4BHK market rates start at ₹90,000+. Budget of ₹15,000 is impossible.
* **Expected Model Behavior**: 
  1. Does **not** hallucinate cheap fake villas.
  2. Acknowledges no listings exist in that price bracket.
  3. Suggests realistic alternatives (e.g. adjusting budget or searching 1BHK/room in flat).
* **Evaluation Result**: **PASS**
  * *Uncertainty Expressed*: `True`
  * *RAG Grounding Score*: **5 / 5**

#### 10. `TC_ADV_002`: Out-of-Scope Geographic Boundary Attack
* **Input Prompt**: `"Show me flats in Bandra, Mumbai."`
* **Adversarial Vector**: The Property Scout is strictly scoped to Bengaluru rentals.
* **Expected Model Behavior**:
  1. Declines politely: *"I'm set up to help with Bengaluru rentals — happy to help with that!"*
  2. Does not call database search for Mumbai.
* **Evaluation Result**: **PASS**
  * *Boundary Adherence*: `100%`

#### 11. `TC_ADV_003`: Contradictory Filters in a Single Turn
* **Input Prompt**: `"I want a room in a flat that only allows vegetarians, but I eat chicken so they have to be okay with non-veg."`
* **Adversarial Vector**: Simultaneous contradictory constraints (`food: veg` vs `food: non_veg`).
* **Expected Model Behavior**:
  1. Identifies the logical conflict.
  2. Asks for clarification rather than executing a broken database filter.
* **Evaluation Result**: **PASS**

---

### Category 4: Failure Mode & Hallucination Resistance Tests (`failure_mode`)

#### 12. `TC_FAIL_001`: Obscure Locality with Zero RAG Indexing
* **Input Prompt**: `"What is the safety like at night in Doddakallasandra?"`
* **Failure Vector**: `Doddakallasandra` is not present in the vector database.
* **Expected Model Behavior**:
  1. Expresses honest uncertainty: *"I don't have verified information on safety in Doddakallasandra yet."*
  2. Never invents fake crime statistics or synthetic resident quotes.
* **Evaluation Result**: **PASS** (Uncertainty detected: `True`)

#### 13. `TC_FAIL_002`: Booking Non-Existent Property ID
* **Input Prompt**: `"Book PROP-99999999 for me at 3 PM tomorrow. Email is test@example.com."`
* **Failure Vector**: `PROP-99999999` does not exist in the database.
* **Expected Model Behavior**:
  1. Catches the `404 / Property Not Found` error from the booking service.
  2. Informs user clearly that the property could not be found.
* **Evaluation Result**: **PASS**

#### 14. `TC_FAIL_003`: Extremely Vague / Underspecified Input
* **Input Prompt**: `"I want a cheap house somewhere nice."`
* **Failure Vector**: Missing both mandatory gates (`locality` and `max_budget`).
* **Expected Model Behavior**:
  1. Does not search blind.
  2. Asks a friendly clarifying question: *"Which neighborhood in Bengaluru do you prefer, and what monthly budget are you working with?"*
* **Evaluation Result**: **PASS**

#### 15. `TC_FAIL_004`: Specific Commute Query with Zero Transit Data
* **Input Prompt**: `"How long does it take to drive from this property to Electronic City Phase 2 during morning peak hours?"`
* **Failure Vector**: Specific peak-hour commute route not indexed in RAG knowledge base.
* **Expected Model Behavior**:
  1. Acknowledges lack of real-time traffic data rather than fabricating an exact minute count.
* **Evaluation Result**: **PASS** (Grounding Score: **5 / 5**)

---

## 🤖 LLM-as-a-Judge Scoring & Evaluation Metrics

The evaluation suite uses **LLM-as-a-Judge** (`evals/judges/llm_judge.py`) to grade response accuracy, hallucination resistance, and context fidelity on a 1–5 scale:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   LLM JUDGE RUBRIC (1 - 5)                                      │
├───────┬─────────────────────────────────────────────────────────────────────────────────────────┤
│ Score │ Description                                                                             │
├───────┼─────────────────────────────────────────────────────────────────────────────────────────┤
│   5   │ PERFECT: 100% of claims trace directly to verified RAG context. Zero hallucinations.    │
│   4   │ MINOR: Completely accurate with minor conversational paraphrasing.                      │
│   3   │ BORDERLINE: Unsupported minor claim that doesn't contradict facts.                      │
│   2   │ POOR: Contains unverified claims or assumes facts not in the context.                   │
│   1   │ UNACCEPTABLE: Direct factual contradiction or fabricated properties/neighborhood data.  │
└───────┴─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 📈 Latest Evaluation Execution Log (`evals/logs/eval_log_20260823_124509.json`)

```json
{
  "run_at": "2026-08-23T07:14:39.550253+00:00",
  "module_filter": "all",
  "total_cases": 15,
  "summary": {
    "feasibility": { "passed": 15, "failed": 0, "skipped": 0 },
    "edit_correctness": { "passed": 6, "failed": 0, "skipped": 9 },
    "grounding": { "passed": 15, "failed": 0, "skipped": 0, "avg_rag_score": 5.0 }
  },
  "verdict": "ALL CHECKS PASSED (100%)"
}
```

---

## 🚀 How to Reproduce and Run the Evals

To execute the entire automated evaluation suite on your local machine:

```bash
# Run all 3 modules (Feasibility, Edit Correctness, RAG Grounding) with verbose output
python evals/run_evals.py --verbose

# Run individual modules
python evals/run_evals.py --module feasibility --verbose
python evals/run_evals.py --module edit_correctness --verbose
python evals/run_evals.py --module grounding --verbose

# Run with PyTest
pytest evals/ -v
```

---

*Report generated and validated for **The Property Scout**.*
