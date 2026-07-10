"""
MedAI Assistant - Disease Prediction Service
ML-based disease prediction using trained models on user datasets.
"""
import json
import logging
import os
from typing import List, Optional
from pathlib import Path

import numpy as np

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# Symptom list matching the Training.csv columns
SYMPTOM_LIST = [
    "itching", "skin_rash", "nodal_skin_eruptions", "continuous_sneezing",
    "shivering", "chills", "joint_pain", "stomach_pain", "acidity",
    "ulcers_on_tongue", "muscle_wasting", "vomiting", "burning_micturition",
    "spotting_urination", "fatigue", "weight_gain", "anxiety",
    "cold_hands_and_feets", "mood_swings", "weight_loss", "restlessness",
    "lethargy", "patches_in_throat", "irregular_sugar_level", "cough",
    "high_fever", "sunken_eyes", "breathlessness", "sweating", "dehydration",
    "indigestion", "headache", "yellowish_skin", "dark_urine", "nausea",
    "loss_of_appetite", "pain_behind_the_eyes", "back_pain", "constipation",
    "abdominal_pain", "diarrhoea", "mild_fever", "yellow_urine",
    "yellowing_of_eyes", "acute_liver_failure", "fluid_overload",
    "swelling_of_stomach", "swelled_lymph_nodes", "malaise",
    "blurred_and_distorted_vision", "phlegm", "throat_irritation",
    "redness_of_eyes", "sinus_pressure", "runny_nose", "congestion",
    "chest_pain", "weakness_in_limbs", "fast_heart_rate",
    "pain_during_bowel_movements", "pain_in_anal_region", "bloody_stool",
    "irritation_in_anus", "neck_pain", "dizziness", "cramps", "bruising",
    "obesity", "swollen_legs", "swollen_blood_vessels", "puffy_face_and_eyes",
    "enlarged_thyroid", "brittle_nails", "swollen_extremeties",
    "excessive_hunger", "extra_marital_contacts", "drying_and_tingling_lips",
    "slurred_speech", "knee_pain", "hip_joint_pain", "muscle_weakness",
    "stiff_neck", "swelling_joints", "movement_stiffness",
    "spinning_movements", "loss_of_balance", "unsteadiness",
    "weakness_of_one_body_side", "loss_of_smell", "bladder_discomfort",
    "foul_smell_of_urine", "continuous_feel_of_urine", "passage_of_gases",
    "internal_itching", "toxic_look_(typhos)", "depression", "irritability",
    "muscle_pain", "altered_sensorium", "red_spots_over_body", "belly_pain",
    "abnormal_menstruation", "dischromic_patches", "watering_from_eyes",
    "increased_appetite", "polyuria", "family_history", "mucoid_sputum",
    "rusty_sputum", "lack_of_concentration", "visual_disturbances",
    "receiving_blood_transfusion", "receiving_unsterile_injections", "coma",
    "stomach_bleeding", "distention_of_abdomen",
    "history_of_alcohol_consumption", "fluid_overload_2",
    "blood_in_sputum", "prominent_veins_on_calf", "palpitations",
    "painful_walking", "pus_filled_pimples", "blackheads", "scurring",
    "skin_peeling", "silver_like_dusting", "small_dents_in_nails",
    "inflammatory_nails", "blister", "red_sore_around_nose",
    "yellow_crust_ooze",
]


