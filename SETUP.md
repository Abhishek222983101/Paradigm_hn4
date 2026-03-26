# TraceLoop - Intelligent Traceability for Recycled Materials

## Quick Start

### Backend
```bash
pip install -r requirements.txt
python main.py
```
Server runs at http://localhost:8000

### Frontend
```bash
cd frontend
npm install
npm run dev
```
UI runs at http://localhost:3000

## Features

- Conversational data entry via chat interface
- Visual dashboard with charts and Sankey diagram
- Batch tracking with full lifecycle traceability
- AI-generated insights and recommendations
- Real-time anomaly detection
- Confidence scoring for data completeness

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/chat` | Conversational input |
| `GET /api/batches` | List all batches |
| `GET /api/batches/{id}` | Batch details |
| `GET /api/dashboard` | Dashboard metrics |
| `GET /api/insights/{id}` | AI insights |
| `GET /api/anomalies` | Anomaly detection |

## Tech Stack

- **Backend**: FastAPI, SQLite, Python 3.10+
- **Frontend**: React, Vite, TailwindCSS, Recharts
- **AI/NLP**: Featherless.ai (Phi-3-mini)

## Project Structure

```
traceloop/
├── backend/
│   ├── database.py
│   ├── nlp_engine.py
│   ├── insights.py
│   ├── ai_service.py
│   └── anomaly_detector.py
├── frontend/
│   └── src/components/
├── tests/
├── data/
└── docs/
```
