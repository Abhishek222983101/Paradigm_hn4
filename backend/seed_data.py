"""
TraceLoop Mock Data Generator
Generates realistic synthetic data for demonstration
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict
import string

from database import (
    init_database, get_connection,
    BatchRepository, TransactionRepository, InsightRepository
)

VENDORS = [
    {"name": "GreenCorp Recyclers", "location": "Mumbai", "materials": "PET,HDPE", "reliability": 0.92},
    {"name": "EcoWaste Solutions", "location": "Delhi", "materials": "PP,LDPE", "reliability": 0.88},
    {"name": "PlasticRevive Ltd", "location": "Bangalore", "materials": "Mixed", "reliability": 0.85},
    {"name": "CleanCycle Inc", "location": "Chennai", "materials": "PET,PP", "reliability": 0.90},
    {"name": "RecycleFirst Pvt", "location": "Hyderabad", "materials": "HDPE,LDPE", "reliability": 0.87},
]

BUYERS = [
    "PlastiCo Industries",
    "GreenPack Solutions", 
    "EcoProducts Ltd",
    "SustainableBrands Inc",
    "CircularMaterials Corp"
]

LOCATIONS = [
    {"id": "WH-MAIN", "name": "Main Warehouse", "type": "storage", "capacity": 50000},
    {"id": "WH-WASH", "name": "Washing Facility", "type": "processing", "capacity": 10000},
    {"id": "WH-SORT", "name": "Sorting Center", "type": "processing", "capacity": 15000},
    {"id": "WH-GRAN", "name": "Granulation Unit", "type": "processing", "capacity": 8000},
    {"id": "WH-DISP", "name": "Dispatch Bay", "type": "dispatch", "capacity": 20000},
]

MATERIALS = ["PET", "HDPE", "PP", "LDPE", "Mixed"]
GRADES = ["A", "B", "C"]

ACTORS = ["Raj Kumar", "Priya Sharma", "Amit Patel", "Suresh Reddy", "Anita Verma"]

def generate_batch_id() -> str:
    return f"B-{random.randint(1000, 9999)}"

def generate_transaction_id(batch_id: str, seq: int) -> str:
    return f"TXN-{batch_id}-{seq:03d}"

def random_date(start_days_ago: int = 90, end_days_ago: int = 0) -> str:
    days_ago = random.randint(end_days_ago, start_days_ago)
    date = datetime.now() - timedelta(days=days_ago)
    return date.strftime("%Y-%m-%d")

def calculate_loss_at_stage(stage: str, input_qty: float, material_quality: str = "A") -> tuple:
    base_loss_rates = {
        "collection": 0.02,
        "segregation": 0.08,
        "baling": 0.02,
        "weighing": 0.00,
        "washing": 0.10,
        "qc_test": 0.03,
        "recycling": 0.12,
        "granulation": 0.05,
        "dispatch": 0.00,
    }
    
    quality_multipliers = {"A": 1.0, "B": 1.3, "C": 1.6}
    
    base_loss = base_loss_rates.get(stage, 0.05)
    multiplier = quality_multipliers.get(material_quality, 1.2)
    
    actual_loss_rate = base_loss * multiplier * random.uniform(0.8, 1.2)
    loss = input_qty * actual_loss_rate
    output = input_qty - loss
    
    return round(output, 2), round(loss, 2)

def seed_database():
    init_database()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM batches")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return
    
    for vendor in VENDORS:
        cursor.execute(
            "INSERT OR IGNORE INTO vendors (name, location, material_types, reliability_score) VALUES (?, ?, ?, ?)",
            (vendor["name"], vendor["location"], vendor["materials"], vendor["reliability"])
        )
    
    for loc in LOCATIONS:
        cursor.execute(
            "INSERT OR IGNORE INTO locations (location_id, name, type, capacity_kg) VALUES (?, ?, ?, ?)",
            (loc["id"], loc["name"], loc["type"], loc["capacity"])
        )
    
    batches_data = []
    
    for i in range(15):
        batch_id = generate_batch_id()
        vendor = random.choice(VENDORS)
        material = random.choice(vendor["materials"].split(","))
        grade = random.choices(GRADES, weights=[0.5, 0.35, 0.15])[0]
        input_qty = random.randint(200, 1000)
        collection_date = random_date(60, 5)
        
        batches_data.append({
            "batch_id": batch_id,
            "material_type": material,
            "grade": grade,
            "vendor": vendor["name"],
            "input_qty": input_qty,
            "collection_date": collection_date,
        })
    
    for batch in batches_data:
        BatchRepository.create(
            batch_id=batch["batch_id"],
            material_type=batch["material_type"],
            source_vendor=batch["vendor"],
            collection_date=batch["collection_date"]
        )
        
        current_qty = batch["input_qty"]
        total_loss = 0
        stages_completed = random.randint(3, 10)
        
        for seq, stage in enumerate(["collection", "segregation", "baling", "washing", "qc_test", "recycling", "granulation", "dispatch"]):
            if seq >= stages_completed:
                break
            
            txn_id = generate_transaction_id(batch["batch_id"], seq + 1)
            actor = random.choice(ACTORS)
            
            status = "APPROVED"
            if stage == "qc_test" and random.random() < 0.1:
                status = "REJECTED"
            
            output_qty, loss = calculate_loss_at_stage(stage, current_qty, batch["grade"])
            
            if stage == "dispatch":
                buyer = random.choice(BUYERS)
                TransactionRepository.create(
                    transaction_id=txn_id,
                    batch_id=batch["batch_id"],
                    stage=stage,
                    qty_in=current_qty,
                    qty_out=current_qty,
                    actor=actor,
                    status=status,
                    buyer=buyer,
                    notes=f"Dispatched to {buyer}"
                )
            elif stage == "collection":
                TransactionRepository.create(
                    transaction_id=txn_id,
                    batch_id=batch["batch_id"],
                    stage=stage,
                    qty_in=current_qty,
                    qty_out=current_qty,
                    actor=actor,
                    status=status,
                    vendor=batch["vendor"],
                    from_location="FIELD",
                    to_location="WH-MAIN",
                    notes=f"Collected {current_qty}kg {batch['material_type']} from {batch['vendor']}"
                )
            else:
                TransactionRepository.create(
                    transaction_id=txn_id,
                    batch_id=batch["batch_id"],
                    stage=stage,
                    qty_in=current_qty,
                    qty_out=output_qty,
                    actor=actor,
                    status=status,
                    notes=f"{stage.title()}: {current_qty}kg -> {output_qty}kg (loss: {loss}kg)"
                )
            
            total_loss += loss
            current_qty = output_qty
        
        final_yield = round((current_qty / batch["input_qty"]) * 100, 1)
        avg_yield = 75
        
        if final_yield < avg_yield - 10:
            InsightRepository.create(
                batch_id=batch["batch_id"],
                insight_type="low_yield",
                content=f"Batch {batch['batch_id']} has {final_yield}% yield, which is {round(avg_yield - final_yield, 1)}% below average. Check {batch['material_type']} quality.",
                severity="warning"
            )
        elif final_yield > avg_yield + 5:
            InsightRepository.create(
                batch_id=batch["batch_id"],
                insight_type="high_yield",
                content=f"Excellent! Batch {batch['batch_id']} achieved {final_yield}% yield, above average performance.",
                severity="success"
            )
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE batches 
            SET total_input_kg = ?, total_output_kg = ?, confidence_score = ?
            WHERE batch_id = ?
        """, (batch["input_qty"], current_qty, random.randint(60, 100), batch["batch_id"]))
        conn.commit()
    
    conn.close()
    print("Database seeded successfully!")

if __name__ == "__main__":
    seed_database()
