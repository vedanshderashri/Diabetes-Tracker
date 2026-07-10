"""
MedAI Assistant - Pydantic Schemas
Request/Response models for all API endpoints.
"""
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# ═══════════════════════════════════════════════════════════════════════════
# AUTH SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: Optional[str] = None
    language_preference: str = Field(default="en", pattern="^(en|hi)$")


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = None
    language_preference: Optional[str] = Field(None, pattern="^(en|hi)$")
    password: Optional[str] = Field(None, min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class TokenRefresh(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    phone: Optional[str]
    role: str
    language_preference: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════════════════
# PATIENT PROFILE SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════

class PatientProfileCreate(BaseModel):
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, pattern="^(male|female|other)$")
    blood_type: Optional[str] = None
    height_cm: Optional[float] = Field(None, ge=0, le=300)
    weight_kg: Optional[float] = Field(None, ge=0, le=500)
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    address: Optional[str] = None


class PatientProfileResponse(PatientProfileCreate):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MedicalHistoryCreate(BaseModel):
    condition: str = Field(..., min_length=2, max_length=255)
    diagnosed_date: Optional[date] = None
    status: str = Field(default="active", pattern="^(active|resolved|managed)$")
    treating_doctor: Optional[str] = None
    notes: Optional[str] = None


class MedicalHistoryResponse(MedicalHistoryCreate):
    id: str
    patient_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class MedicationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    prescribed_by: Optional[str] = None
    is_active: bool = True
    notes: Optional[str] = None


class MedicationResponse(MedicationCreate):
    id: str
    patient_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class AllergyCreate(BaseModel):
    allergen: str = Field(..., min_length=2, max_length=255)
    severity: str = Field(default="moderate", pattern="^(mild|moderate|severe)$")
    reaction: Optional[str] = None
    diagnosed_date: Optional[date] = None


class AllergyResponse(AllergyCreate):
    id: str
    patient_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChronicConditionCreate(BaseModel):
    condition_name: str = Field(..., min_length=2, max_length=255)
    severity: str = Field(default="moderate", pattern="^(mild|moderate|severe)$")
    diagnosed_date: Optional[date] = None
    management_plan: Optional[str] = None
    last_checkup: Optional[date] = None


class ChronicConditionResponse(ChronicConditionCreate):
    id: str
    patient_id: str
    created_at: datetime

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════════════════
# CHAT SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════

class ChatSessionCreate(BaseModel):
    title: Optional[str] = "New Conversation"
    language: str = Field(default="en", pattern="^(en|hi)$")


class ChatSessionResponse(BaseModel):
    id: str
    user_id: str
    title: str
    language: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True


class ChatMessageSend(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class ChatMessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    is_emergency: bool = False
    metadata_json: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatAIResponse(BaseModel):
    user_message: ChatMessageResponse
    ai_message: ChatMessageResponse
    is_emergency: bool = False
    emergency_message: Optional[str] = None
    confidence: Optional[float] = None
    sources_used: int = 0
    web_sources_used: int = 0
    search_performed: bool = False
    references: List["WebReference"] = []
    evidence_summary: Optional[str] = None


class WebReference(BaseModel):
    title: str
    url: str
    source: str
    credibility_score: float = 0.0



# ═══════════════════════════════════════════════════════════════════════════
# REPORT SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════

class ReportResponse(BaseModel):
    id: str
    user_id: str
    file_name: str
    file_type: str
    report_type: Optional[str]
    status: str
    ai_summary: Optional[str]
    ai_explanation: Optional[str]
    critical_findings: Optional[str]
    upload_date: datetime
    analyzed_at: Optional[datetime]

    class Config:
        from_attributes = True


class LabValueResponse(BaseModel):
    id: str
    report_id: str
    test_name: str
    value: str
    unit: Optional[str]
    reference_range_low: Optional[float]
    reference_range_high: Optional[float]
    is_abnormal: bool
    is_critical: bool
    category: Optional[str]

    class Config:
        from_attributes = True


class ReportDetailResponse(ReportResponse):
    lab_values: List[LabValueResponse] = []


# ═══════════════════════════════════════════════════════════════════════════
# PREDICTION SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════

class SymptomPredictionRequest(BaseModel):
    symptoms: List[str] = Field(..., min_length=1)
    age: Optional[int] = Field(None, ge=0, le=150)
    gender: Optional[str] = None


class PredictionResult(BaseModel):
    condition: str
    probability: float
    confidence_level: str  # high | moderate | low
    reasoning: str


class SymptomPredictionResponse(BaseModel):
    predictions: List[PredictionResult]
    symptoms_analyzed: List[str]
    disclaimer: str = (
        "⚠️ This is an AI-generated assessment and NOT a medical diagnosis. "
        "Please consult a qualified healthcare professional for proper evaluation."
    )


class DiabetesRiskRequest(BaseModel):
    age: float = Field(..., ge=0, le=150)
    gender: str = Field(..., pattern="^(male|female|Male|Female)$")
    bmi: float = Field(..., ge=10, le=80)
    hypertension: bool = False
    heart_disease: bool = False
    smoking_history: str = Field(default="never")
    hba1c_level: float = Field(..., ge=3, le=15)
    blood_glucose_level: float = Field(..., ge=50, le=500)


class DiabetesRiskResponse(BaseModel):
    risk_score: float  # 0.0 - 1.0
    risk_level: str  # low | moderate | high | very_high
    contributing_factors: List[str]
    recommendations: List[str]
    disclaimer: str = (
        "⚠️ This is an AI-generated risk assessment and NOT a medical diagnosis. "
        "Please consult a qualified healthcare professional."
    )


# ═══════════════════════════════════════════════════════════════════════════
# DASHBOARD SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════

class HealthScoreResponse(BaseModel):
    overall_score: int = Field(..., ge=0, le=100)
    category: str  # excellent | good | fair | needs_attention
    breakdown: dict
    recommendations: List[str]


class DashboardResponse(BaseModel):
    health_score: HealthScoreResponse
    recent_reports: List[ReportResponse]
    active_conditions: List[str]
    active_medications: int
    allergies_count: int
    recent_chat_sessions: List[ChatSessionResponse]
    risk_indicators: List[dict]
    health_insights: List[str]


# ═══════════════════════════════════════════════════════════════════════════
# DOCTOR SUMMARY SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════

class DoctorSummaryRequest(BaseModel):
    patient_id: Optional[str] = None
    include_reports: bool = True
    include_chat_history: bool = True
    include_predictions: bool = True


class DoctorSummaryResponse(BaseModel):
    patient_name: str
    summary_date: datetime
    demographics: dict
    chief_complaints: List[str]
    symptom_timeline: List[dict]
    lab_abnormalities: List[dict]
    potential_conditions: List[dict]
    current_medications: List[dict]
    allergies: List[str]
    recommended_next_steps: List[str]
    ai_generated_narrative: str
    disclaimer: str = (
        "This is an AI-generated clinical summary for reference only. "
        "Clinical judgment by qualified healthcare professionals is essential."
    )


# ═══════════════════════════════════════════════════════════════════════════
# ADMIN SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════

class AdminUserListResponse(BaseModel):
    users: List[UserResponse]
    total: int
    page: int
    per_page: int


class SystemHealthResponse(BaseModel):
    status: str
    database: str
    vector_store: str
    ml_models: dict
    uptime_seconds: float
    total_users: int
    total_reports: int
    total_chat_sessions: int


class AnalyticsResponse(BaseModel):
    total_users: int
    total_reports: int
    total_chat_sessions: int
    total_messages: int
    reports_by_type: dict
    users_by_role: dict
    daily_activity: List[dict]


# Forward reference resolution
TokenResponse.model_rebuild()
ChatAIResponse.model_rebuild()

