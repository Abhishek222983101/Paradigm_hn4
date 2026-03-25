"""
TraceLoop Seed Data Generator
Populates database with realistic mock data for recycling workflows
"""

import random
from datetime import datetime, timedelta
from backend.database import (
    init_database, get_connection, BatchRepository, 
    TransactionRepository, InsightRepository
)

VENDORS = [
    {"name": "GreenCorp Recycling", "location": "Mumbai", "materials": "PET,HDPE"},
    {"name": "EcoWaste Solutions", "location": "Delhi", "materials": "PP,LDPE"},
    {"name": "RecycleFirst Ltd", "location": "Bangalore", "materials": "Mixed"},
    {"name": "CleanPlast Industries", "location": "Chennai", "materials": "PET,PP"},
    {"name": "Urban Waste Co", "location": "Hyderabad", "materials": "HDPE,LDPE"},
]

BUYERS = [
    "PlastiCo Manufacturing",
    "GreenPack Industries", 
    "EcoProducts Ltd",
    "Sustainable Solutions Inc",
    "Circular Plastics Corp"
]

LOCATIONS = [
    {"id": "WH-COLL", "name": "Collection Warehouse", "type": "warehouse"},
    {"id": "WH-SEG", "name": "Segregation Unit", "type": "processing"},
    {"id": "WH-WASH", "name": "Washing Facility", "type": "processing"},
    {"id": "WH-REC", "name": "Recycling Plant", "type": "processing"},
    {"id": "WH-DISP", "name": "Dispatch Center", "type": "warehouse"},
]

MATERIALS = ["PET", "HDPE", "PP", "LDPE", "Mixed"]

ACTORS = ["Raj Kumar", "Amit Sharma", "Priya Patel", "Suresh Reddy", "Neha Gupta"]

def generate_batch_id(index: int) -> str:
    return f"B-{2800 + index}"

def generate_transaction_id(batch_id: str, stage: str, seq: int) -> str:
    stage_codes = {
        "collection": "COL", "segregation": "SEG", "baling": "BAL",
        "weighing": "WGH", "washing": "WSH", "qc_test": "QCT",
        "recycling": "REC", "granulation": "GRN", "dispatch": "DSP",
        "receive": "RCV"
    }
    code = stage_codes.get(stage, "TRX")
    return f"T-{batch_id[2:]}-{code}-{seq:03d}"

def random_date(days_back: int = 90) -> str:
    start = datetime.now() - timedelta(days=days_back)
    random_days = random.randint(0, days_back)
    return (start + timedelta(days=random_days)).strftime("%Y-%m-%d")

def calculate_stage_loss(stage: str, input_qty: float, is_dirty: bool = False) -> float:
    loss_rates = {
        "collection": 0,
        "segregation": random.uniform(0.05, 0.15) if is_dirty else random.uniform(0.02, 0.08),
        "baling": random.uniform(0.01, 0.03),
        "weighing": 0,
        "washing": random.uniform(0.05, 0.12),
        "qc_test": random.uniform(0.01, 0.05),
        "recycling": random.uniform(0.08, 0.18),
        "granulation": random.uniform(0.02, 0.06),
        "dispatch": 0,
    }
    loss_rate = loss_rates.get(stage, 0.02)
    return input_qty * loss_rate

def seed_database():
    print("Initializing database...")
    init_database()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM batches")
    if cursor.fetchone()[0] > 0:
        print("Database already seeded. Skipping...")
        conn.close()
        return
    
    print("Seeding vendors...")
    for vendor in VENDORS:
        cursor.execute(
            "INSERT INTO vendors (name, location, material_types) VALUES (?, ?, ?)",
            (vendor["name"], vendor["location"], vendor["materials"])
        )
    
    print("Seeding locations...")
    for loc in LOCATIONS:
        cursor.execute(
            "INSERT INTO locations (location_id, name, type) VALUES (?, ?, ?)",
            (loc["id"], loc["name"], loc["type"])
        )
    
    conn.commit()
    
    print("Generating batch data...")
    num_batches = 25
    
    for i in range(num_batches):
        batch_id = generate_batch_id(i)
        material = random.choice(MATERIALS)
        vendor = random.choice(VENDORS)
        collection_date = random_date(60)
        initial_qty = random.randint(200, 1000) * 10
        
        is_dirty = random.random() < 0.3
        
        BatchRepository.create(
            batch_id=batch_id,
            material_type=material,
            source_vendor=vendor["name"],
            collection_date=collection_date
        )
        
        stages = ["collection", "segregation", "baling", "weighing", 
                  "washing", "qc_test", "recycling", "granulation", "dispatch"]
        
        current_qty = initial_qty
        current_location = "WH-COLL"
        
        for stage_idx, stage in enumerate(stages):
            if random.random() < 0.1:
                continue
            
            qty_in = current_qty
            loss = calculate_stage_loss(stage, qty_in, is_dirty)
            qty_out = max(qty_in - loss, 0)
            
            status = "APPROVED"
            if stage == "qc_test" and random.random() < 0.08:
                status = "REJECTED"
            
            next_location = current_location
            if stage_idx < len(stages) - 1:
                location_map = {
                    "collection": "WH-COLL",
                    "segregation": "WH-SEG",
                    "baling": "WH-SEG",
                    "weighing": "WH-SEG",
                    "washing": "WH-WASH",
                    "qc_test": "WH-WASH",
                    "recycling": "WH-REC",
                    "granulation": "WH-REC",
                    "dispatch": "WH-DISP",
                }
                next_location = location_map.get(stage, current_location)
            
            transaction_id = generate_transaction_id(batch_id, stage, stage_idx)
            
            TransactionRepository.create(
                transaction_id=transaction_id,
                batch_id=batch_id,
                stage=stage,
                qty_in=round(qty_in, 2),
                qty_out=round(qty_out, 2) if stage not in ["qc_test", "dispatch"] else None,
                actor=random.choice(ACTORS),
                status=status,
                from_location=current_location,
                to_location=next_location,
                vendor=vendor["name"] if stage == "collection" else None,
                buyer=random.choice(BUYERS) if stage == "dispatch" else None,
                notes=f"{stage.capitalize()} completed" + (" - High contamination" if is_dirty and stage == "segregation" else "")
            )
            
            current_qty = qty_out
            current_location = next_location
            
            if status == "REJECTED":
                InsightRepository.create(
                    batch_id=batch_id,
                    insight_type="anomaly",
                    content=f"QC Test failed at {stage}. Material requires rework or downgrade.",
                    severity="warning"
                )
                break
        
        final_qty = current_qty
        total_loss = initial_qty - final_qty
        loss_percent = round((total_loss / initial_qty) * 100, 1)
        
        if loss_percent > 30:
            InsightRepository.create(
                batch_id=batch_id,
                insight_type="high_loss",
                content=f"Batch has {loss_percent}% total loss rate, which is above the 25% threshold. Check contamination levels.",
                severity="warning"
            )
        
        cursor.execute(
            "UPDATE batches SET total_input_kg = ?, total_output_kg = ? WHERE batch_id = ?",
            (initial_qty, final_qty, batch_id)
        )
        
        confidence = BatchRepository.calculate_confidence(batch_id)
        cursor.execute(
            "UPDATE batches SET confidence_score = ? WHERE batch_id = ?",
            (confidence, batch_id)
        )
    
    conn.commit()
    conn.close()
    
    print(f"Seeding complete! Generated {num_batches} batches with transactions.")

if __name__ == "__main__":
    seed_database()
