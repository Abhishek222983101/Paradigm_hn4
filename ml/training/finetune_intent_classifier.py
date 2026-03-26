"""
TraceFlow AI - LLM Fine-Tuning Pipeline
========================================
Fine-tunes a small LLM (DistilBERT) for Intent Classification using PEFT/LoRA
Optimized for hackathon demonstration with full W&B integration.

This script:
1. Loads domain-specific intent classification data
2. Fine-tunes DistilBERT with LoRA for parameter-efficient training
3. Logs all metrics, loss curves, and confusion matrices to W&B
4. Saves the fine-tuned model for inference

For Hackathon: SYNAPSE HackNiche 4.0 (ML PS1)
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Suppress warnings
warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# PyTorch
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

# Transformers & PEFT
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    DataCollatorWithPadding,
    EarlyStoppingCallback,
)
from peft import (
    LoraConfig,
    get_peft_model,
    TaskType,
    PeftModel,
)
from datasets import Dataset as HFDataset

# Sklearn for metrics
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
    classification_report,
)
from sklearn.preprocessing import LabelEncoder

# W&B
try:
    import wandb

    WANDB_AVAILABLE = True
except ImportError:
    WANDB_AVAILABLE = False
    print("[WARNING] W&B not available")

# Environment
from dotenv import load_dotenv

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models" / "intent_classifier"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# Load environment
env_path = BASE_DIR.parent / "backend" / ".env"
load_dotenv(env_path)

WANDB_PROJECT = os.getenv("WANDB_PROJECT", "traceflow-ai")
WANDB_API_KEY = os.getenv("WANDB_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")

# Configuration
CONFIG = {
    # Model
    "base_model": "distilbert-base-uncased",  # Small, fast, good for classification
    "max_length": 128,
    # LoRA Configuration
    "lora_r": 16,
    "lora_alpha": 32,
    "lora_dropout": 0.1,
    "lora_target_modules": ["q_lin", "v_lin"],  # DistilBERT attention modules
    # Training
    "num_epochs": 5,
    "batch_size": 16,
    "learning_rate": 2e-4,
    "weight_decay": 0.01,
    "warmup_ratio": 0.1,
    "gradient_accumulation_steps": 2,
    # Evaluation
    "eval_steps": 50,
    "save_steps": 100,
    "logging_steps": 10,
}


class IntentDataset(Dataset):
    """PyTorch Dataset for Intent Classification."""

    def __init__(
        self, texts: List[str], labels: List[int], tokenizer, max_length: int = 128
    ):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]

        encoding = self.tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
            return_tensors="pt",
        )

        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "labels": torch.tensor(label, dtype=torch.long),
        }


def load_intent_data() -> Tuple[List[str], List[str]]:
    """Load intent classification training data."""

    data_path = DATA_DIR / "intent_training_data.json"

    if not data_path.exists():
        raise FileNotFoundError(f"Intent training data not found at {data_path}")

    with open(data_path, "r") as f:
        data = json.load(f)

    texts = [item["text"] for item in data]
    intents = [item["intent"] for item in data]

    print(f"Loaded {len(texts)} training samples")
    print(f"Unique intents: {len(set(intents))}")

    return texts, intents


def compute_metrics(eval_pred):
    """Compute metrics for evaluation."""
    predictions, labels = eval_pred
    predictions = np.argmax(predictions, axis=1)

    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predictions, average="weighted", zero_division=0
    )
    accuracy = accuracy_score(labels, predictions)

    return {
        "accuracy": accuracy,
        "f1": f1,
        "precision": precision,
        "recall": recall,
    }


class TraceFlowIntentClassifierTrainer:
    """
    Fine-tuning pipeline for Intent Classification using LoRA.
    """

    def __init__(self, use_wandb: bool = True):
        self.use_wandb = use_wandb and WANDB_AVAILABLE
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        print("=" * 70)
        print("TraceFlow AI - Intent Classifier Fine-Tuning")
        print("=" * 70)
        print(f"Device: {self.device}")
        if torch.cuda.is_available():
            print(f"GPU: {torch.cuda.get_device_name(0)}")
            print(
                f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB"
            )
        print(f"W&B Tracking: {'ENABLED' if self.use_wandb else 'DISABLED'}")
        print(f"Base Model: {CONFIG['base_model']}")
        print(f"LoRA Rank: {CONFIG['lora_r']}")
        print("=" * 70)

    def prepare_data(self) -> Tuple[HFDataset, HFDataset, LabelEncoder]:
        """Load and prepare training data."""

        print("\n[STEP 1] Loading and preparing data...")

        # Load data
        texts, intents = load_intent_data()

        # Encode labels
        self.label_encoder = LabelEncoder()
        labels = self.label_encoder.fit_transform(intents)

        self.num_labels = len(self.label_encoder.classes_)
        self.label_names = list(self.label_encoder.classes_)

        print(f"  Number of classes: {self.num_labels}")
        print(f"  Classes: {self.label_names}")

        # Split data
        train_texts, val_texts, train_labels, val_labels = train_test_split(
            texts, labels, test_size=0.15, random_state=42, stratify=labels
        )

        print(f"  Training samples: {len(train_texts)}")
        print(f"  Validation samples: {len(val_texts)}")

        # Create HuggingFace datasets
        train_dataset = HFDataset.from_dict(
            {"text": train_texts, "label": train_labels.tolist()}
        )

        val_dataset = HFDataset.from_dict(
            {"text": val_texts, "label": val_labels.tolist()}
        )

        return train_dataset, val_dataset, self.label_encoder

    def setup_model(self):
        """Initialize tokenizer, model, and LoRA configuration."""

        print("\n[STEP 2] Setting up model and LoRA...")

        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(CONFIG["base_model"])

        # Load base model
        self.model = AutoModelForSequenceClassification.from_pretrained(
            CONFIG["base_model"],
            num_labels=self.num_labels,
            id2label={i: label for i, label in enumerate(self.label_names)},
            label2id={label: i for i, label in enumerate(self.label_names)},
        )

        # Configure LoRA
        lora_config = LoraConfig(
            task_type=TaskType.SEQ_CLS,
            r=CONFIG["lora_r"],
            lora_alpha=CONFIG["lora_alpha"],
            lora_dropout=CONFIG["lora_dropout"],
            target_modules=CONFIG["lora_target_modules"],
            bias="none",
        )

        # Apply LoRA
        self.model = get_peft_model(self.model, lora_config)
        self.model.print_trainable_parameters()

        # Move to device
        self.model.to(self.device)

        print(f"  Model loaded on {self.device}")

        return self.tokenizer, self.model

    def tokenize_function(self, examples):
        """Tokenize text examples."""
        return self.tokenizer(
            examples["text"],
            truncation=True,
            padding="max_length",
            max_length=CONFIG["max_length"],
        )

    def train(self, train_dataset: HFDataset, val_dataset: HFDataset):
        """Run the fine-tuning process."""

        print("\n[STEP 3] Starting fine-tuning...")

        # Tokenize datasets
        train_tokenized = train_dataset.map(self.tokenize_function, batched=True)
        val_tokenized = val_dataset.map(self.tokenize_function, batched=True)

        # Remove text column and set format
        train_tokenized = train_tokenized.remove_columns(["text"])
        val_tokenized = val_tokenized.remove_columns(["text"])

        train_tokenized.set_format("torch")
        val_tokenized.set_format("torch")

        # Data collator
        data_collator = DataCollatorWithPadding(tokenizer=self.tokenizer)

        # Training arguments
        training_args = TrainingArguments(
            output_dir=str(MODEL_DIR / "checkpoints"),
            num_train_epochs=CONFIG["num_epochs"],
            per_device_train_batch_size=CONFIG["batch_size"],
            per_device_eval_batch_size=CONFIG["batch_size"],
            learning_rate=CONFIG["learning_rate"],
            weight_decay=CONFIG["weight_decay"],
            warmup_ratio=CONFIG["warmup_ratio"],
            gradient_accumulation_steps=CONFIG["gradient_accumulation_steps"],
            eval_strategy="steps",
            eval_steps=CONFIG["eval_steps"],
            save_strategy="steps",
            save_steps=CONFIG["save_steps"],
            logging_steps=CONFIG["logging_steps"],
            load_best_model_at_end=True,
            metric_for_best_model="f1",
            greater_is_better=True,
            report_to="wandb" if self.use_wandb else "none",
            run_name=f"intent-classifier-{datetime.now().strftime('%H%M%S')}",
            fp16=torch.cuda.is_available(),  # Mixed precision if GPU available
            dataloader_num_workers=2,
            remove_unused_columns=False,
        )

        # Initialize W&B
        if self.use_wandb:
            wandb.init(
                project=WANDB_PROJECT,
                name=f"intent-classifier-lora-{datetime.now().strftime('%H%M%S')}",
                config={
                    **CONFIG,
                    "num_labels": self.num_labels,
                    "train_samples": len(train_dataset),
                    "val_samples": len(val_dataset),
                },
                tags=["intent-classification", "lora", "fine-tuning", "distilbert"],
            )

        # Initialize Trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_tokenized,
            eval_dataset=val_tokenized,
            processing_class=self.tokenizer,
            data_collator=data_collator,
            compute_metrics=compute_metrics,
            callbacks=[EarlyStoppingCallback(early_stopping_patience=3)],
        )

        # Train!
        print("\n  Starting training loop...")
        train_result = trainer.train()

        # Evaluate
        print("\n[STEP 4] Final evaluation...")
        eval_results = trainer.evaluate()

        print(f"\n  Final Results:")
        print(f"    Accuracy: {eval_results['eval_accuracy']:.4f}")
        print(f"    F1 Score: {eval_results['eval_f1']:.4f}")
        print(f"    Precision: {eval_results['eval_precision']:.4f}")
        print(f"    Recall: {eval_results['eval_recall']:.4f}")

        # Store metrics
        self.metrics = {
            "accuracy": float(eval_results["eval_accuracy"]),
            "f1": float(eval_results["eval_f1"]),
            "precision": float(eval_results["eval_precision"]),
            "recall": float(eval_results["eval_recall"]),
            "train_loss": float(train_result.training_loss),
        }

        # Generate predictions for confusion matrix
        predictions = trainer.predict(val_tokenized)
        pred_labels = np.argmax(predictions.predictions, axis=1)
        true_labels = predictions.label_ids

        # Confusion matrix
        cm = confusion_matrix(true_labels, pred_labels)

        # Log to W&B
        if self.use_wandb:
            # Log confusion matrix
            wandb.log(
                {
                    "confusion_matrix": wandb.plot.confusion_matrix(
                        probs=None,
                        y_true=true_labels.tolist(),
                        preds=pred_labels.tolist(),
                        class_names=self.label_names,
                    )
                }
            )

            # Log final metrics
            wandb.log(
                {
                    "final_accuracy": self.metrics["accuracy"],
                    "final_f1": self.metrics["f1"],
                    "final_precision": self.metrics["precision"],
                    "final_recall": self.metrics["recall"],
                }
            )

        # Print classification report
        print("\n  Classification Report:")
        print(
            classification_report(
                true_labels, pred_labels, target_names=self.label_names
            )
        )

        return trainer, self.metrics

    def save_model(self):
        """Save the fine-tuned model and metadata."""

        print("\n[STEP 5] Saving model...")

        # Save LoRA adapter
        self.model.save_pretrained(MODEL_DIR / "lora_adapter")

        # Save tokenizer
        self.tokenizer.save_pretrained(MODEL_DIR / "tokenizer")

        # Save label encoder and config
        config = {
            "base_model": CONFIG["base_model"],
            "num_labels": self.num_labels,
            "label_names": self.label_names,
            "label2id": {label: i for i, label in enumerate(self.label_names)},
            "id2label": {i: label for i, label in enumerate(self.label_names)},
            "metrics": self.metrics,
            "training_date": datetime.now().isoformat(),
            "lora_config": {
                "r": CONFIG["lora_r"],
                "alpha": CONFIG["lora_alpha"],
                "dropout": CONFIG["lora_dropout"],
            },
        }

        with open(MODEL_DIR / "config.json", "w") as f:
            json.dump(config, f, indent=2)

        print(f"  Saved LoRA adapter to: {MODEL_DIR / 'lora_adapter'}")
        print(f"  Saved tokenizer to: {MODEL_DIR / 'tokenizer'}")
        print(f"  Saved config to: {MODEL_DIR / 'config.json'}")

        return MODEL_DIR

    def run_pipeline(self):
        """Run the complete fine-tuning pipeline."""

        start_time = datetime.now()

        # Step 1: Prepare data
        train_dataset, val_dataset, label_encoder = self.prepare_data()

        # Step 2: Setup model
        self.setup_model()

        # Step 3-4: Train and evaluate
        trainer, metrics = self.train(train_dataset, val_dataset)

        # Step 5: Save model
        self.save_model()

        # Finish W&B
        if self.use_wandb:
            wandb.finish()

        # Summary
        duration = (datetime.now() - start_time).total_seconds()

        print("\n" + "=" * 70)
        print("FINE-TUNING COMPLETE!")
        print("=" * 70)
        print(f"Duration: {duration:.1f} seconds")
        print(f"\nFinal Metrics:")
        print(f"  Accuracy: {metrics['accuracy']:.4f}")
        print(f"  F1 Score: {metrics['f1']:.4f}")
        print(f"  Precision: {metrics['precision']:.4f}")
        print(f"  Recall: {metrics['recall']:.4f}")
        print(f"\nModel saved to: {MODEL_DIR}")
        print("=" * 70)

        return metrics


class IntentClassifierInference:
    """
    Inference class for the fine-tuned intent classifier.
    Designed for easy integration with the existing NLP Router.
    """

    def __init__(self, model_dir: Path = MODEL_DIR):
        self.model_dir = Path(model_dir)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.tokenizer = None
        self.config = None

        self.load_model()

    def load_model(self):
        """Load the fine-tuned model for inference."""

        config_path = self.model_dir / "config.json"

        if not config_path.exists():
            print(f"[WARNING] Fine-tuned model not found at {self.model_dir}")
            return False

        # Load config
        with open(config_path, "r") as f:
            self.config = json.load(f)

        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir / "tokenizer")

        # Load base model with classification head
        base_model = AutoModelForSequenceClassification.from_pretrained(
            self.config["base_model"],
            num_labels=self.config["num_labels"],
            id2label=self.config["id2label"],
            label2id=self.config["label2id"],
        )

        # Load LoRA adapter
        self.model = PeftModel.from_pretrained(
            base_model, self.model_dir / "lora_adapter"
        )
        self.model.to(self.device)
        self.model.eval()

        print(f"[ML] Loaded intent classifier from {self.model_dir}")
        print(f"     Accuracy: {self.config['metrics'].get('accuracy', 'N/A')}")

        return True

    def classify(self, text: str) -> Dict:
        """
        Classify the intent of a given text.

        Args:
            text: Input text to classify

        Returns:
            Dictionary with predicted intent, confidence, and all scores
        """
        if self.model is None:
            return {"error": "Model not loaded", "intent": "unknown", "confidence": 0.0}

        # Tokenize
        inputs = self.tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=128,
            return_tensors="pt",
        ).to(self.device)

        # Predict
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1)[0]

        # Get top prediction
        top_prob, top_idx = torch.max(probs, dim=0)
        predicted_intent = self.config["id2label"][str(top_idx.item())]
        confidence = top_prob.item()

        # Get all scores
        all_scores = {
            self.config["id2label"][str(i)]: float(probs[i]) for i in range(len(probs))
        }

        return {
            "intent": predicted_intent,
            "confidence": round(confidence, 4),
            "all_scores": all_scores,
        }

    def classify_batch(self, texts: List[str]) -> List[Dict]:
        """Classify multiple texts at once."""
        return [self.classify(text) for text in texts]


# Singleton for inference
_classifier = None


def get_intent_classifier() -> IntentClassifierInference:
    """Get or create the intent classifier singleton."""
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifierInference()
    return _classifier


def main():
    """Main entry point."""

    # Login to W&B
    if WANDB_API_KEY and WANDB_AVAILABLE:
        wandb.login(key=WANDB_API_KEY)
        print(f"W&B logged in: {WANDB_API_KEY[:20]}...")

    # Run training pipeline
    trainer = TraceFlowIntentClassifierTrainer(use_wandb=True)
    metrics = trainer.run_pipeline()

    # Test inference
    print("\n" + "=" * 70)
    print("Testing Inference")
    print("=" * 70)

    classifier = IntentClassifierInference()

    test_texts = [
        "We received 500 kg of PET from EcoPlast",
        "How much HDPE do we have in stock?",
        "Show me the transaction history for last week",
        "Trace batch B-1234",
        "Hello, how can you help me?",
        "Check stock levels",
        "Washed 1000 kg of mixed plastics",
    ]

    print("\nTest Classifications:")
    for text in test_texts:
        result = classifier.classify(text)
        print(f'\n  Input: "{text}"')
        print(f"  Intent: {result['intent']}")
        print(f"  Confidence: {result['confidence']:.2%}")

    return metrics


if __name__ == "__main__":
    metrics = main()
