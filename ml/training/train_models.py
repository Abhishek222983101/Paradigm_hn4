"""
TraceFlow AI - ML Training Pipeline v2.0
=========================================
Professional-grade ML training with:
- XGBoost Yield Predictor with hyperparameter tuning
- Isolation Forest Anomaly Detector with optimal contamination
- Full Weights & Biases integration for experiment tracking
- Cross-validation for robust evaluation
- Feature importance analysis with visualizations
- Real-time metrics logging

For Hackathon: SYNAPSE HackNiche 4.0 (ML PS1)
"""

import json
import pickle
import warnings
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")  # Non-interactive backend for server
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, Optional, List

# Scikit-learn
from sklearn.model_selection import (
    train_test_split,
    cross_val_score,
    GridSearchCV,
    StratifiedKFold,
    KFold,
)
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    mean_squared_error,
    mean_absolute_error,
    r2_score,
    classification_report,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    roc_auc_score,
    precision_recall_curve,
    average_precision_score,
)

# XGBoost
import xgboost as xgb

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

# W&B for experiment tracking
try:
    import wandb

    WANDB_AVAILABLE = True
except ImportError:
    WANDB_AVAILABLE = False
    print("[WARNING] W&B not available. Install with: pip install wandb")

# Environment setup
from dotenv import load_dotenv
import os

# Load environment
env_path = Path(__file__).parent.parent.parent / "backend" / ".env"
load_dotenv(env_path)

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"
MODEL_DIR.mkdir(exist_ok=True)

# W&B Configuration
WANDB_PROJECT = os.getenv("WANDB_PROJECT", "traceflow-ai")
WANDB_API_KEY = os.getenv("WANDB_API_KEY")


