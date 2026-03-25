# TraceLoop

Intelligent Traceability Management for Recycled Materials

## Quick Start

### Backend
```bash
pip install -r requirements.txt
python main.py
```
API will be available at http://localhost:8000

### Frontend
```bash
cd frontend
npm install
npm run dev
```
UI will be available at http://localhost:3000

## Features

- Conversational data entry with NLP
- Visual dashboard with charts
- Batch tracking and traceability
- AI-generated insights
- Loss analysis and anomaly detection

## API Endpoints

- `POST /api/chat` - Conversational input
- `GET /api/batches` - List all batches
- `GET /api/batches/{id}` - Batch details
- `GET /api/dashboard` - Dashboard data
- `GET /api/insights/{id}` - AI insights
