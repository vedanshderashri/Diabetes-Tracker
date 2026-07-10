"""
MedAI Assistant - ML Model Training
Train symptom-disease and diabetes risk prediction models from datasets.
"""
import logging
import sys
from pathlib import Path

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report
import joblib

logger = logging.getLogger(__name__)


def train_symptom_disease_model(datasets_dir: str, output_dir: str):
    """
    Train a Random Forest classifier on Training.csv
    Maps 132 symptoms (binary features) → disease prognosis.
    """
    print("=" * 60)
    print("Training Symptom -> Disease Prediction Model")
    print("=" * 60)

    datasets_path = Path(datasets_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Load training data
    train_file = datasets_path / "Training.csv"
    if not train_file.exists():
        print(f"ERROR: {train_file} not found")
        return False

    df = pd.read_csv(train_file)
    print(f"Dataset loaded: {df.shape[0]} rows, {df.shape[1]} columns")

    # Separate features and target
    target_col = "prognosis"
    X = df.drop(columns=[target_col])
    y = df[target_col]

    # Encode target labels
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)
    print(f"Classes: {len(label_encoder.classes_)} diseases")

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
    )

    # Train Random Forest
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=20,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"\nModel Accuracy: {accuracy * 100:.2f}%")

    # Save model and label encoder
    model_path = output_path / "symptom_disease_model.joblib"
    labels_path = output_path / "symptom_disease_labels.joblib"

    joblib.dump(model, model_path)
    joblib.dump(label_encoder, labels_path)

    print(f"Model saved to: {model_path}")
    print(f"Labels saved to: {labels_path}")

    # Also test with Testing.csv if available
    test_file = datasets_path / "Testing.csv"
    if test_file.exists():
        test_df = pd.read_csv(test_file)
        X_external = test_df.drop(columns=[target_col])
        y_external = label_encoder.transform(test_df[target_col])
        y_ext_pred = model.predict(X_external)
        ext_accuracy = accuracy_score(y_external, y_ext_pred)
        print(f"External Test Accuracy: {ext_accuracy * 100:.2f}%")

    return True


def train_diabetes_risk_model(datasets_dir: str, output_dir: str):
    """
    Train a Gradient Boosting classifier on diabetes_prediction_dataset.csv
    Features: gender, age, hypertension, heart_disease, smoking_history, bmi, HbA1c_level, blood_glucose_level
    Target: diabetes (0/1)
    """
    print("\n" + "=" * 60)
    print("Training Diabetes Risk Prediction Model")
    print("=" * 60)

    datasets_path = Path(datasets_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Load dataset
    diabetes_file = datasets_path / "diabetes_prediction_dataset.csv"
    if not diabetes_file.exists():
        print(f"ERROR: {diabetes_file} not found")
        return False

    df = pd.read_csv(diabetes_file)
    print(f"Dataset loaded: {df.shape[0]} rows, {df.shape[1]} columns")

    # Encode categorical features
    df["gender"] = df["gender"].map({"Female": 1, "Male": 0, "Other": 2}).fillna(0).astype(int)

    smoking_map = {
        "never": 0, "No Info": 1, "current": 2,
        "formerly": 3, "ever": 4, "not current": 5
    }
    df["smoking_history"] = df["smoking_history"].map(smoking_map).fillna(1).astype(int)

    # Features and target
    feature_cols = [
        "gender", "age", "hypertension", "heart_disease",
        "smoking_history", "bmi", "HbA1c_level", "blood_glucose_level"
    ]
    X = df[feature_cols]
    y = df["diabetes"]

    # Handle class imbalance with stratified split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Train Gradient Boosting
    model = GradientBoostingClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.1,
        min_samples_split=10,
        min_samples_leaf=5,
        random_state=42,
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"\nModel Accuracy: {accuracy * 100:.2f}%")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=["No Diabetes", "Diabetes"]))

    # Feature importance
    importances = dict(zip(feature_cols, model.feature_importances_))
    print("Feature Importance:")
    for feat, imp in sorted(importances.items(), key=lambda x: x[1], reverse=True):
        print(f"  {feat}: {imp:.4f}")

    # Save model
    model_path = output_path / "diabetes_risk_model.joblib"
    joblib.dump(model, model_path)
    print(f"\nModel saved to: {model_path}")

    return True


if __name__ == "__main__":
    # Default paths relative to the backend directory
    base_dir = Path(__file__).resolve().parent.parent.parent.parent # Root project directory
    datasets_dir = str(base_dir)  # Root project directory with CSVs
    output_dir = str(base_dir / "backend" / "ml_models")

    print(f"Datasets directory: {datasets_dir}")
    print(f"Output directory: {output_dir}")

    train_symptom_disease_model(datasets_dir, output_dir)
    train_diabetes_risk_model(datasets_dir, output_dir)

    print("\n" + "=" * 60)
    print("All models trained successfully!")
    print("=" * 60)
