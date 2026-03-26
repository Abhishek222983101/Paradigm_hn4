"""
TraceFlow AI - ML Training Data Generator
Generates synthetic yield and anomaly training data based on real industrial recycling patterns.

This generator creates DIVERSE training samples with:
1. Realistic loss percentages by process type (based on industry standards)
2. Edge cases (very high/low losses, extreme quantities)
3. Anomalous data points for anomaly detection training
4. Material-specific yield patterns
"""

import json
import random
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

# Set seed for reproducibility
np.random.seed(42)
random.seed(42)

# ============================================================================
# DOMAIN KNOWLEDGE: Real Industrial Recycling Yield Patterns
# These are based on actual recycling industry standards
# ============================================================================

# Process-specific yield patterns (mean, std, min, max)
# Format: {"mode": (mean_yield, std_yield, min_yield, max_yield)}
PROCESS_YIELD_PATTERNS = {
    # Washing: Typically 92-98% yield (2-8% loss from dirt, contaminants)
    "WASHING": {"mean": 94.0, "std": 2.5, "min": 85.0, "max": 99.0},
    # Segregation: 85-95% yield (5-15% loss from rejected materials)
    "SEGREGATION": {"mean": 90.0, "std": 4.0, "min": 70.0, "max": 99.0},
    # Recycling/Pelletizing: 90-97% yield (3-10% loss from processing)
    "RECYCLING": {"mean": 93.0, "std": 3.0, "min": 80.0, "max": 98.0},
    # Manufacturing: 95-99% yield (1-5% loss)
    "MANUFACTURING": {"mean": 97.0, "std": 1.5, "min": 92.0, "max": 99.5},
    # Production: Similar to manufacturing
    "PRODUCTION": {"mean": 97.5, "std": 1.2, "min": 93.0, "max": 99.5},
    # Quality Control: Pass/Fail (yield is % that passes)
    "QUALITY_CONTROL": {"mean": 85.0, "std": 10.0, "min": 50.0, "max": 100.0},
    # Transfer: Minimal loss (spillage, handling)
    "TRANSFER": {"mean": 99.0, "std": 0.5, "min": 97.0, "max": 100.0},
    # Baling: Compression, minimal loss
    "BALING": {"mean": 99.5, "std": 0.3, "min": 98.0, "max": 100.0},
    # Mixing/Blending: Some material sticks to equipment
    "MIXING": {"mean": 98.0, "std": 1.0, "min": 95.0, "max": 100.0},
    # Inward/Receipt: Should be 100% (just receiving)
    "INWARD": {"mean": 100.0, "std": 0.0, "min": 100.0, "max": 100.0},
    "RECEIPT": {"mean": 100.0, "std": 0.0, "min": 100.0, "max": 100.0},
    # QC Pass: 100% of what passed
    "QC_PASS": {"mean": 100.0, "std": 0.0, "min": 100.0, "max": 100.0},
    # QC Fail: 0% yield (all rejected)
    "QC_FAIL": {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0},
}

# Material-specific yield modifiers (some materials process better than others)
MATERIAL_MODIFIERS = {
    "PET": {"yield_modifier": 1.02, "difficulty": "easy"},  # PET processes well
    "HDPE": {"yield_modifier": 1.00, "difficulty": "medium"},  # Standard
    "LDPE": {
        "yield_modifier": 0.98,
        "difficulty": "hard",
    },  # Thin film, harder to process
    "PP": {"yield_modifier": 1.01, "difficulty": "easy"},  # Good processing
    "PVC": {"yield_modifier": 0.95, "difficulty": "hard"},  # Difficult, chlorine issues
    "FLAKE": {"yield_modifier": 1.03, "difficulty": "easy"},  # Already processed
    "GRANULE": {
        "yield_modifier": 1.05,
        "difficulty": "easy",
    },  # Final form, minimal loss
    "PRODUCT": {"yield_modifier": 1.0, "difficulty": "medium"},  # Varies
    "MIXED": {
        "yield_modifier": 0.92,
        "difficulty": "hard",
    },  # Mixed plastics = more loss
}

