"""
TraceLoop Database Layer
SQLite database with all tables for material traceability
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

DB_PATH = "traceloop.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS batches (
            batch_id TEXT PRIMARY KEY,
            parent_batch_id TEXT,
            material_type TEXT NOT NULL,
            grade TEXT DEFAULT 'A',
            source_vendor TEXT,
            current_location TEXT,
            status TEXT DEFAULT 'active',
            collection_date TEXT,
            total_input_kg REAL DEFAULT 0,
            total_output_kg REAL DEFAULT 0,
            confidence_score INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id TEXT PRIMARY KEY,
            batch_id TEXT NOT NULL,
            stage TEXT NOT NULL,
            transaction_type TEXT,
            qty_in REAL,
            unit_in TEXT DEFAULT 'KG',
            qty_out REAL,
            unit_out TEXT DEFAULT 'KG',
            actor TEXT,
            from_location TEXT,
            to_location TEXT,
            vendor TEXT,
            buyer TEXT,
            status TEXT DEFAULT 'APPROVED',
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
            material_types TEXT,
            reliability_score REAL DEFAULT 0.8
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            location_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT,
            capacity_kg REAL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS insights (
            insight_id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id TEXT,
            insight_type TEXT,
            severity TEXT DEFAULT 'info',
            content TEXT,
            generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (batch_id) REFERENCES batches(batch_id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_input TEXT,
            intent_detected TEXT,
            entities_extracted TEXT,
            response TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

class BatchRepository:
    
    @staticmethod
    def create(batch_id: str, material_type: str, source_vendor: str = None, 
               collection_date: str = None, parent_batch_id: str = None) -> Dict:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO batches (batch_id, material_type, source_vendor, collection_date, parent_batch_id)
            VALUES (?, ?, ?, ?, ?)
        """, (batch_id, material_type, source_vendor, collection_date or datetime.now().strftime("%Y-%m-%d"), parent_batch_id))
        conn.commit()
        conn.close()
        return {"batch_id": batch_id, "material_type": material_type, "status": "created"}
    
    @staticmethod
    def get(batch_id: str) -> Optional[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM batches WHERE batch_id = ?", (batch_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    @staticmethod
    def get_all(limit: int = 50) -> List[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM batches ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def update_status(batch_id: str, status: str):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE batches SET status = ?, updated_at = ? WHERE batch_id = ?
        """, (status, datetime.now().isoformat(), batch_id))
        conn.commit()
        conn.close()
    
    @staticmethod
    def calculate_confidence(batch_id: str) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT stage) FROM transactions WHERE batch_id = ?", (batch_id,))
        stages_complete = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE batch_id = ? AND status = 'APPROVED'", (batch_id,))
        approved_count = cursor.fetchone()[0]
        conn.close()
        
        total_stages = 13
        stage_score = (stages_complete / total_stages) * 70
        approval_score = (approved_count / max(stages_complete, 1)) * 30
        return min(int(stage_score + approval_score), 100)

class TransactionRepository:
    
    @staticmethod
    def create(transaction_id: str, batch_id: str, stage: str, 
               qty_in: float = None, qty_out: float = None, 
               actor: str = None, status: str = "APPROVED",
               from_location: str = None, to_location: str = None,
               vendor: str = None, buyer: str = None, notes: str = None) -> Dict:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transactions 
            (transaction_id, batch_id, stage, qty_in, qty_out, actor, status, from_location, to_location, vendor, buyer, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (transaction_id, batch_id, stage, qty_in, qty_out, actor, status, from_location, to_location, vendor, buyer, notes))
        conn.commit()
        conn.close()
        
        BatchRepository.calculate_confidence(batch_id)
        return {"transaction_id": transaction_id, "batch_id": batch_id, "stage": stage}
    
    @staticmethod
    def get_by_batch(batch_id: str) -> List[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transactions WHERE batch_id = ? ORDER BY timestamp", (batch_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def get_by_stage(stage: str, limit: int = 100) -> List[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transactions WHERE stage = ? ORDER BY timestamp DESC LIMIT ?", (stage, limit))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

class InsightRepository:
    
    @staticmethod
    def create(batch_id: str, insight_type: str, content: str, severity: str = "info"):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO insights (batch_id, insight_type, content, severity)
            VALUES (?, ?, ?, ?)
        """, (batch_id, insight_type, content, severity))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_by_batch(batch_id: str) -> List[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM insights WHERE batch_id = ? ORDER BY generated_at DESC", (batch_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

class ChatHistoryRepository:
    
    @staticmethod
    def log(user_input: str, intent: str, entities: Dict, response: str):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chat_history (user_input, intent_detected, entities_extracted, response)
            VALUES (?, ?, ?, ?)
        """, (user_input, intent, json.dumps(entities), response))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_recent(limit: int = 20) -> List[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM chat_history ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
