"""
TraceLoop - Intelligent Traceability for Recycled Materials
FastAPI Backend for Conversational Data Entry & Dashboard
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import sqlite3
import json
import re
import random

app = FastAPI(
    title="TraceLoop API",
    description="Intelligent Traceability Management for Recycled Materials",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "traceloop.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS batches (
            batch_id TEXT PRIMARY KEY,
            material_type TEXT NOT NULL,
            source_vendor TEXT,
            collection_date TEXT,
            status TEXT DEFAULT 'created',
            total_input_kg REAL DEFAULT 0,
            total_output_kg REAL DEFAULT 0,
            confidence_score INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id TEXT NOT NULL,
            stage TEXT NOT NULL,
            qty_in_kg REAL,
            qty_out_kg REAL,
            operator TEXT,
            vendor TEXT,
            buyer TEXT,
            notes TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (batch_id) REFERENCES batches(batch_id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendors (
            vendor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            location TEXT,
            material_types TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS insights (
            insight_id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id TEXT NOT NULL,
            insight_type TEXT,
            content TEXT,
            generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (batch_id) REFERENCES batches(batch_id)
        )
    """)
    
    conn.commit()
    conn.close()

class ChatInput(BaseModel):
    text: str
    batch_id: Optional[str] = None

class BatchCreate(BaseModel):
    material_type: str
    source_vendor: Optional[str] = None
    collection_date: Optional[str] = None

class EventCreate(BaseModel):
    batch_id: str
    stage: str
    qty_in_kg: Optional[float] = None
    qty_out_kg: Optional[float] = None
    operator: Optional[str] = None
    vendor: Optional[str] = None
    buyer: Optional[str] = None
    notes: Optional[str] = None

STAGES = ["collection", "procurement", "sorting", "processing", "recycling", "dispatch"]
MATERIAL_TYPES = ["PET", "HDPE", "PP", "LDPE", "Mixed"]

def parse_natural_language(text: str) -> dict:
    text_lower = text.lower()
    
    intent = "unknown"
    entities = {
        "material_type": None,
        "quantity_kg": None,
        "vendor": None,
        "buyer": None,
        "date": None,
        "stage": None,
        "operator": None
    }
    
    if any(word in text_lower for word in ["purchased", "bought", "procured", "buy", "purchase"]):
        intent = "purchase"
        entities["stage"] = "procurement"
    elif any(word in text_lower for word in ["sorted", "sorting", "sort"]):
        intent = "sorting"
        entities["stage"] = "sorting"
    elif any(word in text_lower for word in ["processed", "processing", "process"]):
        intent = "processing"
        entities["stage"] = "processing"
    elif any(word in text_lower for word in ["dispatched", "dispatch", "sent", "shipped", "delivered"]):
        intent = "dispatch"
        entities["stage"] = "dispatch"
    elif any(word in text_lower for word in ["recycl", "output"]):
        intent = "recycling"
        entities["stage"] = "recycling"
    elif any(word in text_lower for word in ["collected", "collection", "collect"]):
        intent = "collection"
        entities["stage"] = "collection"
    elif any(word in text_lower for word in ["show", "how much", "what", "list", "report", "summary"]):
        intent = "query"
    
    quantity_pattern = r'(\d+(?:\.\d+)?)\s*(?:kg|kilogram|kgs)'
    qty_match = re.search(quantity_pattern, text_lower)
    if qty_match:
        entities["quantity_kg"] = float(qty_match.group(1))
    
    for mat in MATERIAL_TYPES:
        if mat.lower() in text_lower:
            entities["material_type"] = mat
            break
    
    vendor_patterns = [
        r'(?:from|vendor)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)',
        r'vendor\s*([A-Za-z]+)',
    ]
    for pattern in vendor_patterns:
        match = re.search(pattern, text_lower)
        if match:
            entities["vendor"] = match.group(1).title()
            break
    
    buyer_patterns = [
        r'(?:to|customer)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)',
    ]
    for pattern in buyer_patterns:
        match = re.search(pattern, text_lower)
        if match:
            entities["buyer"] = match.group(1).title()
            break
    
    date_patterns = {
        "today": datetime.now().strftime("%Y-%m-%d"),
        "yesterday": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
    }
    for key, val in date_patterns.items():
        if key in text_lower:
            entities["date"] = val
            break
    
    return {
        "intent": intent,
        "entities": entities,
        "original_text": text,
        "confidence": 0.85
    }

def generate_batch_id() -> str:
    return f"B-{random.randint(100, 999)}"

def calculate_confidence(batch_id: str) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM events WHERE batch_id = ?", (batch_id,))
    event_count = cursor.fetchone()[0]
    conn.close()
    
    stages_present = min(event_count, 5)
    confidence = int((stages_present / 5) * 100)
    return min(confidence, 100)

@app.on_event("startup")
def startup():
    init_db()
    seed_mock_data()