# Grade-specific modifiers
GRADE_MODIFIERS = {
    "Grade A": 1.05,  # Premium = better yield
    "Grade B": 1.00,  # Standard
    "Grade C": 0.95,  # Lower quality = more loss
    "Premium": 1.06,
    "Standard": 1.00,
    "Rejected": 0.50,  # Already poor quality
    "Food Grade": 1.04,
    "Technical Grade": 0.98,
    "Unknown": 1.00,
}

# Scenarios with different profiles
SCENARIOS = ["SCN-1", "SCN-2", "SCN-3", "SCN-4", "SCN-5", "SCN-6"]

# Form/State of materials
MATERIAL_FORMS = ["BALE", "FLAKE", "GRANULE", "RAW", "PROCESSED", "WASHED", "SORTED"]


def generate_yield_sample(
    process_mode: str,
    material_type: str = None,
    grade: str = None,
    quantity: float = None,
    scenario: str = None,
    add_noise: bool = True,
) -> dict:
    """Generate a single yield training sample with realistic values."""

    # Get base yield pattern for this process
    pattern = PROCESS_YIELD_PATTERNS.get(
        process_mode, PROCESS_YIELD_PATTERNS["TRANSFER"]
    )

    # Generate base yield from normal distribution
    base_yield = np.random.normal(pattern["mean"], pattern["std"])

    # Apply material modifier
    material = material_type or random.choice(list(MATERIAL_MODIFIERS.keys()))
    material_mod = MATERIAL_MODIFIERS.get(material, MATERIAL_MODIFIERS["PET"])
    yield_value = base_yield * material_mod["yield_modifier"]

    # Apply grade modifier
    grade = grade or random.choice(list(GRADE_MODIFIERS.keys()))
    grade_mod = GRADE_MODIFIERS.get(grade, 1.0)
    yield_value = yield_value * grade_mod

    # Clip to realistic bounds
    yield_value = np.clip(yield_value, pattern["min"], pattern["max"])

    # Add small random noise for diversity
    if add_noise:
        yield_value += np.random.uniform(-0.5, 0.5)
        yield_value = np.clip(yield_value, 0, 100)

    # Generate quantity (realistic industrial quantities)
    if quantity is None:
        # Log-normal distribution for realistic quantity spread
        quantity = np.random.lognormal(
            mean=6.5, sigma=1.0
        )  # Mean ~660kg, range 50-5000+
        quantity = np.clip(quantity, 50, 10000)

    # Calculate loss
    loss_percent = 100 - yield_value

    # Select scenario
    scenario = scenario or random.choice(SCENARIOS)

    # Select form/state
    source_state = random.choice(MATERIAL_FORMS)

    return {
        "process_mode": process_mode,
        "input_quantity": round(quantity, 2),
        "source_material": material,
        "source_state": source_state,
        "source_grade": grade,
        "scenario": scenario,
        "yield_percent": round(yield_value, 2),
        "loss_percent": round(loss_percent, 2),
        "output_quantity": round(quantity * yield_value / 100, 2),
    }


