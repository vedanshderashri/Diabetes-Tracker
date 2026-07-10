"""
MedAI Assistant - Chat & Prediction Tests
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_chat_session(auth_client: AsyncClient):
    """Test creating a chat session."""
    response = await auth_client.post("/api/v1/chat/sessions", json={
        "title": "Test Session",
        "language": "en",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Session"
    assert data["language"] == "en"


@pytest.mark.asyncio
async def test_list_chat_sessions(auth_client: AsyncClient):
    """Test listing chat sessions."""
    # Create a session first
    await auth_client.post("/api/v1/chat/sessions", json={"title": "Test"})
    response = await auth_client.get("/api/v1/chat/sessions")
    assert response.status_code == 200
    assert len(response.json()) >= 1


@pytest.mark.asyncio
async def test_symptom_prediction(auth_client: AsyncClient):
    """Test symptom-based prediction."""
    response = await auth_client.post("/api/v1/prediction/symptoms", json={
        "symptoms": ["headache", "fever", "fatigue"],
        "age": 30,
        "gender": "male",
    })
    assert response.status_code == 200
    data = response.json()
    assert "predictions" in data
    assert "disclaimer" in data


@pytest.mark.asyncio
async def test_diabetes_risk_prediction(auth_client: AsyncClient):
    """Test diabetes risk prediction."""
    response = await auth_client.post("/api/v1/prediction/diabetes-risk", json={
        "age": 55,
        "gender": "male",
        "bmi": 28.5,
        "hypertension": True,
        "heart_disease": False,
        "smoking_history": "never",
        "hba1c_level": 6.1,
        "blood_glucose_level": 140,
    })
    assert response.status_code == 200
    data = response.json()
    assert "risk_score" in data
    assert "risk_level" in data
    assert "contributing_factors" in data
    assert "recommendations" in data


@pytest.mark.asyncio
async def test_get_dashboard(auth_client: AsyncClient):
    """Test dashboard endpoint."""
    response = await auth_client.get("/api/v1/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "health_score" in data
    assert "recent_reports" in data


@pytest.mark.asyncio
async def test_get_profile(auth_client: AsyncClient):
    """Test patient profile endpoint."""
    response = await auth_client.get("/api/v1/patients/profile")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_profile(auth_client: AsyncClient):
    """Test profile update."""
    response = await auth_client.put("/api/v1/patients/profile", json={
        "gender": "male",
        "height_cm": 175,
        "weight_kg": 70,
    })
    assert response.status_code == 200
    assert response.json()["gender"] == "male"


@pytest.mark.asyncio
async def test_patient_parameters_crud(auth_client: AsyncClient):
    """Test adding and deleting medications, medical history, and allergies."""
    # Ensure profile exists
    await auth_client.put("/api/v1/patients/profile", json={
        "gender": "female",
        "height_cm": 160,
        "weight_kg": 55,
    })

    # 1. Medications
    med_resp = await auth_client.post("/api/v1/patients/medications", json={
        "name": "Metformin",
        "dosage": "500mg",
        "frequency": "Once daily",
    })
    assert med_resp.status_code == 201
    med_id = med_resp.json()["id"]

    # Delete Medication
    del_med_resp = await auth_client.delete(f"/api/v1/patients/medications/{med_id}")
    assert del_med_resp.status_code == 204

    # 2. Medical History
    hist_resp = await auth_client.post("/api/v1/patients/medical-history", json={
        "condition": "Diabetes Type 2",
        "status": "active",
    })
    assert hist_resp.status_code == 201
    hist_id = hist_resp.json()["id"]

    # Delete Medical History
    del_hist_resp = await auth_client.delete(f"/api/v1/patients/medical-history/{hist_id}")
    assert del_hist_resp.status_code == 204

    # 3. Allergies
    allergy_resp = await auth_client.post("/api/v1/patients/allergies", json={
        "allergen": "Peanuts",
        "severity": "severe",
        "reaction": "Anaphylaxis",
    })
    assert allergy_resp.status_code == 201
    allergy_id = allergy_resp.json()["id"]

    # Delete Allergy
    del_allergy_resp = await auth_client.delete(f"/api/v1/patients/allergies/{allergy_id}")
    assert del_allergy_resp.status_code == 204


@pytest.mark.asyncio
async def test_health_check():
    """Test health endpoint."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_chat_session_deletion(auth_client: AsyncClient):
    """Test creating and deleting a chat session."""
    # 1. Create a session
    create_response = await auth_client.post("/api/v1/chat/sessions", json={
        "title": "Chat to Delete",
        "language": "en",
    })
    assert create_response.status_code == 201
    session_id = create_response.json()["id"]

    # 2. Delete the session
    delete_response = await auth_client.delete(f"/api/v1/chat/sessions/{session_id}")
    assert delete_response.status_code == 204

    # 3. Verify it is gone
    list_response = await auth_client.get("/api/v1/chat/sessions")
    assert list_response.status_code == 200
    sessions = list_response.json()
    assert not any(s["id"] == session_id for s in sessions)


@pytest.mark.asyncio
async def test_report_deletion(auth_client: AsyncClient):
    """Test uploading and deleting a medical report."""
    # 1. Upload a report
    import io
    file_data = b"This is a fake medical report file content. CBC result normal hemoglobin 14.2"
    files = {"file": ("report.pdf", io.BytesIO(file_data), "application/pdf")}
    upload_response = await auth_client.post("/api/v1/reports/upload", files=files)
    assert upload_response.status_code == 201
    report_id = upload_response.json()["id"]

    # 2. Delete the report
    delete_response = await auth_client.delete(f"/api/v1/reports/{report_id}")
    assert delete_response.status_code == 204

    # 3. Verify it is gone
    list_response = await auth_client.get("/api/v1/reports")
    assert list_response.status_code == 200
    reports = list_response.json()
    assert not any(r["id"] == report_id for r in reports)
