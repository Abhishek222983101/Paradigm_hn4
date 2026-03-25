# ♻️ TraceLoop — Intelligent Traceability for Recycled Materials

> AI-powered end-to-end material tracking system for the circular economy. From waste collection to final dispatch — transparent, trustworthy, and conversational.

---

## What is TraceLoop?

TraceLoop is an intelligent traceability management system for recycled plastic materials. It replaces rigid forms, fragmented spreadsheets, and manual data entry with a conversational AI interface and a live visual dashboard that tracks every kilogram of material from collection to dispatch.

Built for recycling facilities, regulators, and sustainability stakeholders who need **accurate, accessible, and trustworthy** lifecycle data.

---

## The Problem We're Solving

Recycling companies struggle to answer a simple question: *where did this material come from, and where did it go?*

Current systems suffer from:
- Manual data entry that is error-prone and time-consuming
- Fragmented reporting across spreadsheets and forms
- No visibility into processing losses or inefficiencies
- Dashboards that non-technical stakeholders can't interpret
- No trust signals — regulators can't verify data completeness or reliability

TraceLoop fixes all of this.

---

## Key Features

### 💬 Conversational Data Entry
Type naturally. The AI handles the rest.

```
User:  "Purchased 300 kg of PET bottles from Vendor A yesterday"
AI:    ✓ Logged — Batch B-031 created. 300 kg PET from Vendor A on Mar 24.
       Data confidence: 20% (1/5 stages complete)
```

Supported intents: Purchase · Processing Start · Processing End · Dispatch · Query

### 📊 Interactive Visual Dashboard
- **Sankey diagram** — full material flow from source to dispatch, with losses visualized
- **Loss waterfall chart** — see exactly where material is lost at each stage
- **Batch timeline** — every batch as a horizontal swimlane, colored by stage
- **Material type breakdown** — PET vs HDPE vs PP vs Mixed, filterable by date
- **Live credibility badges** — data completeness score (0–100%) per batch record

### 🤖 AI-Driven Insights
Auto-generated plain-English summaries for every batch:

```
Batch B-047 summary:
500 kg of HDPE was purchased from Vendor B on Mar 10. After sorting and
processing, 387 kg of recycled pellets were dispatched to GreenTech Industries —
a 22.6% total loss rate, 4.6% above the facility average. Processing loss
exceeded the threshold on Mar 14; a missing weight-out entry reduces data
confidence to 61% for this batch.
```

Anomaly flagging, completeness scoring, and narrative generation — all automatic.

### 🔍 Conversational Querying
Ask questions in plain language:

```
"How much material was dispatched last week?"
"Show me processing losses for PET this month"
"Which vendor supplied the most material in Q1?"
"Flag batches with data confidence below 70%"
```

---

## Material Lifecycle Tracked

```
Collection → Procurement → Sorting → Processing → Recycled Output → Dispatch
```

At every stage transition, the system records:
- Weight in / weight out (loss = inefficiency or contamination)
- Operator, timestamp, vendor/buyer
- Batch ID for full traceability

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | React + Plotly.js | Sankey + charts, runs in browser |
| Backend | FastAPI (Python) | Lightweight REST API, easy JSON |
| Database | SQLite | Zero infrastructure, fully local |
| AI / NLP | Ollama + Phi-3-mini (3.8B) | Runs on CPU, no GPU required |
| Insight engine | Phi-3-mini via prompt engineering | Narrative generation, anomaly detection |
| Mock data | Python seed script | 3 months of realistic batch events |

> All components run on a standard student laptop. No cloud required.

---

## Project Structure