def generate_anomaly_sample(anomaly_type: str = None) -> dict:
    """Generate an anomalous data point for anomaly detection training."""

    if anomaly_type is None:
        anomaly_type = random.choice(
            [
                "high_loss",
                "negative_loss",
                "extreme_quantity_high",
                "extreme_quantity_low",
                "impossible_yield",
                "process_mismatch",
            ]
        )

    process_mode = random.choice(list(PROCESS_YIELD_PATTERNS.keys()))

    if anomaly_type == "high_loss":
        # Unusually high loss (>30%)
        loss_percent = random.uniform(35, 80)
        quantity = random.uniform(100, 2000)
        reason = f"Unusually high loss ({loss_percent:.1f}%) for {process_mode}"
        severity = "high" if loss_percent > 50 else "medium"

    elif anomaly_type == "negative_loss":
        # Negative loss (impossible - more output than input)
        loss_percent = random.uniform(-30, -5)
        quantity = random.uniform(100, 2000)
        reason = "Negative loss - more output than input (data entry error or fraud)"
        severity = "high"

    elif anomaly_type == "extreme_quantity_high":
        # Extremely large quantity (unusual for single batch)
        loss_percent = random.uniform(2, 8)
        quantity = random.uniform(50000, 500000)
        reason = (
            f"Unusually large quantity ({quantity:.0f}kg) for single processing batch"
        )
        severity = "medium"

    elif anomaly_type == "extreme_quantity_low":
        # Extremely small quantity (waste of processing)
        loss_percent = random.uniform(2, 8)
        quantity = random.uniform(0.1, 5)
        reason = f"Unusually small quantity ({quantity:.2f}kg) - inefficient processing"
        severity = "low"

    elif anomaly_type == "impossible_yield":
        # Yield > 100% (impossible)
        loss_percent = random.uniform(-50, -10)  # This makes yield > 100
        quantity = random.uniform(500, 2000)
        reason = "Yield exceeds 100% - data entry error"
        severity = "high"

    elif anomaly_type == "process_mismatch":
        # Process with unexpected loss pattern
        # e.g., TRANSFER with high loss
        process_mode = "TRANSFER"
        loss_percent = random.uniform(15, 40)
        quantity = random.uniform(500, 2000)
        reason = (
            f"High loss ({loss_percent:.1f}%) for TRANSFER operation (should be <3%)"
        )
        severity = "high"

    return {
        "process_mode": process_mode,
        "loss_percent": round(loss_percent, 2),
        "quantity": round(quantity, 2),
        "is_anomaly": True,
        "anomaly_type": anomaly_type,
        "reason": reason,
        "severity": severity,
    }


def generate_normal_sample_for_anomaly() -> dict:
    """Generate a normal (non-anomalous) sample for anomaly detection."""

    process_mode = random.choice(list(PROCESS_YIELD_PATTERNS.keys()))
    pattern = PROCESS_YIELD_PATTERNS[process_mode]

    # Normal loss within expected range
    mean_loss = 100 - pattern["mean"]
    std_loss = pattern["std"]
    loss_percent = np.random.normal(mean_loss, std_loss)
    loss_percent = np.clip(loss_percent, 0, 100 - pattern["min"])

    # Normal quantity range
    quantity = np.random.lognormal(mean=6.5, sigma=0.8)
    quantity = np.clip(quantity, 100, 5000)

    return {
        "process_mode": process_mode,
        "loss_percent": round(loss_percent, 2),
        "quantity": round(quantity, 2),
        "is_anomaly": False,
        "anomaly_type": None,
        "reason": None,
        "severity": "low",
    }


def generate_yield_dataset(n_samples: int = 2000) -> pd.DataFrame:
    """Generate a comprehensive yield prediction training dataset."""

    samples = []

    # Distribute samples across process types
    process_modes = list(PROCESS_YIELD_PATTERNS.keys())
    samples_per_mode = n_samples // len(process_modes)

    for mode in process_modes:
        for _ in range(samples_per_mode):
            sample = generate_yield_sample(process_mode=mode)
            samples.append(sample)

    # Add extra samples with edge cases
    edge_case_count = n_samples - len(samples)
    for _ in range(edge_case_count):
        # Random edge cases
        mode = random.choice(process_modes)

        # Sometimes use extreme quantities
        if random.random() < 0.2:
            quantity = random.choice(
                [
                    random.uniform(10, 50),  # Small batch
                    random.uniform(5000, 10000),  # Large batch
                ]
            )
        else:
            quantity = None

        sample = generate_yield_sample(process_mode=mode, quantity=quantity)
        samples.append(sample)

    df = pd.DataFrame(samples)

    # Shuffle
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    return df


