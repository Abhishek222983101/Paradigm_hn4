"""
TraceLoop Main API Application
FastAPI backend for Intelligent Traceability Management
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uvicorn

from backend.database import (
    init_database, get_connection, 
    BatchRepository, TransactionRepository, 
    InsightRepository, ChatHistoryRepository
)
from backend.nlp_engine import NLPEngine, QueryParser
from backend.insights import InsightEngine
from backend.seed_data import seed_database
from backend.ai_service import ai_service
from backend.anomaly_detector import AnomalyDetector

app = FastAPI(
    title="TraceLoop API",
    description="Intelligent Traceability Management for Recycled Materials",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

nlp_engine = NLPEngine()
query_parser = QueryParser()

class ChatRequest(BaseModel):
    text: str
    batch_id: Optional[str] = None

class TransactionRequest(BaseModel):
    batch_id: str
    stage: str
    qty_in: Optional[float] = None
    qty_out: Optional[float] = None
    actor: Optional[str] = None
    status: Optional[str] = "APPROVED"
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    vendor: Optional[str] = None
    buyer: Optional[str] = None
    notes: Optional[str] = None

class BatchRequest(BaseModel):
    material_type: str
    source_vendor: Optional[str] = None
    collection_date: Optional[str] = None
    parent_batch_id: Optional[str] = None

@app.on_event("startup")
def startup():
    init_database()
    seed_database()

@app.get("/")
def root():
    return {
        "message": "TraceLoop API",
        "description": "Intelligent Traceability Management for Recycled Materials",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "TraceLoop", "timestamp": datetime.now().isoformat()}

@app.post("/api/chat")
def process_chat(request: ChatRequest):
    parsed = nlp_engine.parse(request.text)
    
    if parsed["intent"] == "query":
        return handle_conversational_query(request.text, parsed)
    
    if parsed["intent"] == "help":
        return {
            "success": True,
            "message": "I can help you with: \n"
                      "- 'Purchased 300kg PET from GreenCorp yesterday'\n"
                      "- 'Sorted batch B-101, 450kg output'\n"
                      "- 'Dispatched 200kg to PlastiCo'\n"
                      "- 'Show all batches'\n"
                      "- 'How much material was dispatched last week?'\n"
                      "- 'Show losses for batch B-101'"
        }
    
    if parsed["intent"] == "unknown":
        response = "I couldn't understand that. Try: 'Purchased 300kg PET from Vendor A' or 'Show batches'"
        ChatHistoryRepository.log(request.text, "unknown", parsed["entities"], response)
        return {"success": False, "message": response, "parsed": parsed}
    
    result = create_transaction_from_parsed(parsed, request.batch_id)
    
    response = nlp_engine.generate_response(parsed, result)
    ChatHistoryRepository.log(request.text, parsed["intent"], parsed["entities"], response)
    
    return {
        "success": True,
        "message": response,
        "batch_id": result.get("batch_id"),
        "transaction_id": result.get("transaction_id"),
        "parsed": parsed
    }

def create_transaction_from_parsed(parsed: Dict, existing_batch_id: str = None) -> Dict:
    entities = parsed["entities"]
    intent = parsed["intent"]
    
    batch_id = existing_batch_id or entities.get("batch_id")
    
    if not batch_id:
        import random
        batch_id = f"B-{random.randint(2800, 9999)}"
        BatchRepository.create(
            batch_id=batch_id,
            material_type=entities.get("material_type", "Mixed"),
            source_vendor=entities.get("vendor"),
            collection_date=entities.get("date")
        )
    
    import random
    transaction_id = f"T-{batch_id[2:]}-{intent[:3].upper()}-{random.randint(100,999)}"
    
    stage_map = {
        "purchase": "collection",
        "collection": "collection",
        "segregation": "segregation",
        "baling": "baling",
        "washing": "washing",
        "qc_test": "qc_test",
        "recycling": "recycling",
        "granulation": "granulation",
        "dispatch": "dispatch",
        "receive": "receive"
    }
    
    stage = stage_map.get(intent, intent)
    qty = entities.get("quantity_kg")
    
    result = TransactionRepository.create(
        transaction_id=transaction_id,
        batch_id=batch_id,
        stage=stage,
        qty_in=qty,
        qty_out=None,
        vendor=entities.get("vendor"),
        buyer=entities.get("buyer"),
        status=entities.get("status", "APPROVED"),
        notes=parsed["original_text"]
    )
    
    result["batch_id"] = batch_id
    return result

def handle_conversational_query(text: str, parsed: Dict) -> Dict:
    query = query_parser.parse_query(text)
    conn = get_connection()
    cursor = conn.cursor()
    
    if query["query_type"] == "dispatch_summary":
        cursor.execute("""
            SELECT SUM(qty_in) as total, COUNT(*) as count 
            FROM transactions 
            WHERE stage = 'dispatch' AND status = 'APPROVED'
        """)
        result = cursor.fetchone()
        conn.close()
        total = result[0] or 0
        count = result[1] or 0
        return {
            "success": True,
            "message": f"Total dispatched: {total}kg across {count} transactions",
            "data": {"total_kg": total, "transaction_count": count}
        }
    
    if query["query_type"] == "loss_analysis":
        cursor.execute("""
            SELECT batch_id, 
                   SUM(COALESCE(qty_in, 0)) as total_in,
                   SUM(COALESCE(qty_out, 0)) as total_out
            FROM transactions 
            WHERE stage IN ('segregation', 'washing', 'recycling')
            GROUP BY batch_id
        """)
        results = cursor.fetchall()
        conn.close()
        
        losses = []
        total_loss = 0
        for r in results:
            loss = (r[1] or 0) - (r[2] or 0)
            if loss > 0:
                loss_pct = round((loss / r[1]) * 100, 1) if r[1] > 0 else 0
                losses.append({"batch_id": r[0], "loss_kg": round(loss, 2), "loss_percent": loss_pct})
                total_loss += loss
        
        return {
            "success": True,
            "message": f"Total processing losses: {round(total_loss, 2)}kg across {len(losses)} batches",
            "data": {"losses": losses, "total_loss_kg": round(total_loss, 2)}
        }
    
    if query["query_type"] == "batch_list":
        filters = query.get("filters", {})
        sql = "SELECT batch_id, material_type, status, confidence_score, total_input_kg FROM batches WHERE 1=1"
        params = []
        
        if "material_type" in filters:
            sql += " AND material_type = ?"
            params.append(filters["material_type"])
        
        cursor.execute(sql, params)
        batches = [dict(r) for r in cursor.fetchall()]
        conn.close()
        
        return {
            "success": True,
            "message": f"Found {len(batches)} batches",
            "data": {"batches": batches}
        }
    
    cursor.execute("SELECT batch_id, material_type, status, confidence_score FROM batches LIMIT 20")
    batches = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    return {
        "success": True,
        "message": f"Found {len(batches)} batches",
        "data": {"batches": batches}
    }

@app.get("/api/batches")
def list_batches(
    material_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, le=100)
):
    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT b.batch_id, b.material_type, b.source_vendor, b.collection_date,
               b.status, b.confidence_score, b.total_input_kg, b.total_output_kg,
               (SELECT COUNT(*) FROM transactions WHERE batch_id = b.batch_id) as transaction_count
        FROM batches b WHERE 1=1
    """
    params = []
    
    if material_type:
        query += " AND b.material_type = ?"
        params.append(material_type)
    if status:
        query += " AND b.status = ?"
        params.append(status)
    
    query += " ORDER BY b.created_at DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    batches = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    return {"batches": batches, "count": len(batches)}

