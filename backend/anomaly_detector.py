"""
TraceLoop Anomaly Detection System
Real-time detection of anomalies in material traceability data
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import statistics

class AnomalyType(Enum):
    HIGH_LOSS = "high_loss"
    UNUSUAL_YIELD = "unusual_yield"
    MISSING_STAGES = "missing_stages"
    REJECTED_CONTINUE = "rejected_continue"
    DATA_GAP = "data_gap"
    VENDOR_ANOMALY = "vendor_anomaly"
    TIMING_ANOMALY = "timing_anomaly"

class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class Anomaly:
    anomaly_id: str
    anomaly_type: AnomalyType
    severity: Severity
    batch_id: str
    stage: Optional[str]
    message: str
    details: Dict
    detected_at: str
    recommendation: str

class AnomalyDetector:
    
    LOSS_THRESHOLDS = {
        "segregation": {"warning": 0.10, "critical": 0.15},
        "washing": {"warning": 0.12, "critical": 0.18},
        "recycling": {"warning": 0.18, "critical": 0.25},
        "granulation": {"warning": 0.05, "critical": 0.08},
        "overall": {"warning": 0.25, "critical": 0.35}
    }
    
    EXPECTED_STAGES = [
        "collection", "segregation", "baling", "weighing",
        "washing", "qc_test", "recycling", "granulation", "dispatch"
    ]
    
    def __init__(self, db_connection):
        self.conn = db_connection
        self.anomalies = []
    
    def detect_all(self, batch_id: str = None) -> List[Anomaly]:
        self.anomalies = []
        
        if batch_id:
            self._analyze_batch(batch_id)
        else:
            cursor = self.conn.cursor()
            cursor.execute("SELECT batch_id FROM batches WHERE status != 'cancelled'")
            batches = cursor.fetchall()
            
            for batch in batches:
                self._analyze_batch(batch[0])
        
        return self.anomalies
    
    def _analyze_batch(self, batch_id: str):
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT * FROM batches WHERE batch_id = ?", (batch_id,))
        batch = cursor.fetchone()
        if not batch:
            return
        
        batch_dict = dict(batch)
        
        cursor.execute("""
            SELECT * FROM transactions 
            WHERE batch_id = ? 
            ORDER BY timestamp
        """, (batch_id,))
        transactions = [dict(t) for t in cursor.fetchall()]
        
        self._check_loss_anomalies(batch_dict, transactions)
        self._check_stage_sequence(batch_dict, transactions)
        self._check_rejected_continue(batch_dict, transactions)
        self._check_data_gaps(batch_dict, transactions)
        self._check_timing_anomalies(batch_dict, transactions)
    
    def _check_loss_anomalies(self, batch: Dict, transactions: List[Dict]):
        for tx in transactions:
            stage = tx.get("stage", "")
            qty_in = tx.get("qty_in") or 0
            qty_out = tx.get("qty_out")
            
            if qty_in <= 0 or qty_out is None:
                continue
            
            loss_rate = (qty_in - qty_out) / qty_in
            
            if stage in self.LOSS_THRESHOLDS:
                thresholds = self.LOSS_THRESHOLDS[stage]
                
                if loss_rate > thresholds["critical"]:
                    self._add_anomaly(
                        batch_id=batch["batch_id"],
                        anomaly_type=AnomalyType.HIGH_LOSS,
                        severity=Severity.CRITICAL,
                        stage=stage,
                        message=f"Critical loss rate of {loss_rate*100:.1f}% at {stage} stage",
                        details={
                            "loss_rate": round(loss_rate * 100, 2),
                            "qty_in": qty_in,
                            "qty_out": qty_out,
                            "loss_kg": qty_in - qty_out,
                            "threshold": thresholds["critical"] * 100
                        },
                        recommendation=f"Investigate {stage} process for contamination or equipment issues"
                    )
                elif loss_rate > thresholds["warning"]:
                    self._add_anomaly(
                        batch_id=batch["batch_id"],
                        anomaly_type=AnomalyType.HIGH_LOSS,
                        severity=Severity.MEDIUM,
                        stage=stage,
                        message=f"High loss rate of {loss_rate*100:.1f}% at {stage} stage",
                        details={
                            "loss_rate": round(loss_rate * 100, 2),
                            "qty_in": qty_in,
                            "qty_out": qty_out,
                            "loss_kg": qty_in - qty_out,
                            "threshold": thresholds["warning"] * 100
                        },
                        recommendation=f"Monitor {stage} stage for recurring issues"
                    )
        
        total_input = batch.get("total_input_kg") or 0
        total_output = batch.get("total_output_kg") or 0
        
        if total_input > 0 and total_output > 0:
            overall_loss = (total_input - total_output) / total_input
            
            if overall_loss > self.LOSS_THRESHOLDS["overall"]["critical"]:
                self._add_anomaly(
                    batch_id=batch["batch_id"],
                    anomaly_type=AnomalyType.UNUSUAL_YIELD,
                    severity=Severity.CRITICAL,
                    stage=None,
                    message=f"Critical overall loss of {overall_loss*100:.1f}% for batch",
                    details={
                        "total_loss_rate": round(overall_loss * 100, 2),
                        "total_input_kg": total_input,
                        "total_output_kg": total_output
                    },
                    recommendation="Review entire batch lifecycle for systemic issues"
                )
    
    def _check_stage_sequence(self, batch: Dict, transactions: List[Dict]):
        completed_stages = set(tx["stage"] for tx in transactions if tx["status"] == "APPROVED")
        
        missing_stages = []
        for i, stage in enumerate(self.EXPECTED_STAGES):
            if stage not in completed_stages:
                prev_stages_complete = all(
                    self.EXPECTED_STAGES[j] in completed_stages 
                    for j in range(i)
                )
                if prev_stages_complete and i < len(self.EXPECTED_STAGES) - 2:
                    missing_stages.append(stage)
        
        if len(missing_stages) > 1:
            self._add_anomaly(
                batch_id=batch["batch_id"],
                anomaly_type=AnomalyType.MISSING_STAGES,
                severity=Severity.MEDIUM,
                stage=None,
                message=f"Missing stages detected: {', '.join(missing_stages)}",
                details={"missing_stages": missing_stages},
                recommendation="Complete all required stages for full traceability"
            )
    
    def _check_rejected_continue(self, batch: Dict, transactions: List[Dict]):
        rejected_at = None
        rejected_stage = None
        
        for tx in transactions:
            if tx["status"] == "REJECTED":
                rejected_at = tx["timestamp"]
                rejected_stage = tx["stage"]
            elif rejected_at and tx["status"] == "APPROVED":
                if tx["timestamp"] > rejected_at:
                    self._add_anomaly(
                        batch_id=batch["batch_id"],
                        anomaly_type=AnomalyType.REJECTED_CONTINUE,
                        severity=Severity.HIGH,
                        stage=tx["stage"],
                        message=f"Processing continued after rejection at {rejected_stage}",
                        details={
                            "rejected_stage": rejected_stage,
                            "rejected_at": rejected_at,
                            "continued_stage": tx["stage"],
                            "continued_at": tx["timestamp"]
                        },
                        recommendation="Review quality control process - material should be reworked or rejected"
                    )
                    break
    
    def _check_data_gaps(self, batch: Dict, transactions: List[Dict]):
        confidence = batch.get("confidence_score", 0)
        
        if confidence < 50:
            self._add_anomaly(
                batch_id=batch["batch_id"],
                anomaly_type=AnomalyType.DATA_GAP,
                severity=Severity.LOW,
                stage=None,
                message=f"Low data confidence score: {confidence}%",
                details={
                    "confidence_score": confidence,
                    "transaction_count": len(transactions)
                },
                recommendation="Complete missing transaction records to improve traceability"
            )
    
    def _check_timing_anomalies(self, batch: Dict, transactions: List[Dict]):
        if len(transactions) < 2:
            return
        
        timestamps = []
        for tx in transactions:
            if tx.get("timestamp"):
                try:
                    ts = datetime.fromisoformat(tx["timestamp"].replace("Z", "+00:00"))
                    timestamps.append(ts)
                except:
                    pass
        
        if len(timestamps) < 2:
            return
        
        timestamps.sort()
        
        for i in range(1, len(timestamps)):
            time_diff = (timestamps[i] - timestamps[i-1]).total_seconds() / 3600
            
            if time_diff > 72:
                self._add_anomaly(
                    batch_id=batch["batch_id"],
                    anomaly_type=AnomalyType.TIMING_ANOMALY,
                    severity=Severity.LOW,
                    stage=transactions[i]["stage"],
                    message=f"Large time gap of {time_diff:.1f} hours between stages",
                    details={
                        "gap_hours": round(time_diff, 1),
                        "from_stage": transactions[i-1]["stage"],
                        "to_stage": transactions[i]["stage"]
                    },
                    recommendation="Investigate delay in processing"
                )
    
    def _add_anomaly(self, batch_id: str, anomaly_type: AnomalyType, severity: Severity,
                     stage: Optional[str], message: str, details: Dict, recommendation: str):
        import random
        anomaly_id = f"AN-{random.randint(1000, 9999)}"
        
        anomaly = Anomaly(
            anomaly_id=anomaly_id,
            anomaly_type=anomaly_type,
            severity=severity,
            batch_id=batch_id,
            stage=stage,
            message=message,
            details=details,
            detected_at=datetime.now().isoformat(),
            recommendation=recommendation
        )
        
        self.anomalies.append(anomaly)
        
        self._save_anomaly(anomaly)
    
    def _save_anomaly(self, anomaly: Anomaly):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO insights (batch_id, insight_type, content, severity)
            VALUES (?, ?, ?, ?)
        """, (
            anomaly.batch_id,
            anomaly.anomaly_type.value,
            anomaly.message,
            anomaly.severity.value
        ))
        self.conn.commit()
    
    def get_statistics(self) -> Dict:
        if not self.anomalies:
            return {"total": 0, "by_severity": {}, "by_type": {}}
        
        by_severity = {}
        by_type = {}
        
        for a in self.anomalies:
            sev = a.severity.value
            typ = a.anomaly_type.value
            
            by_severity[sev] = (by_severity.get(sev, 0) + 1)
            by_type[typ] = (by_type.get(typ, 0) + 1)
        
        return {
            "total": len(self.anomalies),
            "by_severity": by_severity,
            "by_type": by_type,
            "critical_count": by_severity.get("critical", 0),
            "high_count": by_severity.get("high", 0),
            "medium_count": by_severity.get("medium", 0),
            "low_count": by_severity.get("low", 0)
        }
    
    def get_recommendations(self) -> List[Dict]:
        recommendations = []
        
        for anomaly in self.anomalies:
            if anomaly.severity in [Severity.HIGH, Severity.CRITICAL]:
                recommendations.append({
                    "priority": anomaly.severity.value,
                    "batch_id": anomaly.batch_id,
                    "issue": anomaly.message,
                    "recommendation": anomaly.recommendation
                })
        
        return sorted(recommendations, key=lambda x: 
            {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x["priority"], 4)
        )
