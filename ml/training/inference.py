"""
TraceFlow AI - ML Inference Module v2.0
=======================================
Provides prediction functions for yield and anomaly detection.
Compatible with models trained by train_models.py v2.0

For Hackathon: SYNAPSE HackNiche 4.0 (ML PS1)
"""

import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, List, Any

MODEL_DIR = Path(__file__).parent.parent / "models"


class TraceFlowPredictor:
    """
    ML Predictor for TraceFlow AI.

    Provides high-level prediction interfaces for:
    - Yield prediction (XGBoost)
    - Anomaly detection (Isolation Forest)
    - Batch analysis
    """

    def __init__(self):
        """Initialize the predictor and load models."""
        self.yield_model = None
        self.yield_label_encoders = {}
        self.yield_features = []
        self.yield_metrics = {}

        self.anomaly_model = None
        self.anomaly_label_encoders = {}
        self.anomaly_scaler = None
        self.anomaly_features = []
        self.anomaly_threshold = 0.0
        self.anomaly_metrics = {}

        self.models_loaded = False
        self.load_models()

    def load_models(self) -> bool:
        """
        Load trained models from disk.

        Returns:
            True if at least one model was loaded successfully
        """
        loaded_any = False

        # Load yield predictor
        yield_path = MODEL_DIR / "yield_predictor.pkl"
        if yield_path.exists():
            try:
                with open(yield_path, "rb") as f:
                    data = pickle.load(f)
                    self.yield_model = data["model"]
                    self.yield_label_encoders = data.get("label_encoders", {})
                    self.yield_features = data.get("feature_columns", [])
                    self.yield_metrics = data.get("metrics", {})
                print(f"[ML] Loaded yield predictor from {yield_path}")
                print(f"     R² Score: {self.yield_metrics.get('r2', 'N/A')}")
                loaded_any = True
            except Exception as e:
                print(f"[ML ERROR] Failed to load yield predictor: {e}")
        else:
            print(f"[ML WARNING] Yield predictor not found at {yield_path}")

        # Load anomaly detector
        anomaly_path = MODEL_DIR / "anomaly_detector.pkl"
        if anomaly_path.exists():
            try:
                with open(anomaly_path, "rb") as f:
                    data = pickle.load(f)
                    self.anomaly_model = data["model"]
                    self.anomaly_label_encoders = data.get("label_encoders", {})
                    self.anomaly_scaler = data.get("scaler")
                    self.anomaly_features = data.get("feature_columns", [])
                    self.anomaly_threshold = data.get("threshold", 0.0)
                    self.anomaly_metrics = data.get("metrics", {})
                print(f"[ML] Loaded anomaly detector from {anomaly_path}")
                print(f"     F1 Score: {self.anomaly_metrics.get('f1_score', 'N/A')}")
                loaded_any = True
            except Exception as e:
                print(f"[ML ERROR] Failed to load anomaly detector: {e}")
        else:
            print(f"[ML WARNING] Anomaly detector not found at {anomaly_path}")

        self.models_loaded = loaded_any
        return loaded_any

    def _encode_features(self, df: pd.DataFrame, label_encoders: Dict) -> pd.DataFrame:
        """Encode categorical features using saved label encoders."""
        df_encoded = df.copy()

        for col in df.select_dtypes(include=["object", "string"]).columns:
            le = label_encoders.get(col)
            if le:
                df_encoded[col] = df_encoded[col].fillna("Unknown")
                df_encoded[col] = df_encoded[col].apply(
                    lambda x: le.transform([str(x)])[0] if str(x) in le.classes_ else -1
                )
            else:
                # No encoder found, use -1 for unknown
                df_encoded[col] = -1

        return df_encoded

    def predict_yield(
        self,
        process_mode: str,
        input_quantity: float,
        source_material: str = "Unknown",
        source_state: str = "Unknown",
        source_grade: str = "Unknown",
        scenario: str = "Unknown",
    ) -> Dict[str, Any]:
        """
        Predict yield percentage for a processing step.

        Args:
            process_mode: Type of process (WASHING, SEGREGATION, etc.)
            input_quantity: Input material quantity in kg
            source_material: Material type (PET, HDPE, etc.)
            source_state: Material form (FLAKE, GRANULE, etc.)
            source_grade: Quality grade (Grade A, Grade B, etc.)
            scenario: Scenario identifier

        Returns:
            Dictionary with:
            - predicted_yield: Predicted yield percentage
            - predicted_loss: Predicted loss percentage
            - predicted_output: Predicted output quantity
            - confidence: Confidence level (high/medium/low)
            - model_r2: Model's R² score
        """
        if self.yield_model is None:
            return {
                "error": "Yield model not loaded",
                "predicted_yield": 0.0,
                "predicted_loss": 0.0,
                "predicted_output": 0.0,
                "confidence": "none",
            }

        # Create feature DataFrame
        features = pd.DataFrame(
            [
                {
                    "process_mode": process_mode,
                    "input_quantity": float(input_quantity),
                    "source_material": source_material,
                    "source_state": source_state,
                    "source_grade": source_grade,
                    "scenario": scenario,
                }
            ]
        )

        # Ensure columns match training order
        for col in self.yield_features:
            if col not in features.columns:
                features[col] = "Unknown"
        features = features[self.yield_features]

        # Encode and predict
        X = self._encode_features(features, self.yield_label_encoders)

        try:
            yield_pred = float(self.yield_model.predict(X)[0])
        except Exception as e:
            return {
                "error": f"Prediction failed: {str(e)}",
                "predicted_yield": 0.0,
                "predicted_loss": 0.0,
                "predicted_output": 0.0,
                "confidence": "none",
            }

        # Clip to valid range
        yield_pred = np.clip(yield_pred, 0, 100)

        # Calculate derived values
        loss_pred = 100 - yield_pred
        output_pred = input_quantity * yield_pred / 100

        # Determine confidence based on yield and model quality
        r2 = self.yield_metrics.get("r2", 0)
        if r2 > 0.9 and yield_pred > 85:
            confidence = "high"
        elif r2 > 0.7 and yield_pred > 70:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "predicted_yield": round(float(yield_pred), 2),
            "predicted_loss": round(float(loss_pred), 2),
            "predicted_output": round(float(output_pred), 2),
            "confidence": confidence,
            "model_r2": round(float(r2), 4) if r2 else None,
            "process_mode": process_mode,
            "input_quantity": float(input_quantity),
        }

    def detect_anomaly(
        self, loss_percent: float, quantity: float, process_mode: str
    ) -> Dict[str, Any]:
        """
        Detect if a transaction is anomalous.

        Args:
            loss_percent: Observed loss percentage
            quantity: Processing quantity
            process_mode: Type of process

        Returns:
            Dictionary with:
            - is_anomaly: Boolean indicating anomaly
            - anomaly_score: Numerical anomaly score (higher = more anomalous)
            - threshold: Decision threshold
            - reason: Human-readable reason if anomaly
            - severity: low/medium/high
        """
        if self.anomaly_model is None:
            return {
                "error": "Anomaly model not loaded",
                "is_anomaly": False,
                "anomaly_score": 0.0,
                "threshold": 0.0,
                "reason": None,
                "severity": "unknown",
            }

        # Create feature DataFrame
        features = pd.DataFrame(
            [
                {
                    "process_mode": process_mode,
                    "loss_percent": float(loss_percent),
                    "quantity": float(quantity),
                }
            ]
        )

        # Encode categorical features
        X = self._encode_features(features, self.anomaly_label_encoders)

        # Scale features if scaler exists
        if self.anomaly_scaler is not None:
            X_scaled = self.anomaly_scaler.transform(X)
        else:
            X_scaled = X.values

        try:
            # Get prediction (-1 = anomaly, 1 = normal)
            prediction = self.anomaly_model.predict(X_scaled)[0]

            # Get anomaly score (higher = more anomalous)
            score = float(-self.anomaly_model.decision_function(X_scaled)[0])
        except Exception as e:
            return {
                "error": f"Detection failed: {str(e)}",
                "is_anomaly": False,
                "anomaly_score": 0.0,
                "threshold": self.anomaly_threshold,
                "reason": None,
                "severity": "unknown",
            }

        # Determine if anomaly
        is_anomaly = prediction == -1 or score > self.anomaly_threshold

        # Generate reason
        reason = None
        severity = "low"

        if is_anomaly:
            if loss_percent < 0:
                reason = "Negative loss detected - more output than input (data entry error or fraud)"
                severity = "high"
            elif loss_percent > 50:
                reason = f"Extremely high loss ({loss_percent:.1f}%) - major processing issue or data error"
                severity = "high"
            elif loss_percent > 25:
                reason = f"Unusually high loss ({loss_percent:.1f}%) for {process_mode}"
                severity = "medium"
            elif quantity > 50000:
                reason = (
                    f"Extremely large quantity ({quantity:.0f} kg) for single batch"
                )
                severity = "medium"
            elif quantity < 1:
                reason = f"Unusually small quantity ({quantity:.2f} kg) - inefficient processing"
                severity = "low"
            else:
                reason = "Statistical outlier based on historical patterns"
                severity = "medium" if score > self.anomaly_threshold * 1.5 else "low"

        return {
            "is_anomaly": bool(is_anomaly),
            "anomaly_score": round(float(score), 4),
            "threshold": round(float(self.anomaly_threshold), 4),
            "reason": reason,
            "severity": severity,
            "loss_percent": float(loss_percent),
            "quantity": float(quantity),
            "process_mode": process_mode,
        }

    def analyze_batch(self, transforms: List[Dict]) -> Dict[str, Any]:
        """
        Analyze a batch of transforms for anomalies and yield insights.

        Args:
            transforms: List of dicts with loss_percent, quantity, process_mode

        Returns:
            Summary with anomalies found and overall health assessment
        """
        if not transforms:
            return {
                "total_steps": 0,
                "anomalies_found": 0,
                "anomaly_details": [],
                "average_loss": 0.0,
                "total_quantity_processed": 0.0,
                "health_score": 100,
                "health_status": "unknown",
            }

        anomalies = []
        total_loss = 0.0
        total_quantity = 0.0

        for i, t in enumerate(transforms):
            loss_pct = t.get("loss_percent", 0)
            qty = t.get("quantity", 0)
            mode = t.get("process_mode", "Unknown")

            # Detect anomalies
            anomaly_result = self.detect_anomaly(
                loss_percent=loss_pct, quantity=qty, process_mode=mode
            )

            if anomaly_result.get("is_anomaly"):
                anomalies.append({"step": i + 1, "process": mode, **anomaly_result})

            total_loss += loss_pct
            total_quantity += qty

        # Calculate health score (0-100)
        n_steps = len(transforms)
        n_anomalies = len(anomalies)

        # Deduct points for anomalies (more severe = more deduction)
        deduction = 0
        for a in anomalies:
            if a["severity"] == "high":
                deduction += 25
            elif a["severity"] == "medium":
                deduction += 15
            else:
                deduction += 5

        health_score = max(0, 100 - deduction)

        # Determine health status
        if health_score >= 90:
            health_status = "excellent"
        elif health_score >= 75:
            health_status = "good"
        elif health_score >= 50:
            health_status = "fair"
        else:
            health_status = "poor"

        return {
            "total_steps": n_steps,
            "anomalies_found": n_anomalies,
            "anomaly_details": anomalies,
            "average_loss": round(total_loss / n_steps, 2) if n_steps > 0 else 0.0,
            "total_quantity_processed": round(total_quantity, 2),
            "health_score": health_score,
            "health_status": health_status,
        }

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models."""
        return {
            "models_loaded": self.models_loaded,
            "yield_model": {
                "loaded": self.yield_model is not None,
                "features": self.yield_features,
                "metrics": self.yield_metrics,
            },
            "anomaly_model": {
                "loaded": self.anomaly_model is not None,
                "features": self.anomaly_features,
                "threshold": self.anomaly_threshold,
                "metrics": self.anomaly_metrics,
            },
        }


# Singleton instance for global access
_predictor: Optional[TraceFlowPredictor] = None


def get_predictor() -> TraceFlowPredictor:
    """
    Get or create the predictor singleton.

    Returns:
        TraceFlowPredictor instance
    """
    global _predictor
    if _predictor is None:
        _predictor = TraceFlowPredictor()
    return _predictor


def reload_models() -> TraceFlowPredictor:
    """
    Force reload of all models.

    Returns:
        Fresh TraceFlowPredictor instance
    """
    global _predictor
    _predictor = TraceFlowPredictor()
    return _predictor


# =============================================================================
# CLI Testing
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("TraceFlow AI - ML Inference Module Test")
    print("=" * 70)

    # Initialize predictor
    predictor = get_predictor()

    # Print model info
    info = predictor.get_model_info()
    print(f"\nModel Status:")
    print(
        f"  Yield Model: {'LOADED' if info['yield_model']['loaded'] else 'NOT LOADED'}"
    )
    if info["yield_model"]["loaded"]:
        print(f"    R² Score: {info['yield_model']['metrics'].get('r2', 'N/A')}")
    print(
        f"  Anomaly Model: {'LOADED' if info['anomaly_model']['loaded'] else 'NOT LOADED'}"
    )
    if info["anomaly_model"]["loaded"]:
        print(
            f"    F1 Score: {info['anomaly_model']['metrics'].get('f1_score', 'N/A')}"
        )

    # Test yield predictions
    print("\n" + "=" * 70)
    print("Testing Yield Predictor")
    print("=" * 70)

    yield_tests = [
        {"process_mode": "WASHING", "input_quantity": 1000, "source_material": "PET"},
        {
            "process_mode": "SEGREGATION",
            "input_quantity": 500,
            "source_material": "HDPE",
        },
        {"process_mode": "RECYCLING", "input_quantity": 800, "source_material": "PP"},
        {
            "process_mode": "MANUFACTURING",
            "input_quantity": 2000,
            "source_material": "PET",
        },
        {
            "process_mode": "TRANSFER",
            "input_quantity": 1500,
            "source_material": "FLAKE",
        },
    ]

    for test in yield_tests:
        result = predictor.predict_yield(**test)
        print(
            f"\n{test['process_mode']} ({test['input_quantity']} kg {test.get('source_material', '')}):"
        )
        if "error" in result:
            print(f"  ERROR: {result['error']}")
        else:
            print(f"  Predicted Yield: {result['predicted_yield']}%")
            print(f"  Predicted Output: {result['predicted_output']} kg")
            print(f"  Confidence: {result['confidence']}")

    # Test anomaly detection
    print("\n" + "=" * 70)
    print("Testing Anomaly Detector")
    print("=" * 70)

    anomaly_tests = [
        {"loss_percent": 3.0, "quantity": 1000, "process_mode": "WASHING"},  # Normal
        {
            "loss_percent": 50.0,
            "quantity": 500,
            "process_mode": "SEGREGATION",
        },  # High loss
        {
            "loss_percent": -5.0,
            "quantity": 800,
            "process_mode": "RECYCLING",
        },  # Negative loss
        {
            "loss_percent": 2.0,
            "quantity": 100000,
            "process_mode": "TRANSFER",
        },  # Large quantity
        {
            "loss_percent": 1.0,
            "quantity": 0.5,
            "process_mode": "WASHING",
        },  # Tiny quantity
    ]

    for test in anomaly_tests:
        result = predictor.detect_anomaly(**test)
        print(
            f"\nLoss: {test['loss_percent']}%, Qty: {test['quantity']}, Process: {test['process_mode']}"
        )
        if "error" in result:
            print(f"  ERROR: {result['error']}")
        else:
            status = "ANOMALY" if result["is_anomaly"] else "NORMAL"
            print(
                f"  Status: {status} (score: {result['anomaly_score']}, threshold: {result['threshold']})"
            )
            if result["reason"]:
                print(f"  Reason: {result['reason']}")
                print(f"  Severity: {result['severity']}")

    # Test batch analysis
    print("\n" + "=" * 70)
    print("Testing Batch Analysis")
    print("=" * 70)

    batch_transforms = [
        {"loss_percent": 5.0, "quantity": 1000, "process_mode": "WASHING"},
        {"loss_percent": 8.0, "quantity": 950, "process_mode": "SEGREGATION"},
        {"loss_percent": 45.0, "quantity": 870, "process_mode": "RECYCLING"},  # Anomaly
        {"loss_percent": 2.0, "quantity": 480, "process_mode": "MANUFACTURING"},
    ]

    batch_result = predictor.analyze_batch(batch_transforms)
    print(f"\nBatch Analysis Results:")
    print(f"  Total Steps: {batch_result['total_steps']}")
    print(f"  Anomalies Found: {batch_result['anomalies_found']}")
    print(f"  Average Loss: {batch_result['average_loss']}%")
    print(f"  Health Score: {batch_result['health_score']}/100")
    print(f"  Health Status: {batch_result['health_status'].upper()}")

    if batch_result["anomaly_details"]:
        print(f"\n  Anomaly Details:")
        for a in batch_result["anomaly_details"]:
            print(
                f"    Step {a['step']} ({a['process']}): {a['reason']} [{a['severity'].upper()}]"
            )

    print("\n" + "=" * 70)
    print("All tests completed!")
    print("=" * 70)