@app.get("/api/batches/{batch_id}")
def get_batch_detail(batch_id: str):
    batch = BatchRepository.get(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    transactions = TransactionRepository.get_by_batch(batch_id)
    insights = InsightRepository.get_by_batch(batch_id)
    
    conn = get_connection()
    insight_engine = InsightEngine(conn)
    analysis = insight_engine.analyze_batch(batch_id)
    conn.close()
    
    return {
        "batch": batch,
        "transactions": transactions,
        "insights": insights,
        "analysis": analysis
    }

@app.post("/api/batches")
def create_batch(request: BatchRequest):
    import random
    batch_id = f"B-{random.randint(2800, 9999)}"
    
    result = BatchRepository.create(
        batch_id=batch_id,
        material_type=request.material_type,
        source_vendor=request.source_vendor,
        collection_date=request.collection_date,
        parent_batch_id=request.parent_batch_id
    )
    
    return {"success": True, "batch_id": batch_id, "batch": result}

@app.post("/api/transactions")
def create_transaction(request: TransactionRequest):
    batch = BatchRepository.get(request.batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    import random
    transaction_id = f"T-{request.batch_id[2:]}-{request.stage[:3].upper()}-{random.randint(100,999)}"
    
    result = TransactionRepository.create(
        transaction_id=transaction_id,
        batch_id=request.batch_id,
        stage=request.stage,
        qty_in=request.qty_in,
        qty_out=request.qty_out,
        actor=request.actor,
        status=request.status,
        from_location=request.from_location,
        to_location=request.to_location,
        vendor=request.vendor,
        buyer=request.buyer,
        notes=request.notes
    )
    
    return {"success": True, "transaction_id": transaction_id, "transaction": result}

@app.get("/api/dashboard")
def get_dashboard_data():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM batches")
    total_batches = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(total_input_kg) FROM batches")
    total_input = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT SUM(total_output_kg) FROM batches WHERE status != 'cancelled'")
    total_output = cursor.fetchone()[0] or 0
    
    cursor.execute("""
        SELECT material_type, SUM(total_input_kg) as total 
        FROM batches 
        GROUP BY material_type
    """)
    material_breakdown = [{"material": r[0], "total_kg": r[1]} for r in cursor.fetchall()]
    
    cursor.execute("""
        SELECT stage, 
               SUM(COALESCE(qty_in, 0)) as qty_in,
               SUM(COALESCE(qty_out, 0)) as qty_out
        FROM transactions 
        GROUP BY stage
    """)
    stage_flow = []
    for r in cursor.fetchall():
        stage_flow.append({
            "stage": r[0],
            "qty_in": r[1],
            "qty_out": r[2],
            "loss": r[1] - r[2] if r[2] else 0
        })
    
    cursor.execute("""
        SELECT status, COUNT(*) as count 
        FROM transactions 
        GROUP BY status
    """)
    status_summary = {r[0]: r[1] for r in cursor.fetchall()}
    
    conn.close()
    
    yield_pct = round((total_output / total_input * 100), 1) if total_input > 0 else 0
    
    return {
        "summary": {
            "total_batches": total_batches,
            "total_input_kg": round(total_input, 2),
            "total_output_kg": round(total_output, 2),
            "overall_yield_percent": yield_pct,
            "total_loss_kg": round(total_input - total_output, 2)
        },
        "material_breakdown": material_breakdown,
        "stage_flow": stage_flow,
        "status_summary": status_summary
    }

@app.get("/api/insights/{batch_id}")
def get_batch_insights(batch_id: str):
    batch = BatchRepository.get(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    conn = get_connection()
    insight_engine = InsightEngine(conn)
    analysis = insight_engine.analyze_batch(batch_id)
    comparison = insight_engine.compare_with_average(analysis)
    conn.close()
    
    return {
        "batch_id": batch_id,
        "analysis": analysis,
        "comparison": comparison
    }

@app.get("/api/vendors")
def list_vendors():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vendors")
    vendors = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"vendors": vendors}

@app.get("/api/locations")
def list_locations():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM locations")
    locations = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"locations": locations}

@app.get("/api/chat-history")
def get_chat_history(limit: int = 20):
    history = ChatHistoryRepository.get_recent(limit)
    return {"history": history}

@app.post("/api/ai/classify")
async def ai_classify_intent(request: ChatRequest):
    result = await ai_service.classify_intent(request.text)
    return {"text": request.text, "classification": result}

@app.post("/api/ai/extract")
async def ai_extract_entities(request: ChatRequest):
    entities = await ai_service.extract_entities(request.text)
    return {"text": request.text, "entities": entities}

@app.get("/api/ai/insight/{batch_id}")
async def ai_generate_insight(batch_id: str):
    batch = BatchRepository.get(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    batch_dict = dict(batch)
    insight = await ai_service.generate_insight(batch_dict)
    
    return {
        "batch_id": batch_id,
        "ai_insight": insight,
        "generated_at": datetime.now().isoformat()
    }

@app.get("/api/ai/suggest")
async def ai_suggest_action():
    dashboard = get_dashboard_data()
    
    context = {
        "total_batches": dashboard["summary"]["total_batches"],
        "average_yield": dashboard["summary"]["overall_yield_percent"],
        "high_loss_count": sum(1 for s in dashboard["stage_flow"] if s.get("loss", 0) > 100),
        "pending_qc": dashboard["status_summary"].get("PENDING", 0)
    }
    
    suggestion = await ai_service.suggest_action(context)
    
    return {
        "context": context,
        "suggestion": suggestion
    }

@app.get("/api/anomalies")
def detect_anomalies(batch_id: Optional[str] = None):
    conn = get_connection()
    detector = AnomalyDetector(conn)
    anomalies = detector.detect_all(batch_id)
    stats = detector.get_statistics()
    conn.close()
    
    return {
        "anomalies": [
            {
                "anomaly_id": a.anomaly_id,
                "type": a.anomaly_type.value,
                "severity": a.severity.value,
                "batch_id": a.batch_id,
                "stage": a.stage,
                "message": a.message,
                "details": a.details,
                "detected_at": a.detected_at,
                "recommendation": a.recommendation
            }
            for a in anomalies
        ],
        "statistics": stats
    }

@app.get("/api/anomalies/batch/{batch_id}")
def detect_batch_anomalies(batch_id: str):
    batch = BatchRepository.get(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    conn = get_connection()
    detector = AnomalyDetector(conn)
    anomalies = detector.detect_all(batch_id)
    stats = detector.get_statistics()
    conn.close()
    
    return {
        "batch_id": batch_id,
        "anomalies": [
            {
                "anomaly_id": a.anomaly_id,
                "type": a.anomaly_type.value,
                "severity": a.severity.value,
                "stage": a.stage,
                "message": a.message,
                "details": a.details,
                "detected_at": a.detected_at,
                "recommendation": a.recommendation
            }
            for a in anomalies
        ],
        "statistics": stats
    }

@app.get("/api/anomalies/recommendations")
def get_anomaly_recommendations():
    conn = get_connection()
    detector = AnomalyDetector(conn)
    detector.detect_all()
    recommendations = detector.get_recommendations()
    conn.close()
    
    return {"recommendations": recommendations}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