class TraceFlowMLPipeline:
    """
    Production-grade ML Pipeline for TraceFlow AI.

    Features:
    - XGBoost Regressor for yield prediction
    - Isolation Forest for anomaly detection
    - Full W&B experiment tracking
    - Hyperparameter optimization
    - Cross-validation evaluation
    """

    def __init__(self, use_wandb: bool = True, experiment_name: str = None):
        """
        Initialize the ML pipeline.

        Args:
            use_wandb: Whether to log to Weights & Biases
            experiment_name: Custom name for this experiment run
        """
        self.use_wandb = use_wandb and WANDB_AVAILABLE
        self.experiment_name = (
            experiment_name or f"traceflow-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.scalers: Dict[str, StandardScaler] = {}

        # Model storage
        self.yield_model = None
        self.anomaly_model = None

        # Metrics storage
        self.yield_metrics: Dict = {}
        self.anomaly_metrics: Dict = {}

        print("=" * 70)
        print("TraceFlow AI - ML Training Pipeline v2.0")
        print("=" * 70)
        print(f"W&B Tracking: {'ENABLED' if self.use_wandb else 'DISABLED'}")
        print(f"Experiment: {self.experiment_name}")
        print(f"Models will be saved to: {MODEL_DIR}")
        print("=" * 70)

    def load_training_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load pre-generated training datasets."""

        print("\n[STEP 1] Loading Training Data...")

        # Load yield dataset
        yield_path = DATA_DIR / "yield_training_data.csv"
        if not yield_path.exists():
            raise FileNotFoundError(
                f"Yield training data not found at {yield_path}. Run generate_ml_training_data.py first."
            )

        self.yield_df = pd.read_csv(yield_path)
        print(f"  Yield Dataset: {len(self.yield_df)} samples")
        print(f"    Features: {list(self.yield_df.columns)}")
        print(
            f"    Yield range: {self.yield_df['yield_percent'].min():.2f}% - {self.yield_df['yield_percent'].max():.2f}%"
        )

        # Load anomaly dataset
        anomaly_path = DATA_DIR / "anomaly_training_data.csv"
        if not anomaly_path.exists():
            raise FileNotFoundError(
                f"Anomaly training data not found at {anomaly_path}. Run generate_ml_training_data.py first."
            )

        self.anomaly_df = pd.read_csv(anomaly_path)
        n_normal = len(self.anomaly_df[self.anomaly_df["is_anomaly"] == False])
        n_anomaly = len(self.anomaly_df[self.anomaly_df["is_anomaly"] == True])
        print(f"  Anomaly Dataset: {len(self.anomaly_df)} samples")
        print(f"    Normal: {n_normal}, Anomalies: {n_anomaly}")

        return self.yield_df, self.anomaly_df

    def _encode_categorical(self, df: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """Encode categorical features using LabelEncoder."""

        df_encoded = df.copy()
        categorical_cols = df.select_dtypes(include=["object"]).columns

        for col in categorical_cols:
            if fit:
                le = LabelEncoder()
                df_encoded[col] = df_encoded[col].fillna("Unknown")
                df_encoded[col] = le.fit_transform(df_encoded[col].astype(str))
                self.label_encoders[col] = le
            else:
                le = self.label_encoders.get(col)
                if le:
                    df_encoded[col] = df_encoded[col].fillna("Unknown")
                    df_encoded[col] = df_encoded[col].apply(
                        lambda x: (
                            le.transform([str(x)])[0] if str(x) in le.classes_ else -1
                        )
                    )

        return df_encoded

    def train_yield_predictor(
        self, tune_hyperparams: bool = True, cv_folds: int = 5
    ) -> Dict:
        """
        Train XGBoost model for yield prediction with full W&B logging.

        Args:
            tune_hyperparams: Whether to perform grid search
            cv_folds: Number of cross-validation folds

        Returns:
            Dictionary of evaluation metrics
        """

        print("\n" + "=" * 70)
        print("[STEP 2] Training XGBoost Yield Predictor")
        print("=" * 70)

        # Prepare features
        feature_cols = [
            "process_mode",
            "input_quantity",
            "source_material",
            "source_state",
            "source_grade",
            "scenario",
        ]
        target_col = "yield_percent"

        X = self.yield_df[feature_cols].copy()
        y = self.yield_df[target_col].values

        # Encode categorical features
        X_encoded = self._encode_categorical(X, fit=True)

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_encoded, y, test_size=0.2, random_state=42
        )

        print(f"\n  Dataset Split:")
        print(f"    Training: {len(X_train)} samples")
        print(f"    Testing: {len(X_test)} samples")
        print(f"    Features: {list(X_encoded.columns)}")

        # Initialize W&B run
        if self.use_wandb:
            wandb.init(
                project=WANDB_PROJECT,
                name=f"yield-predictor-{datetime.now().strftime('%H%M%S')}",
                config={
                    "model_type": "XGBoost",
                    "task": "yield_prediction",
                    "n_samples": len(X_encoded),
                    "n_features": X_encoded.shape[1],
                    "train_size": len(X_train),
                    "test_size": len(X_test),
                    "cv_folds": cv_folds,
                    "tune_hyperparams": tune_hyperparams,
                },
                tags=["yield", "xgboost", "regression"],
            )

        # Base parameters
        base_params = {
            "objective": "reg:squarederror",
            "eval_metric": "rmse",
            "random_state": 42,
            "n_jobs": -1,
        }

        if tune_hyperparams:
            print("\n  Hyperparameter Tuning (Grid Search)...")

            param_grid = {
                "n_estimators": [100, 200],
                "max_depth": [4, 6, 8],
                "learning_rate": [0.05, 0.1],
                "min_child_weight": [1, 3],
                "subsample": [0.8, 0.9],
                "colsample_bytree": [0.8, 0.9],
            }

            grid_search = GridSearchCV(
                xgb.XGBRegressor(**base_params),
                param_grid,
                cv=cv_folds,
                scoring="r2",
                n_jobs=-1,
                verbose=1,
            )

            grid_search.fit(X_train, y_train)
            best_params = grid_search.best_params_

            print(f"\n  Best Parameters Found:")
            for param, value in best_params.items():
                print(f"    {param}: {value}")

            self.yield_model = grid_search.best_estimator_

            if self.use_wandb:
                wandb.config.update({"best_params": best_params})
        else:
            # Use reasonable defaults
            best_params = {
                "n_estimators": 200,
                "max_depth": 6,
                "learning_rate": 0.1,
                "min_child_weight": 1,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
            }

            self.yield_model = xgb.XGBRegressor(**base_params, **best_params)
            self.yield_model.fit(
                X_train,
                y_train,
                eval_set=[(X_train, y_train), (X_test, y_test)],
                verbose=False,
            )

        # Cross-validation evaluation
        print(f"\n  Cross-Validation ({cv_folds} folds)...")
        cv_scores_r2 = cross_val_score(
            self.yield_model, X_encoded, y, cv=cv_folds, scoring="r2"
        )
        cv_scores_mae = -cross_val_score(
            self.yield_model,
            X_encoded,
            y,
            cv=cv_folds,
            scoring="neg_mean_absolute_error",
        )

        print(f"    R² Scores: {cv_scores_r2}")
        print(
            f"    Mean R²: {cv_scores_r2.mean():.4f} (+/- {cv_scores_r2.std() * 2:.4f})"
        )
        print(
            f"    Mean MAE: {cv_scores_mae.mean():.4f} (+/- {cv_scores_mae.std() * 2:.4f})"
        )

        # Final evaluation on test set
        y_pred = self.yield_model.predict(X_test)

        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)

        # Store metrics
        self.yield_metrics = {
            "mse": float(mse),
            "rmse": float(rmse),
            "mae": float(mae),
            "r2": float(r2),
            "cv_r2_mean": float(cv_scores_r2.mean()),
            "cv_r2_std": float(cv_scores_r2.std()),
            "cv_mae_mean": float(cv_scores_mae.mean()),
            "cv_mae_std": float(cv_scores_mae.std()),
        }

        print(f"\n  Test Set Results:")
        print(f"    MSE:  {mse:.4f}")
        print(f"    RMSE: {rmse:.4f}%")
        print(f"    MAE:  {mae:.4f}%")
        print(
            f"    R²:   {r2:.4f} {'[EXCELLENT]' if r2 > 0.9 else '[GOOD]' if r2 > 0.7 else '[NEEDS IMPROVEMENT]' if r2 > 0.5 else '[POOR]'}"
        )

        # Feature importance
        importance = dict(zip(X_encoded.columns, self.yield_model.feature_importances_))
        sorted_importance = sorted(importance.items(), key=lambda x: x[1], reverse=True)

        print(f"\n  Feature Importance:")
        for feat, imp in sorted_importance:
            bar = "█" * int(imp * 50)
            print(f"    {feat:20s}: {imp:.4f} {bar}")

        # Generate and save plots
        self._generate_yield_plots(X_encoded, y, y_test, y_pred, importance)

        # Log to W&B
        if self.use_wandb:
            wandb.log(
                {
                    "yield_mse": mse,
                    "yield_rmse": rmse,
                    "yield_mae": mae,
                    "yield_r2": r2,
                    "yield_cv_r2_mean": cv_scores_r2.mean(),
                    "yield_cv_r2_std": cv_scores_r2.std(),
                }
            )

            # Log feature importance as bar chart
            wandb.log(
                {
                    "feature_importance": wandb.plot.bar(
                        wandb.Table(
                            data=[[k, v] for k, v in sorted_importance],
                            columns=["feature", "importance"],
                        ),
                        "feature",
                        "importance",
                        title="Feature Importance",
                    )
                }
            )

            # Log prediction scatter plot
            wandb.log(
                {
                    "predictions_vs_actual": wandb.plot.scatter(
                        wandb.Table(
                            data=[[a, p] for a, p in zip(y_test[:200], y_pred[:200])],
                            columns=["actual", "predicted"],
                        ),
                        "actual",
                        "predicted",
                        title="Predictions vs Actual Yield",
                    )
                }
            )

            # Log saved plot images
            plot_path = MODEL_DIR / "yield_analysis.png"
            if plot_path.exists():
                wandb.log({"yield_analysis_plot": wandb.Image(str(plot_path))})

            wandb.finish()

        # Save model
        self._save_yield_model(X_encoded.columns.tolist())

        return self.yield_metrics

    def _generate_yield_plots(
        self,
        X: pd.DataFrame,
        y: np.ndarray,
        y_test: np.ndarray,
        y_pred: np.ndarray,
        importance: Dict,
    ) -> None:
        """Generate and save yield prediction analysis plots."""

        fig, axes = plt.subplots(2, 2, figsize=(14, 12))
        fig.suptitle(
            "TraceFlow AI - Yield Predictor Analysis", fontsize=14, fontweight="bold"
        )

        # 1. Predictions vs Actual
        ax1 = axes[0, 0]
        ax1.scatter(y_test, y_pred, alpha=0.5, s=20)
        ax1.plot([0, 100], [0, 100], "r--", linewidth=2, label="Perfect Prediction")
        ax1.set_xlabel("Actual Yield (%)")
        ax1.set_ylabel("Predicted Yield (%)")
        ax1.set_title("Predictions vs Actual")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 2. Residuals distribution
        ax2 = axes[0, 1]
        residuals = y_test - y_pred
        ax2.hist(residuals, bins=50, edgecolor="black", alpha=0.7)
        ax2.axvline(x=0, color="r", linestyle="--", linewidth=2)
        ax2.set_xlabel("Residual (Actual - Predicted)")
        ax2.set_ylabel("Frequency")
        ax2.set_title(f"Residuals Distribution (Mean: {residuals.mean():.2f})")
        ax2.grid(True, alpha=0.3)

        # 3. Feature Importance
        ax3 = axes[1, 0]
        sorted_imp = sorted(importance.items(), key=lambda x: x[1], reverse=True)
        features = [x[0] for x in sorted_imp]
        importances = [x[1] for x in sorted_imp]
        colors = plt.cm.viridis(np.linspace(0, 1, len(features)))
        ax3.barh(features, importances, color=colors)
        ax3.set_xlabel("Importance")
        ax3.set_title("Feature Importance")
        ax3.invert_yaxis()

        # 4. Yield Distribution by Process
        ax4 = axes[1, 1]
        process_yields = self.yield_df.groupby("process_mode")["yield_percent"].agg(
            ["mean", "std"]
        )
        process_yields = process_yields.sort_values("mean", ascending=True)
        ax4.barh(
            process_yields.index,
            process_yields["mean"],
            xerr=process_yields["std"],
            capsize=3,
            alpha=0.7,
        )
        ax4.set_xlabel("Mean Yield (%)")
        ax4.set_title("Yield by Process Type")
        ax4.axvline(x=90, color="g", linestyle="--", alpha=0.5, label="90% threshold")
        ax4.legend()

        plt.tight_layout()
        plt.savefig(MODEL_DIR / "yield_analysis.png", dpi=150, bbox_inches="tight")
        plt.close()

        print(f"\n  Saved analysis plot to: {MODEL_DIR / 'yield_analysis.png'}")

    def _save_yield_model(self, feature_columns: List[str]) -> None:
        """Save the yield predictor model and metadata."""

        model_data = {
            "model": self.yield_model,
            "label_encoders": self.label_encoders.copy(),
            "feature_columns": feature_columns,
            "metrics": self.yield_metrics,
            "training_date": datetime.now().isoformat(),
            "version": "2.0",
        }

        model_path = MODEL_DIR / "yield_predictor.pkl"
        with open(model_path, "wb") as f:
            pickle.dump(model_data, f)

        print(f"\n  Saved yield predictor to: {model_path}")

    def train_anomaly_detector(
        self, contamination: float = 0.25, cv_folds: int = 5
    ) -> Dict:
        """
        Train Isolation Forest for anomaly detection with full W&B logging.

        Args:
            contamination: Expected proportion of anomalies
            cv_folds: Number of cross-validation folds

        Returns:
            Dictionary of evaluation metrics
        """

        print("\n" + "=" * 70)
        print("[STEP 3] Training Isolation Forest Anomaly Detector")
        print("=" * 70)

        # Prepare features
        feature_cols = ["process_mode", "loss_percent", "quantity"]
        X = self.anomaly_df[feature_cols].copy()
        y_true = self.anomaly_df["is_anomaly"].astype(int).values

        # Encode categorical features
        X_encoded = self._encode_categorical(X, fit=True)

        # Scale numerical features for Isolation Forest
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_encoded)
        self.scalers["anomaly"] = scaler

        print(f"\n  Dataset:")
        print(f"    Total samples: {len(X_encoded)}")
        print(f"    Normal: {(y_true == 0).sum()}")
        print(f"    Anomalies: {(y_true == 1).sum()}")
        print(f"    Features: {feature_cols}")

        # Initialize W&B run
        if self.use_wandb:
            wandb.init(
                project=WANDB_PROJECT,
                name=f"anomaly-detector-{datetime.now().strftime('%H%M%S')}",
                config={
                    "model_type": "IsolationForest",
                    "task": "anomaly_detection",
                    "n_samples": len(X_encoded),
                    "n_normal": int((y_true == 0).sum()),
                    "n_anomaly": int((y_true == 1).sum()),
                    "contamination": contamination,
                },
                tags=["anomaly", "isolation_forest", "classification"],
            )

        # Train Isolation Forest
        print(f"\n  Training Isolation Forest...")
        print(f"    contamination: {contamination}")
        print(f"    n_estimators: 200")

        self.anomaly_model = IsolationForest(
            n_estimators=200,
            contamination=contamination,
            random_state=42,
            max_samples="auto",
            n_jobs=-1,
            verbose=0,
        )

        self.anomaly_model.fit(X_scaled)

        # Predictions (-1 for anomaly, 1 for normal in sklearn)
        y_pred_raw = self.anomaly_model.predict(X_scaled)
        y_pred = (y_pred_raw == -1).astype(int)  # Convert to 0/1 (0=normal, 1=anomaly)

        # Anomaly scores (higher = more anomalous)
        anomaly_scores = -self.anomaly_model.decision_function(X_scaled)

        # Calculate threshold (percentile based)
        threshold = np.percentile(anomaly_scores, 100 * (1 - contamination))

        # Metrics
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)

        # ROC AUC using anomaly scores
        try:
            roc_auc = roc_auc_score(y_true, anomaly_scores)
        except:
            roc_auc = 0.0

        # Average Precision
        try:
            avg_precision = average_precision_score(y_true, anomaly_scores)
        except:
            avg_precision = 0.0

        # Confusion Matrix
        cm = confusion_matrix(y_true, y_pred)

        # Store metrics
        self.anomaly_metrics = {
            "precision": float(precision),
            "recall": float(recall),
            "f1_score": float(f1),
            "roc_auc": float(roc_auc),
            "avg_precision": float(avg_precision),
            "threshold": float(threshold),
            "confusion_matrix": cm.tolist(),
        }

        print(f"\n  Results:")
        print(f"    Precision: {precision:.4f}")
        print(f"    Recall:    {recall:.4f}")
        print(f"    F1 Score:  {f1:.4f}")
        print(f"    ROC AUC:   {roc_auc:.4f}")
        print(f"    Avg Precision: {avg_precision:.4f}")

        print(f"\n  Confusion Matrix:")
        print(f"                  Predicted")
        print(f"                Normal  Anomaly")
        print(f"    Actual Normal  {cm[0, 0]:5d}   {cm[0, 1]:5d}")
        print(f"    Actual Anomaly {cm[1, 0]:5d}   {cm[1, 1]:5d}")

        print(f"\n  Classification Report:")
        print(classification_report(y_true, y_pred, target_names=["Normal", "Anomaly"]))

        # Anomaly score statistics
        print(f"\n  Anomaly Score Statistics:")
        print(f"    Min:    {anomaly_scores.min():.4f}")
        print(f"    Max:    {anomaly_scores.max():.4f}")
        print(f"    Mean:   {anomaly_scores.mean():.4f}")
        print(f"    Std:    {anomaly_scores.std():.4f}")
        print(f"    Threshold: {threshold:.4f}")

        # Generate plots
        self._generate_anomaly_plots(anomaly_scores, y_true, y_pred, threshold)

        # Log to W&B
        if self.use_wandb:
            wandb.log(
                {
                    "anomaly_precision": precision,
                    "anomaly_recall": recall,
                    "anomaly_f1": f1,
                    "anomaly_roc_auc": roc_auc,
                    "anomaly_avg_precision": avg_precision,
                    "anomaly_threshold": threshold,
                }
            )

            # Log confusion matrix
            wandb.log(
                {
                    "confusion_matrix": wandb.plot.confusion_matrix(
                        probs=None,
                        y_true=y_true,
                        preds=y_pred,
                        class_names=["Normal", "Anomaly"],
                    )
                }
            )

            # Log ROC curve
            wandb.log(
                {
                    "roc_curve": wandb.plot.roc_curve(
                        y_true,
                        np.column_stack(
                            [
                                1 - anomaly_scores / anomaly_scores.max(),
                                anomaly_scores / anomaly_scores.max(),
                            ]
                        ),
                        labels=["Normal", "Anomaly"],
                    )
                }
            )

            # Log saved plot
            plot_path = MODEL_DIR / "anomaly_analysis.png"
            if plot_path.exists():
                wandb.log({"anomaly_analysis_plot": wandb.Image(str(plot_path))})

            wandb.finish()

        # Save model
        self._save_anomaly_model(feature_cols, threshold)

        return self.anomaly_metrics

    def _generate_anomaly_plots(
        self,
        scores: np.ndarray,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        threshold: float,
    ) -> None:
        """Generate and save anomaly detection analysis plots."""

        fig, axes = plt.subplots(2, 2, figsize=(14, 12))
        fig.suptitle(
            "TraceFlow AI - Anomaly Detector Analysis", fontsize=14, fontweight="bold"
        )

        # 1. Score Distribution
        ax1 = axes[0, 0]
        ax1.hist(scores[y_true == 0], bins=50, alpha=0.7, label="Normal", color="green")
        ax1.hist(scores[y_true == 1], bins=50, alpha=0.7, label="Anomaly", color="red")
        ax1.axvline(
            x=threshold,
            color="black",
            linestyle="--",
            linewidth=2,
            label=f"Threshold ({threshold:.2f})",
        )
        ax1.set_xlabel("Anomaly Score")
        ax1.set_ylabel("Frequency")
        ax1.set_title("Anomaly Score Distribution")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 2. Confusion Matrix Heatmap
        ax2 = axes[0, 1]
        cm = confusion_matrix(y_true, y_pred)
        im = ax2.imshow(cm, cmap="Blues")
        ax2.set_xticks([0, 1])
        ax2.set_yticks([0, 1])
        ax2.set_xticklabels(["Normal", "Anomaly"])
        ax2.set_yticklabels(["Normal", "Anomaly"])
        ax2.set_xlabel("Predicted")
        ax2.set_ylabel("Actual")
        ax2.set_title("Confusion Matrix")

        for i in range(2):
            for j in range(2):
                ax2.text(
                    j,
                    i,
                    str(cm[i, j]),
                    ha="center",
                    va="center",
                    fontsize=20,
                    fontweight="bold",
                )

        plt.colorbar(im, ax=ax2)

        # 3. Precision-Recall Curve
        ax3 = axes[1, 0]
        precision_curve, recall_curve, _ = precision_recall_curve(y_true, scores)
        ax3.plot(recall_curve, precision_curve, linewidth=2)
        ax3.fill_between(recall_curve, precision_curve, alpha=0.3)
        ax3.set_xlabel("Recall")
        ax3.set_ylabel("Precision")
        ax3.set_title(
            f"Precision-Recall Curve (AP: {average_precision_score(y_true, scores):.3f})"
        )
        ax3.grid(True, alpha=0.3)

        # 4. Score Box Plot by Class
        ax4 = axes[1, 1]
        normal_scores = scores[y_true == 0]
        anomaly_scores_true = scores[y_true == 1]
        bp = ax4.boxplot(
            [normal_scores, anomaly_scores_true],
            labels=["Normal", "Anomaly"],
            patch_artist=True,
        )
        bp["boxes"][0].set_facecolor("green")
        bp["boxes"][1].set_facecolor("red")
        ax4.axhline(
            y=threshold, color="black", linestyle="--", linewidth=2, label=f"Threshold"
        )
        ax4.set_ylabel("Anomaly Score")
        ax4.set_title("Score Distribution by Class")
        ax4.legend()
        ax4.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(MODEL_DIR / "anomaly_analysis.png", dpi=150, bbox_inches="tight")
        plt.close()

        print(f"\n  Saved analysis plot to: {MODEL_DIR / 'anomaly_analysis.png'}")

    def _save_anomaly_model(self, feature_columns: List[str], threshold: float) -> None:
        """Save the anomaly detector model and metadata."""

        model_data = {
            "model": self.anomaly_model,
            "label_encoders": {
                k: v for k, v in self.label_encoders.items() if k in feature_columns
            },
            "scaler": self.scalers.get("anomaly"),
            "feature_columns": feature_columns,
            "threshold": threshold,
            "metrics": self.anomaly_metrics,
            "training_date": datetime.now().isoformat(),
            "version": "2.0",
        }

        model_path = MODEL_DIR / "anomaly_detector.pkl"
        with open(model_path, "wb") as f:
            pickle.dump(model_data, f)

        print(f"\n  Saved anomaly detector to: {model_path}")

    def run_full_pipeline(
        self, tune_hyperparams: bool = True, cv_folds: int = 5
    ) -> Dict:
        """
        Run the complete ML training pipeline.

        Args:
            tune_hyperparams: Whether to tune hyperparameters
            cv_folds: Number of cross-validation folds

        Returns:
            Dictionary with all metrics
        """

        start_time = datetime.now()
        print(f"\nPipeline started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Step 1: Load data
        self.load_training_data()

        # Step 2: Train yield predictor
        yield_metrics = self.train_yield_predictor(
            tune_hyperparams=tune_hyperparams, cv_folds=cv_folds
        )

        # Step 3: Train anomaly detector
        anomaly_metrics = self.train_anomaly_detector(cv_folds=cv_folds)

        # Summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print("\n" + "=" * 70)
        print("TRAINING COMPLETE!")
        print("=" * 70)
        print(f"Duration: {duration:.1f} seconds")
        print(f"\nYield Predictor:")
        print(f"  R² Score: {yield_metrics['r2']:.4f}")
        print(f"  MAE: {yield_metrics['mae']:.4f}%")
        print(f"  RMSE: {yield_metrics['rmse']:.4f}%")
        print(f"\nAnomaly Detector:")
        print(f"  F1 Score: {anomaly_metrics['f1_score']:.4f}")
        print(f"  Precision: {anomaly_metrics['precision']:.4f}")
        print(f"  Recall: {anomaly_metrics['recall']:.4f}")
        print(f"  ROC AUC: {anomaly_metrics['roc_auc']:.4f}")
        print(f"\nModels saved to: {MODEL_DIR}")
        print("=" * 70)

        # Save summary
        summary = {
            "experiment_name": self.experiment_name,
            "training_date": end_time.isoformat(),
            "duration_seconds": duration,
            "yield_metrics": yield_metrics,
            "anomaly_metrics": anomaly_metrics,
        }

        with open(MODEL_DIR / "training_summary.json", "w") as f:
            json.dump(summary, f, indent=2)

        return summary


def main():
    """Main entry point for training."""

    # Check if W&B is configured
    if WANDB_API_KEY:
        print(f"W&B API Key found: {WANDB_API_KEY[:20]}...")
        # Login to W&B
        if WANDB_AVAILABLE:
            wandb.login(key=WANDB_API_KEY)
    else:
        print("[WARNING] WANDB_API_KEY not found in environment")

    # Initialize and run pipeline
    pipeline = TraceFlowMLPipeline(use_wandb=True)
    results = pipeline.run_full_pipeline(
        tune_hyperparams=True,  # Enable grid search for best params
        cv_folds=5,  # 5-fold cross-validation
    )

    return results


if __name__ == "__main__":
    results = main()