```
traceloop/
├── backend/
│   ├── main.py              # FastAPI app — /ingest, /dashboard-data, /insights
│   ├── database.py          # SQLite setup and queries
│   ├── nlp.py               # Intent classification + entity extraction
│   ├── insights.py          # AI summary and anomaly generation
│   └── seed_data.py         # Mock dataset generator
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatPanel.jsx        # Conversational input UI
│   │   │   ├── SankeyDiagram.jsx    # Material flow visualization
│   │   │   ├── BatchTimeline.jsx    # Per-batch stage tracker
│   │   │   ├── LossWaterfall.jsx    # Stage-by-stage loss chart
│   │   │   ├── BatchCard.jsx        # AI insight card per batch
│   │   │   └── CredibilityBadge.jsx # Data completeness indicator
│   │   └── App.jsx
│   └── package.json
├── docs/
│   ├── data_assumptions.md   # All assumptions about the mock dataset
│   ├── design_rationale.md   # Why we made each visualization choice
│   └── ai_transparency.md    # How AI improves trust in the system
└── README.md
```

---

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- [Ollama](https://ollama.ai) installed locally

### 1. Pull the AI model
```bash
ollama pull phi3:mini
```

### 2. Set up the backend
```bash
cd backend
pip install fastapi uvicorn sqlite3 ollama
python seed_data.py        # seeds SQLite with 3 months of mock data
uvicorn main:app --reload  # starts API on http://localhost:8000
```

### 3. Start the frontend
```bash
cd frontend
npm install
npm run dev                # starts UI on http://localhost:5173
```

### 4. Open the app
Navigate to `http://localhost:5173` — the dashboard loads with mock data pre-populated. Try typing in the chat panel.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/ingest` | Submit a natural language entry or structured event |
| `GET` | `/dashboard-data` | Aggregated flow data for all charts |
| `GET` | `/insights/{batch_id}` | Fetch or generate AI insight for a batch |
| `GET` | `/batches` | List all batches with stage and confidence info |
| `GET` | `/query` | Natural language query → structured result |

---

## Data Schema

```sql
batches   (batch_id, material_type, source_vendor, collection_date)
events    (batch_id, stage, qty_in_kg, qty_out_kg, operator, timestamp)
vendors   (vendor_id, name, location, material_types)
insights  (batch_id, insight_type, content, generated_at)
```

---

## Data Assumptions

All data in this submission is synthetically generated. Key assumptions:

- **3 vendors** — Vendor A (PET specialist), Vendor B (HDPE/PP mixed), Vendor C (post-consumer mixed)
- **15 batches** across Jan–Mar 2024, ranging from 200–800 kg per purchase
- **Sorting loss** assumed at 5–10% (contamination removal)
- **Processing loss** assumed at 15–25% (shredding, washing, granulation)
- **Dispatch yield** is 65–80% of original input weight across a full batch lifecycle
- **Data completeness** is intentionally incomplete on ~30% of batches to demonstrate the credibility scoring feature
- Material types: PET, HDPE, PP, LDPE, Mixed

See `docs/data_assumptions.md` for full details.

---

## Design Rationale

**Why a Sankey diagram?** It is the single most intuitive way to show material flow and loss simultaneously. The width of each flow = kg of material. Losses visibly "drain" from the main flow. A regulator can see in seconds where material is going and where it's being lost.

**Why conversational input?** Recycling facility operators are not data entry clerks. They work on the floor. Typing one sentence is faster and less error-prone than navigating a multi-field form. The AI extracts structure so the database stays clean.

**Why credibility scoring?** Data you can't trust is worse than no data. Showing a 61% confidence badge next to a batch record tells stakeholders exactly how much weight to give that number — turning uncertainty into a feature rather than hiding it.

See `docs/design_rationale.md` for full discussion.

---

## How AI Improves Transparency

1. **Removes the expertise barrier** — stakeholders don't need to read charts; the AI reads them and writes a summary in plain English
2. **Surfaces what's hidden** — anomalies that would be invisible in a table (e.g. loss rate 2σ above average) are automatically flagged
3. **Builds accountability** — every AI-generated insight is timestamped and tied to specific batch data, making claims verifiable
4. **Scales trust signals** — data completeness is computed and displayed automatically, so regulators know when to ask for more information

See `docs/ai_transparency.md` for full discussion.

---

## Team

Built at **[Hackathon Name]** · [Date]

| Name | Role |
|---|---|
| — | AI / NLP pipeline |
| — | Backend + database |
| — | Frontend + dashboard |
| — | Design + documentation |

---

## License

MIT — free to use, adapt, and build on.
