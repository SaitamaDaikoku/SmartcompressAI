import json
import sys
import types
from pathlib import Path
from typing import Dict, Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Windows WDAC compatibility: stub unused _libsvm_sparse if blocked by policy
if "sklearn.svm._libsvm_sparse" not in sys.modules:
    sys.modules["sklearn.svm._libsvm_sparse"] = types.ModuleType("sklearn.svm._libsvm_sparse")

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from config import Config
from dataset.generate_dataset import generate_dataset


def train_model(
    dataset_csv: Path = Config.DATASET_PATH,
    model_output: Path = Config.MODEL_PATH
) -> Dict[str, Any]:
    """
    Train and evaluate a Random Forest model on experimental compression measurements.
    """
    if not dataset_csv.exists():
        print(f"[Model Training] Dataset not found at {dataset_csv}. Generating now...")
        generate_dataset(dataset_csv)

    df = pd.read_csv(dataset_csv)
    print(f"[Model Training] Loaded dataset with {len(df)} samples.")

    # Define feature set and target
    feature_cols = ["file_size", "entropy", "category", "extension", "preference"]
    target_col = "best_algorithm"

    X = df[feature_cols]
    y = df[target_col]

    # Preprocessing pipeline
    numeric_features = ["file_size", "entropy"]
    categorical_features = ["category", "extension", "preference"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric_features),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features)
        ]
    )

    # Random Forest Classifier with robust parameters
    rf_classifier = RandomForestClassifier(
        n_estimators=100,
        max_depth=12,
        min_samples_split=2,
        min_samples_leaf=1,
        random_state=42,
        class_weight="balanced"
    )

    model_pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", rf_classifier)
        ]
    )

    # Stratified or standard train-test split
    # Since dataset is generated across samples, split by random state
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y if len(y.unique()) > 1 else None
    )

    print(f"[Model Training] Training pipeline on {len(X_train)} samples, testing on {len(X_test)} samples...")
    model_pipeline.fit(X_train, y_train)

    # Evaluation
    y_pred = model_pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    classes = list(model_pipeline.named_steps["classifier"].classes_)

    report_dict = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_test, y_pred, labels=classes).tolist()

    print("\n" + "="*50)
    print(f"RANDOM FOREST EVALUATION RESULTS (ISM PROJECT)")
    print("="*50)
    print(f"Test Set Accuracy: {acc * 100:.2f}%\n")
    print(classification_report(y_test, y_pred, zero_division=0))
    print("Confusion Matrix:")
    print(pd.DataFrame(cm, index=classes, columns=classes))
    print("="*50 + "\n")

    # Serialize trained pipeline and metadata
    model_output.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "classes": classes,
        "feature_cols": feature_cols,
        "test_accuracy": float(acc),
        "evaluation_report": report_dict,
        "confusion_matrix": cm,
        "training_samples": len(X_train),
        "test_samples": len(X_test)
    }

    joblib.dump({"pipeline": model_pipeline, "metadata": metadata}, model_output)
    print(f"[Model Training] Model artifact saved to: {model_output}")

    # Also save metadata as json for dashboard inspectability
    meta_path = model_output.parent / "model_metrics.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return metadata


if __name__ == "__main__":
    train_model()
