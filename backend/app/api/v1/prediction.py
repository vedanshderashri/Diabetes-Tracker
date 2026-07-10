"""
MedAI Assistant - Prediction API
Disease prediction and diabetes risk assessment.
"""
from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.models.user import User
from app.services.disease_predictor import disease_predictor
from app.schemas.schemas import (
    SymptomPredictionRequest, SymptomPredictionResponse, PredictionResult,
    DiabetesRiskRequest, DiabetesRiskResponse,
)

router = APIRouter(prefix="/prediction", tags=["Prediction"])


@router.post("/symptoms", response_model=SymptomPredictionResponse)
async def predict_from_symptoms(
    data: SymptomPredictionRequest,
    current_user: User = Depends(get_current_user),
):
    """Predict possible diseases from reported symptoms."""
    result = disease_predictor.predict_from_symptoms(
        symptoms=data.symptoms,
        age=data.age,
        gender=data.gender,
    )

    predictions = [
        PredictionResult(**pred) for pred in result["predictions"]
    ]

    return SymptomPredictionResponse(
        predictions=predictions,
        symptoms_analyzed=result["symptoms_analyzed"],
    )


@router.post("/diabetes-risk", response_model=DiabetesRiskResponse)
async def predict_diabetes_risk(
    data: DiabetesRiskRequest,
    current_user: User = Depends(get_current_user),
):
    """Assess diabetes risk based on health indicators."""
    result = disease_predictor.predict_diabetes_risk(
        age=data.age,
        gender=data.gender,
        bmi=data.bmi,
        hypertension=data.hypertension,
        heart_disease=data.heart_disease,
        smoking_history=data.smoking_history,
        hba1c_level=data.hba1c_level,
        blood_glucose_level=data.blood_glucose_level,
    )

    return DiabetesRiskResponse(
        risk_score=result["risk_score"],
        risk_level=result["risk_level"],
        contributing_factors=result["contributing_factors"],
        recommendations=result["recommendations"],
    )