def generate_anomaly_dataset(
    n_normal: int = 1500, n_anomaly: int = 500
) -> pd.DataFrame:
    """Generate a dataset for anomaly detection training."""

    samples = []

    # Generate normal samples
    for _ in range(n_normal):
        samples.append(generate_normal_sample_for_anomaly())

    # Generate anomaly samples (distributed across types)
    anomaly_types = [
        "high_loss",
        "negative_loss",
        "extreme_quantity_high",
        "extreme_quantity_low",
        "impossible_yield",
        "process_mismatch",
    ]
    anomalies_per_type = n_anomaly // len(anomaly_types)

    for atype in anomaly_types:
        for _ in range(anomalies_per_type):
            samples.append(generate_anomaly_sample(anomaly_type=atype))

    # Add remaining anomalies randomly
    remaining = n_anomaly - (anomalies_per_type * len(anomaly_types))
    for _ in range(remaining):
        samples.append(generate_anomaly_sample())

    df = pd.DataFrame(samples)

    # Shuffle
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    return df


def main():
    """Generate all training datasets."""

    print("=" * 70)
    print("TraceFlow AI - ML Training Data Generator")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    output_dir = Path(__file__).parent

    # 1. Generate Yield Dataset
    print("\n[1/2] Generating Yield Prediction Dataset...")
    yield_df = generate_yield_dataset(n_samples=2000)

    print(f"    Generated {len(yield_df)} samples")
    print(f"    Process modes: {yield_df['process_mode'].nunique()}")
    print(f"    Materials: {yield_df['source_material'].nunique()}")
    print(
        f"    Yield range: {yield_df['yield_percent'].min():.2f}% - {yield_df['yield_percent'].max():.2f}%"
    )
    print(f"    Mean yield: {yield_df['yield_percent'].mean():.2f}%")
    print(f"    Std yield: {yield_df['yield_percent'].std():.2f}%")

    # Save yield dataset
    yield_df.to_csv(output_dir / "yield_training_data.csv", index=False)
    yield_df.to_json(
        output_dir / "yield_training_data.json", orient="records", indent=2
    )
    print(f"    Saved to: {output_dir / 'yield_training_data.csv'}")

    # Print distribution by process
    print("\n    Yield by Process Mode:")
    for mode in yield_df["process_mode"].unique():
        mode_df = yield_df[yield_df["process_mode"] == mode]
        print(
            f"      {mode}: mean={mode_df['yield_percent'].mean():.2f}%, "
            f"std={mode_df['yield_percent'].std():.2f}%, n={len(mode_df)}"
        )

    # 2. Generate Anomaly Dataset
    print("\n[2/2] Generating Anomaly Detection Dataset...")
    anomaly_df = generate_anomaly_dataset(n_normal=1500, n_anomaly=500)

    n_normal = len(anomaly_df[anomaly_df["is_anomaly"] == False])
    n_anomaly = len(anomaly_df[anomaly_df["is_anomaly"] == True])

    print(f"    Generated {len(anomaly_df)} samples")
    print(f"    Normal samples: {n_normal} ({100 * n_normal / len(anomaly_df):.1f}%)")
    print(
        f"    Anomaly samples: {n_anomaly} ({100 * n_anomaly / len(anomaly_df):.1f}%)"
    )

    # Anomaly type distribution
    print("\n    Anomaly Types:")
    anomaly_subset = anomaly_df[anomaly_df["is_anomaly"] == True]
    for atype, count in anomaly_subset["anomaly_type"].value_counts().items():
        print(f"      {atype}: {count}")

    # Save anomaly dataset
    anomaly_df.to_csv(output_dir / "anomaly_training_data.csv", index=False)
    anomaly_df.to_json(
        output_dir / "anomaly_training_data.json", orient="records", indent=2
    )
    print(f"\n    Saved to: {output_dir / 'anomaly_training_data.csv'}")

    # 3. Print summary statistics
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(
        f"Yield Dataset: 2000 samples, {yield_df['process_mode'].nunique()} process modes"
    )
    print(f"Anomaly Dataset: 2000 samples ({n_normal} normal, {n_anomaly} anomalies)")
    print(f"Output directory: {output_dir}")
    print("=" * 70)

    return yield_df, anomaly_df


if __name__ == "__main__":
    yield_df, anomaly_df = main()
