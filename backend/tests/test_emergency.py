"""
MedAI Assistant - Emergency Detection Tests
"""
import pytest
from app.services.emergency import emergency_detector


def test_detect_chest_pain():
    result = emergency_detector.check_message("I have severe chest pain")
    assert result is not None
    assert result["is_emergency"] is True
    assert result["category"] == "cardiac"


def test_detect_breathing_difficulty():
    result = emergency_detector.check_message("I can't breathe properly")
    assert result is not None
    assert result["category"] == "respiratory"


def test_detect_stroke():
    result = emergency_detector.check_message("I think I'm having a stroke")
    assert result is not None
    assert result["category"] == "stroke"


def test_detect_suicidal_thoughts():
    result = emergency_detector.check_message("I want to kill myself")
    assert result is not None
    assert result["category"] == "mental_health"


def test_detect_hindi_emergency():
    result = emergency_detector.check_message("मुझे छाती में दर्द हो रहा है")
    assert result is not None
    assert result["is_emergency"] is True


def test_no_emergency():
    result = emergency_detector.check_message("I have a mild headache")
    assert result is None


def test_no_emergency_normal_message():
    result = emergency_detector.check_message("What foods are good for diabetes?")
    assert result is None


def test_emergency_response_format():
    result = emergency_detector.check_message("chest pain")
    assert result is not None
    response = emergency_detector.get_emergency_response(result)
    assert "EMERGENCY" in response or "emergency" in response.lower()
    assert "112" in response or "108" in response