def seed_mock_data():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM batches")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return
    
    vendors = [
        ("GreenCorp", "Mumbai", "PET,HDPE"),
        ("EcoWaste Ltd", "Delhi", "PP,LDPE"),
        ("RecycleFirst", "Bangalore", "Mixed"),
    ]
    cursor.executemany("INSERT OR IGNORE INTO vendors (name, location, material_types) VALUES (?, ?, ?)", vendors)
    
    mock_batches = [
        ("B-101", "PET", "GreenCorp", "2024-01-15", "dispatched", 500, 380, 85),
        ("B-102", "HDPE", "EcoWaste Ltd", "2024-02-01", "processing", 350, 0, 60),
        ("B-103", "PP", "RecycleFirst", "2024-02-20", "sorting", 200, 0, 40),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO batches (batch_id, material_type, source_vendor, collection_date, status, total_input_kg, total_output_kg, confidence_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        mock_batches
    )
    
    mock_events = [
        ("B-101", "procurement", 500, 500, "Raj", "GreenCorp", None, "Purchased PET bottles"),
        ("B-101", "sorting", 500, 450, "Amit", None, None, "50kg rejected - contamination"),
        ("B-101", "processing", 450, 380, "Priya", None, None, "70kg processing loss"),
        ("B-101", "dispatch", 380, 380, "Suresh", None, "PlastiCo", "Dispatched to PlastiCo"),
        ("B-102", "procurement", 350, 350, "Raj", "EcoWaste Ltd", None, "HDPE bales purchased"),
        ("B-102", "sorting", 350, 320, "Amit", None, None, "30kg contamination removed"),
        ("B-102", "processing", 320, None, "Priya", None, None, "In progress"),
        ("B-103", "procurement", 200, 200, "Raj", "RecycleFirst", None, "Mixed plastic lot"),
        ("B-103", "sorting", 200, None, "Amit", None, None, "Sorting in progress"),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO events (batch_id, stage, qty_in_kg, qty_out_kg, operator, vendor, buyer, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        mock_events
    )
    
    conn.commit()
    conn.close()

@app.get("/")
def root():
    return {"message": "TraceLoop API - Intelligent Traceability for Recycled Materials", "version": "1.0.0"}

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "TraceLoop"}

@app.post("/api/chat")
def chat_input(input: ChatInput):
    parsed = parse_natural_language(input.text)
    
    if parsed["intent"] == "query":
        return handle_query(input.text, parsed)
    
    if parsed["intent"] == "unknown":
        return {
            "success": False,
            "message": "Could not understand the intent. Try: 'Purchased 300kg PET from Vendor A' or 'Show batches'",
            "parsed": parsed
        }
    
    batch_id = input.batch_id
    if not batch_id:
        batch_id = generate_batch_id()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO batches (batch_id, material_type, source_vendor, collection_date, total_input_kg) VALUES (?, ?, ?, ?, ?)",
            (batch_id, parsed["entities"]["material_type"] or "Mixed", parsed["entities"]["vendor"], parsed["entities"]["date"] or datetime.now().strftime("%Y-%m-%d"), parsed["entities"]["quantity_kg"] or 0)
        )
        conn.commit()
        conn.close()
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO events (batch_id, stage, qty_in_kg, qty_out_kg, vendor, buyer, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (batch_id, parsed["entities"]["stage"], parsed["entities"]["quantity_kg"], None, parsed["entities"]["vendor"], parsed["entities"]["buyer"], input.text)
    )
    conn.commit()
    conn.close()
    
    confidence = calculate_confidence(batch_id)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE batches SET confidence_score = ? WHERE batch_id = ?", (confidence, batch_id))
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "message": f"{parsed['intent'].capitalize()} recorded for batch {batch_id}",
        "batch_id": batch_id,
        "parsed": parsed,
        "confidence_score": confidence
    }

def handle_query(text: str, parsed: dict) -> dict:
    conn = get_db()
    cursor = conn.cursor()
    
    if "dispatched" in text.lower() or "dispatch" in text.lower():
        cursor.execute("SELECT SUM(qty_out_kg) FROM events WHERE stage = 'dispatch'")
        result = cursor.fetchone()[0] or 0
        conn.close()
        return {
            "success": True,
            "message": f"Total material dispatched: {result} kg",
            "data": {"total_dispatched_kg": result}
        }
    
    if "loss" in text.lower() or "losses" in text.lower():
        cursor.execute("""
            SELECT batch_id, 
                   SUM(CASE WHEN qty_in_kg IS NOT NULL THEN qty_in_kg ELSE 0 END) as total_in,
                   SUM(CASE WHEN qty_out_kg IS NOT NULL THEN qty_out_kg ELSE 0 END) as total_out
            FROM events 
            WHERE stage IN ('sorting', 'processing')
            GROUP BY batch_id
        """)
        results = cursor.fetchall()
        losses = []
        for r in results:
            loss = (r["total_in"] or 0) - (r["total_out"] or 0)
            if loss > 0:
                losses.append({"batch_id": r["batch_id"], "loss_kg": loss})
        conn.close()
        total_loss = sum(l["loss_kg"] for l in losses)
        return {
            "success": True,
            "message": f"Total processing losses: {total_loss} kg across {len(losses)} batches",
            "data": {"losses": losses, "total_loss_kg": total_loss}
        }
    
    cursor.execute("SELECT batch_id, material_type, status, confidence_score FROM batches")
    batches = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    return {
        "success": True,
        "message": f"Found {len(batches)} batches",
        "data": {"batches": batches}
    }

