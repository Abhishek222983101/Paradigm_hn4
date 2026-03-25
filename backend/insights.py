"""
TraceLoop AI Insights Engine
Generates intelligent insights from traceability data
"""

from typing import Dict, List, Optional
from datetime import datetime
import statistics

class InsightEngine:
    
    LOSS_THRESHOLDS = {
        "segregation": {"warning": 10, "critical": 15},
        "washing": {"warning": 10, "critical": 15},
        "recycling": {"warning": 18, "critical": 25},
        "granulation": {"warning": 5, "critical": 8},
        "overall": {"warning": 25, "critical": 35}
    }
    
    def __init__(self, db_connection):
        self.conn = db_connection
    
    def analyze_batch(self, batch_id: str) -> Dict:
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT * FROM batches WHERE batch_id = ?", (batch_id,))
        batch = cursor.fetchone()
        if not batch:
            return {"error": "Batch not found"}
        
        cursor.execute("""
            SELECT stage, qty_in, qty_out, status, timestamp 
            FROM transactions 
            WHERE batch_id = ? 
            ORDER BY timestamp
        """, (batch_id,))
        transactions = cursor.fetchall()
        
        batch_dict = dict(batch)
        analysis = {
            "batch_id": batch_id,
            "material_type": batch_dict["material_type"],
            "source_vendor": batch_dict["source_vendor"],
            "collection_date": batch_dict["collection_date"],
            "stages": [],
            "metrics": {},
            "insights": [],
            "alerts": [],
            "summary": ""
        }
        
        total_in = 0
        total_out = 0
        stage_losses = {}
        
        for tx in transactions:
            tx_dict = dict(tx)
            stage = tx_dict["stage"]
            qty_in = tx_dict["qty_in"] or 0
            qty_out = tx_dict["qty_out"] or qty_in
            
            stage_loss = qty_in - qty_out if qty_out else 0
            stage_loss_pct = (stage_loss / qty_in * 100) if qty_in > 0 else 0
            
            analysis["stages"].append({
                "stage": stage,
                "qty_in": qty_in,
                "qty_out": qty_out,
                "loss_kg": stage_loss,
                "loss_percent": round(stage_loss_pct, 1),
                "status": tx_dict["status"]
            })
            
            if stage_loss > 0:
                stage_losses[stage] = stage_loss
            
            total_in = qty_in if total_in == 0 else total_in
            total_out = qty_out
        
        total_loss = total_in - total_out
        total_loss_pct = (total_loss / total_in * 100) if total_in > 0 else 0
        
        analysis["metrics"] = {
            "total_input_kg": round(total_in, 2),
            "total_output_kg": round(total_out, 2),
            "total_loss_kg": round(total_loss, 2),
            "total_loss_percent": round(total_loss_pct, 1),
            "yield_percent": round(100 - total_loss_pct, 1),
            "stages_completed": len([s for s in analysis["stages"] if s["status"] == "APPROVED"])
        }
        
        for stage_data in analysis["stages"]:
            stage = stage_data["stage"]
            loss_pct = stage_data["loss_percent"]
            
            if stage in self.LOSS_THRESHOLDS:
                thresholds = self.LOSS_THRESHOLDS[stage]
                if loss_pct > thresholds["critical"]:
                    analysis["alerts"].append({
                        "type": "critical",
                        "stage": stage,
                        "message": f"Critical loss of {loss_pct}% at {stage} stage (threshold: {thresholds['critical']}%)"
                    })
                elif loss_pct > thresholds["warning"]:
                    analysis["alerts"].append({
                        "type": "warning",
                        "stage": stage,
                        "message": f"High loss of {loss_pct}% at {stage} stage (threshold: {thresholds['warning']}%)"
                    })
        
        if any(tx["status"] == "REJECTED" for tx in analysis["stages"]):
            rejected_stages = [tx["stage"] for tx in analysis["stages"] if tx["status"] == "REJECTED"]
            analysis["alerts"].append({
                "type": "anomaly",
                "stage": ", ".join(rejected_stages),
                "message": f"Rejected transactions found at: {', '.join(rejected_stages)}"
            })
        
        analysis["summary"] = self._generate_summary(analysis)
        
        return analysis
    
    def _generate_summary(self, analysis: Dict) -> str:
        metrics = analysis["metrics"]
        summary_parts = []
        
        summary_parts.append(
            f"Batch {analysis['batch_id']} ({analysis['material_type']}): "
            f"Started with {metrics['total_input_kg']}kg from {analysis['source_vendor']}."
        )
        
        if metrics['stages_completed'] >= 5:
            summary_parts.append(
                f"Completed {metrics['stages_completed']} processing stages with "
                f"{metrics['yield_percent']}% yield ({metrics['total_output_kg']}kg output)."
            )
        else:
            summary_parts.append(
                f"Currently at {metrics['stages_completed']} stages completed."
            )
        
        if metrics['total_loss_percent'] > 25:
            summary_parts.append(
                f"WARNING: Total loss of {metrics['total_loss_percent']}% exceeds the 25% threshold."
            )
        else:
            summary_parts.append(
                f"Total loss: {metrics['total_loss_kg']}kg ({metrics['total_loss_percent']}%), within acceptable range."
            )
        
        if analysis['alerts']:
            summary_parts.append(
                f"{len(analysis['alerts'])} alert(s) detected requiring attention."
            )
        
        return " ".join(summary_parts)
    
    def compare_with_average(self, batch_analysis: Dict) -> Dict:
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT b.batch_id, b.total_input_kg, b.total_output_kg, b.material_type
            FROM batches b
            WHERE b.material_type = ?
        """, (batch_analysis["material_type"],))
        
        similar_batches = cursor.fetchall()
        
        if len(similar_batches) < 2:
            return {"comparison": "Insufficient data for comparison"}
        
        loss_percents = []
        for batch in similar_batches:
            batch_dict = dict(batch)
            if batch_dict["total_input_kg"] and batch_dict["total_output_kg"]:
                loss_pct = ((batch_dict["total_input_kg"] - batch_dict["total_output_kg"]) / 
                           batch_dict["total_input_kg"] * 100)
                loss_percents.append(loss_pct)
        
        if not loss_percents:
            return {"comparison": "No comparable data"}
        
        avg_loss = statistics.mean(loss_percents)
        std_dev = statistics.stdev(loss_percents) if len(loss_percents) > 1 else 0
        
        current_loss = batch_analysis["metrics"]["total_loss_percent"]
        deviation = current_loss - avg_loss
        
        comparison = {
            "average_loss_percent": round(avg_loss, 1),
            "standard_deviation": round(std_dev, 1),
            "current_batch_loss": current_loss,
            "deviation_from_average": round(deviation, 1),
            "status": "normal"
        }
        
        if deviation > std_dev * 1.5:
            comparison["status"] = "above_average"
            comparison["recommendation"] = "Loss rate significantly above average. Investigate contamination or process issues."
        elif deviation < -std_dev:
            comparison["status"] = "below_average"
            comparison["recommendation"] = "Loss rate better than average. Document best practices."
        
        return comparison
    
    def generate_report(self, date_range: tuple = None, material_type: str = None) -> Dict:
        cursor = self.conn.cursor()
        
        query = "SELECT batch_id, material_type, total_input_kg, total_output_kg, confidence_score FROM batches WHERE 1=1"
        params = []
        
        if material_type:
            query += " AND material_type = ?"
            params.append(material_type)
        
        cursor.execute(query, params)
        batches = cursor.fetchall()
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_batches": len(batches),
            "material_breakdown": {},
            "overall_metrics": {
                "total_input_kg": 0,
                "total_output_kg": 0,
                "average_yield": 0,
                "average_confidence": 0
            },
            "recommendations": []
        }
        
        total_input = 0
        total_output = 0
        confidence_scores = []
        
        for batch in batches:
            batch_dict = dict(batch)
            mat = batch_dict["material_type"]
            
            if mat not in report["material_breakdown"]:
                report["material_breakdown"][mat] = {
                    "count": 0,
                    "total_input_kg": 0,
                    "total_output_kg": 0
                }
            
            report["material_breakdown"][mat]["count"] += 1
            report["material_breakdown"][mat]["total_input_kg"] += batch_dict["total_input_kg"] or 0
            report["material_breakdown"][mat]["total_output_kg"] += batch_dict["total_output_kg"] or 0
            
            total_input += batch_dict["total_input_kg"] or 0
            total_output += batch_dict["total_output_kg"] or 0
            confidence_scores.append(batch_dict["confidence_score"] or 0)
        
        report["overall_metrics"]["total_input_kg"] = round(total_input, 2)
        report["overall_metrics"]["total_output_kg"] = round(total_output, 2)
        report["overall_metrics"]["average_yield"] = round(
            (total_output / total_input * 100) if total_input > 0 else 0, 1
        )
        report["overall_metrics"]["average_confidence"] = round(
            sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0, 1
        )
        
        if report["overall_metrics"]["average_yield"] < 70:
            report["recommendations"].append(
                "Average yield below 70%. Review processing efficiency at washing and recycling stages."
            )
        
        if report["overall_metrics"]["average_confidence"] < 60:
            report["recommendations"].append(
                "Data confidence below 60%. Ensure all transaction stages are properly recorded."
            )
        
        return report