class DiseasePredictionService:
    """ML-based disease and diabetes risk prediction."""

    def __init__(self):
        self._symptom_model = None
        self._symptom_label_encoder = None
        self._diabetes_model = None
        self._models_loaded = False

    def load_models(self):
        """Load pre-trained ML models from disk."""
        if self._models_loaded:
            return

        models_dir = settings.ml_models_path
        try:
            import joblib

            symptom_model_path = models_dir / "symptom_disease_model.joblib"
            symptom_labels_path = models_dir / "symptom_disease_labels.joblib"
            diabetes_model_path = models_dir / "diabetes_risk_model.joblib"

            if symptom_model_path.exists():
                self._symptom_model = joblib.load(symptom_model_path)
                self._symptom_label_encoder = joblib.load(symptom_labels_path)
                logger.info("Symptom-disease model loaded")

            if diabetes_model_path.exists():
                self._diabetes_model = joblib.load(diabetes_model_path)
                logger.info("Diabetes risk model loaded")

            self._models_loaded = True

        except Exception as e:
            logger.error(f"Failed to load ML models: {e}")

    def predict_from_symptoms(
        self,
        symptoms: List[str],
        age: Optional[int] = None,
        gender: Optional[str] = None,
        top_k: int = 5,
    ) -> dict:
        """
        Predict possible diseases from symptoms.

        Returns ranked predictions with confidence scores.
        """
        self.load_models()

        # Normalize symptom names
        normalized_symptoms = []
        matched_symptoms = []
        for symptom in symptoms:
            normalized = symptom.lower().strip().replace(" ", "_")
            normalized_symptoms.append(normalized)
            if normalized in SYMPTOM_LIST:
                matched_symptoms.append(normalized)

        if not matched_symptoms and self._symptom_model is None:
            return self._rule_based_prediction(symptoms)

        if self._symptom_model is not None and matched_symptoms:
            return self._ml_prediction(matched_symptoms, top_k)
        else:
            return self._rule_based_prediction(symptoms)

    def _ml_prediction(self, matched_symptoms: List[str], top_k: int) -> dict:
        """Use trained ML model for prediction."""
        # Create feature vector
        feature_vector = np.zeros(len(SYMPTOM_LIST))
        for symptom in matched_symptoms:
            if symptom in SYMPTOM_LIST:
                idx = SYMPTOM_LIST.index(symptom)
                feature_vector[idx] = 1

        # Get prediction probabilities
        probabilities = self._symptom_model.predict_proba([feature_vector])[0]
        classes = self._symptom_label_encoder.classes_

        # Get top-k predictions
        top_indices = np.argsort(probabilities)[::-1][:top_k]

        predictions = []
        for idx in top_indices:
            prob = float(probabilities[idx])
            if prob > 0.01:  # Filter out very low probabilities
                condition = classes[idx]
                confidence_level = "High" if prob > 0.5 else "Moderate" if prob > 0.2 else "Low"

                # Generate reasoning
                reasoning = (
                    f"Based on the reported symptoms ({', '.join(matched_symptoms[:5])}), "
                    f"this condition shows a {prob*100:.1f}% match. "
                    f"The model analyzed {len(matched_symptoms)} symptom(s) against known disease patterns."
                )

                predictions.append({
                    "condition": condition,
                    "probability": round(prob, 4),
                    "confidence_level": confidence_level,
                    "reasoning": reasoning,
                })

        return {
            "predictions": predictions,
            "symptoms_analyzed": matched_symptoms,
            "model_type": "ml_classifier",
        }

    def _rule_based_prediction(self, symptoms: List[str]) -> dict:
        """Fallback rule-based prediction when ML model isn't available."""
        # Common symptom-disease mappings for basic functionality
        disease_rules = {
            "Common Cold": ["sneezing", "cough", "runny_nose", "congestion", "sore_throat"],
            "Influenza": ["high_fever", "body_aches", "fatigue", "cough", "headache"],
            "Diabetes": ["excessive_hunger", "weight_loss", "fatigue", "polyuria", "irregular_sugar_level"],
            "Hypertension": ["headache", "dizziness", "chest_pain", "breathlessness"],
            "Gastritis": ["stomach_pain", "acidity", "nausea", "vomiting", "indigestion"],
            "Migraine": ["headache", "nausea", "visual_disturbances", "sensitivity_to_light"],
            "Allergic Rhinitis": ["continuous_sneezing", "runny_nose", "watering_from_eyes", "itching"],
        }

        normalized_symptoms = [s.lower().strip().replace(" ", "_") for s in symptoms]
        predictions = []

        for disease, disease_symptoms in disease_rules.items():
            matches = sum(1 for s in normalized_symptoms if s in disease_symptoms)
            if matches > 0:
                prob = min(matches / len(disease_symptoms), 0.85)
                confidence_level = "High" if prob > 0.5 else "Moderate" if prob > 0.2 else "Low"
                predictions.append({
                    "condition": disease,
                    "probability": round(prob, 4),
                    "confidence_level": confidence_level,
                    "reasoning": f"Matched {matches} out of {len(disease_symptoms)} known symptoms for this condition.",
                })

        predictions.sort(key=lambda x: x["probability"], reverse=True)

        return {
            "predictions": predictions[:5],
            "symptoms_analyzed": normalized_symptoms,
            "model_type": "rule_based",
        }

    def predict_diabetes_risk(
        self,
        age: float,
        gender: str,
        bmi: float,
        hypertension: bool,
        heart_disease: bool,
        smoking_history: str,
        hba1c_level: float,
        blood_glucose_level: float,
    ) -> dict:
        """
        Predict diabetes risk based on health indicators.
        """
        self.load_models()

        contributing_factors = []
        recommendations = []

        # Rule-based risk assessment (always available)
        risk_score = 0.0

        # HbA1c analysis
        if hba1c_level >= 6.5:
            risk_score += 0.35
            contributing_factors.append(f"HbA1c level ({hba1c_level}%) is in the diabetic range (≥6.5%)")
        elif hba1c_level >= 5.7:
            risk_score += 0.2
            contributing_factors.append(f"HbA1c level ({hba1c_level}%) is in the pre-diabetic range (5.7-6.4%)")

        # Blood glucose analysis
        if blood_glucose_level >= 200:
            risk_score += 0.3
            contributing_factors.append(f"Blood glucose ({blood_glucose_level} mg/dL) is very high (≥200)")
        elif blood_glucose_level >= 126:
            risk_score += 0.2
            contributing_factors.append(f"Blood glucose ({blood_glucose_level} mg/dL) is in diabetic range (≥126)")
        elif blood_glucose_level >= 100:
            risk_score += 0.1
            contributing_factors.append(f"Blood glucose ({blood_glucose_level} mg/dL) is in pre-diabetic range (100-125)")

        # BMI analysis
        if bmi >= 30:
            risk_score += 0.15
            contributing_factors.append(f"BMI ({bmi}) indicates obesity (≥30)")
            recommendations.append("Weight management through balanced diet and regular exercise")
        elif bmi >= 25:
            risk_score += 0.08
            contributing_factors.append(f"BMI ({bmi}) indicates overweight (25-29.9)")

        # Other factors
        if hypertension:
            risk_score += 0.08
            contributing_factors.append("History of hypertension increases diabetes risk")
            recommendations.append("Regular blood pressure monitoring")

        if heart_disease:
            risk_score += 0.05
            contributing_factors.append("Heart disease history is associated with higher diabetes risk")

        if smoking_history in ("current", "ever", "formerly"):
            risk_score += 0.05
            contributing_factors.append("Smoking increases insulin resistance and diabetes risk")
            recommendations.append("Smoking cessation program recommended")

        if age > 45:
            risk_score += 0.05
            contributing_factors.append(f"Age ({age}) is a risk factor (>45)")

        # If ML model is available, use it too
        ml_score = None
        if self._diabetes_model is not None:
            try:
                gender_encoded = 1 if gender.lower() == "female" else 0
                smoking_map = {"never": 0, "no info": 1, "current": 2, "formerly": 3, "ever": 4, "not current": 5}
                smoking_encoded = smoking_map.get(smoking_history.lower(), 1)

                features = np.array([[
                    gender_encoded, age, int(hypertension), int(heart_disease),
                    smoking_encoded, bmi, hba1c_level, blood_glucose_level
                ]])

                ml_score = float(self._diabetes_model.predict_proba(features)[0][1])
                # Blend ML score with rule-based score
                risk_score = 0.6 * ml_score + 0.4 * risk_score
            except Exception as e:
                logger.error(f"ML diabetes prediction failed: {e}")

        risk_score = min(risk_score, 0.99)

        # Determine risk level
        if risk_score >= 0.7:
            risk_level = "very_high"
        elif risk_score >= 0.45:
            risk_level = "high"
        elif risk_score >= 0.25:
            risk_level = "moderate"
        else:
            risk_level = "low"

        # Generate recommendations
        if not recommendations:
            recommendations.append("Maintain a balanced diet rich in whole grains, vegetables, and lean proteins")
        recommendations.extend([
            "Regular physical activity (at least 150 minutes per week)",
            "Regular health check-ups and blood sugar monitoring",
            "Consult an endocrinologist for personalized assessment",
        ])

        if not contributing_factors:
            contributing_factors.append("No major risk factors identified based on the provided data")

        return {
            "risk_score": round(risk_score, 4),
            "risk_level": risk_level,
            "contributing_factors": contributing_factors,
            "recommendations": list(set(recommendations)),
            "ml_model_used": ml_score is not None,
        }

    def get_model_status(self) -> dict:
        """Check the status of loaded ML models."""
        return {
            "symptom_model": "loaded" if self._symptom_model is not None else "not_loaded",
            "diabetes_model": "loaded" if self._diabetes_model is not None else "not_loaded",
        }


# Singleton instance
disease_predictor = DiseasePredictionService()