@app.get("/api/batches")
def list_batches():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT b.batch_id, b.material_type, b.source_vendor, b.collection_date, 
               b.status, b.confidence_score, b.total_input_kg,
               (SELECT COUNT(*) FROM events WHERE batch_id = b.batch_id) as event_count
        FROM batches b
        ORDER BY b.created_at DESC
    """)
    batches = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"batches": batches, "count": len(batches)}

@app.get("/api/batches/{batch_id}")
def get_batch(batch_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM batches WHERE batch_id = ?", (batch_id,))
    batch = cursor.fetchone()
    if not batch:
        conn.close()
        raise HTTPException(status_code=404, detail="Batch not found")
    
    cursor.execute("SELECT * FROM events WHERE batch_id = ? ORDER BY timestamp", (batch_id,))
    events = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    return {"batch": dict(batch), "events": events}

@app.post("/api/events")
def create_event(event: EventCreate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT batch_id FROM batches WHERE batch_id = ?", (event.batch_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Batch not found")
    
    cursor.execute(
        "INSERT INTO events (batch_id, stage, qty_in_kg, qty_out_kg, operator, vendor, buyer, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (event.batch_id, event.stage, event.qty_in_kg, event.qty_out_kg, event.operator, event.vendor, event.buyer, event.notes)
    )
    conn.commit()
    conn.close()
    
    confidence = calculate_confidence(event.batch_id)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE batches SET confidence_score = ? WHERE batch_id = ?", (confidence, event.batch_id))
    conn.commit()
    conn.close()
    
    return {"success": True, "message": f"Event added to batch {event.batch_id}", "confidence_score": confidence}

@app.get("/api/dashboard-data")
def dashboard_data():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT material_type, SUM(total_input_kg) as total FROM batches GROUP BY material_type")
    material_breakdown = [{"material": r["material_type"], "total_kg": r["total"]} for r in cursor.fetchall()]
    
    cursor.execute("""
        SELECT stage, 
               SUM(COALESCE(qty_in_kg, 0)) as qty_in,
               SUM(COALESCE(qty_out_kg, 0)) as qty_out
        FROM events 
        GROUP BY stage
    """)
    stage_flow = []
    for r in cursor.fetchall():
        stage_flow.append({
            "stage": r["stage"],
            "qty_in_kg": r["qty_in"],
            "qty_out_kg": r["qty_out"],
            "loss_kg": (r["qty_in"] or 0) - (r["qty_out"] or 0) if r["qty_out"] else 0
        })
    
    cursor.execute("SELECT COUNT(*) FROM batches")
    total_batches = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(total_input_kg) FROM batches")
    total_input = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT SUM(total_output_kg) FROM batches WHERE status = 'dispatched'")
    total_dispatched = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return {
        "summary": {
            "total_batches": total_batches,
            "total_input_kg": total_input,
            "total_dispatched_kg": total_dispatched,
            "overall_yield_percent": round((total_dispatched / total_input * 100) if total_input > 0 else 0, 1)
        },
        "material_breakdown": material_breakdown,
        "stage_flow": stage_flow
    }

@app.get("/api/insights/{batch_id}")
def get_insights(batch_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM batches WHERE batch_id = ?", (batch_id,))
    batch = cursor.fetchone()
    if not batch:
        conn.close()
        raise HTTPException(status_code=404, detail="Batch not found")
    
    cursor.execute("SELECT * FROM events WHERE batch_id = ? ORDER BY timestamp", (batch_id,))
    events = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    total_in = sum(e.get("qty_in_kg") or 0 for e in events)
    total_out = sum(e.get("qty_out_kg") or 0 for e in events)
    loss = total_in - total_out if total_out > 0 else 0
    loss_percent = round((loss / total_in * 100) if total_in > 0 else 0, 1)
    
    insight = f"Batch {batch_id} ({batch['material_type']}): "
    insight += f"Purchased {total_in}kg from {batch['source_vendor'] or 'Unknown'}. "
    
    if total_out > 0:
        insight += f"After processing, {total_out}kg was dispatched. "
        insight += f"Total loss: {loss}kg ({loss_percent}%). "
        if loss_percent > 20:
            insight += "WARNING: Loss rate is above average (20%)."
        else:
            insight += "Loss rate is within acceptable range."
    else:
        insight += "Processing not yet complete."
    
    return {
        "batch_id": batch_id,
        "insight": insight,
        "metrics": {
            "total_input_kg": total_in,
            "total_output_kg": total_out,
            "loss_kg": loss,
            "loss_percent": loss_percent
        },
        "confidence_score": batch["confidence_score"]
    }

@app.get("/api/vendors")
def list_vendors():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vendors")
    vendors = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"vendors": vendors}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
