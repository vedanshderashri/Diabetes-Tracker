"""
MedAI Assistant - Emergency Detection Engine
Detects high-risk phrases and triggers emergency workflow.
"""
import re
from typing import Optional


# Emergency keyword patterns organized by category
EMERGENCY_PATTERNS = {
    "cardiac": {
        "keywords": [
            r"chest\s*pain", r"heart\s*attack", r"cardiac\s*arrest",
            r"severe\s*chest\s*pressure", r"crushing\s*chest",
            r"pain\s*in\s*(my\s*)?chest", r"left\s*arm\s*pain.*chest",
            r"छाती\s*में\s*दर्द", r"दिल\s*का\s*दौरा",
        ],
        "severity": "critical",
        "message": "🚨 CARDIAC EMERGENCY DETECTED — Please call emergency services (112/108) IMMEDIATELY. "
                   "If you are experiencing chest pain, crushing pressure, or radiating pain to the arm/jaw, "
                   "do NOT wait. Seek immediate medical attention.",
    },
    "respiratory": {
        "keywords": [
            r"can'?t\s*breathe", r"difficulty\s*breathing", r"unable\s*to\s*breathe",
            r"shortness\s*of\s*breath.*severe", r"choking", r"suffocating",
            r"severe\s*breathing\s*problem", r"सांस\s*नहीं\s*आ\s*रही",
            r"सांस\s*लेने\s*में\s*तकलीफ",
        ],
        "severity": "critical",
        "message": "🚨 RESPIRATORY EMERGENCY DETECTED — If you are having severe difficulty breathing, "
                   "call emergency services (112/108) IMMEDIATELY. Sit upright and try to stay calm.",
    },
    "stroke": {
        "keywords": [
            r"stroke", r"face\s*drooping", r"slurred\s*speech",
            r"sudden\s*numbness", r"sudden\s*confusion",
            r"sudden\s*severe\s*headache", r"loss\s*of\s*vision.*sudden",
            r"one\s*side.*numb", r"can'?t\s*move.*arm", r"can'?t\s*move.*leg",
            r"लकवा", r"अचानक\s*सुन्नपन",
        ],
        "severity": "critical",
        "message": "🚨 POSSIBLE STROKE DETECTED — Time is critical. Call emergency services (112/108) NOW. "
                   "Remember FAST: Face drooping, Arm weakness, Speech difficulty, Time to call emergency.",
    },
    "bleeding": {
        "keywords": [
            r"severe\s*bleeding", r"won'?t\s*stop\s*bleeding",
            r"heavy\s*blood\s*loss", r"bleeding\s*profusely",
            r"coughing\s*blood", r"vomiting\s*blood",
            r"खून\s*बहना\s*बंद\s*नहीं", r"खून\s*की\s*उल्टी",
        ],
        "severity": "critical",
        "message": "🚨 SEVERE BLEEDING DETECTED — Apply direct pressure to the wound and call "
                   "emergency services (112/108) IMMEDIATELY. Keep the injured area elevated if possible.",
    },
    "mental_health": {
        "keywords": [
            r"suicid", r"kill\s*myself", r"want\s*to\s*die",
            r"end\s*(my\s*)?life", r"self\s*harm",
            r"don'?t\s*want\s*to\s*live", r"no\s*reason\s*to\s*live",
            r"आत्महत्या", r"जीने\s*का\s*मन\s*नहीं",
        ],
        "severity": "critical",
        "message": "🚨 MENTAL HEALTH CRISIS DETECTED — You are not alone. Please reach out immediately:\n"
                   "• India: iCall – 9152987821 | Vandrevala Foundation – 1860-2662-345\n"
                   "• Emergency: 112\n"
                   "• International: Crisis Text Line – Text HOME to 741741\n\n"
                   "Your life matters. Please talk to someone right now.",
    },
    "consciousness": {
        "keywords": [
            r"loss\s*of\s*consciousness", r"faint(ed|ing)", r"passed\s*out",
            r"unconscious", r"seizure", r"convulsion",
            r"not\s*responding", r"बेहोश", r"दौरा\s*पड़ना",
        ],
        "severity": "critical",
        "message": "🚨 LOSS OF CONSCIOUSNESS / SEIZURE DETECTED — Call emergency services (112/108) "
                   "IMMEDIATELY. If someone has fainted or is having a seizure, place them on their side, "
                   "clear the area, and do NOT put anything in their mouth.",
    },
    "poisoning": {
        "keywords": [
            r"poison(ed|ing)?", r"overdose", r"took\s*too\s*many\s*pills",
            r"swallowed.*chemical", r"drug\s*overdose",
            r"जहर", r"ज्यादा\s*दवाई\s*खा\s*ली",
        ],
        "severity": "critical",
        "message": "🚨 POSSIBLE POISONING / OVERDOSE DETECTED — Call Poison Control or emergency services "
                   "(112/108) IMMEDIATELY. Do NOT induce vomiting unless instructed by a medical professional.",
    },
    "allergic_reaction": {
        "keywords": [
            r"anaphyla(xis|ctic)", r"throat\s*swelling.*can'?t\s*breathe",
            r"severe\s*allergic\s*reaction", r"face\s*swelling.*breathing",
            r"एलर्जी.*सांस",
        ],
        "severity": "critical",
        "message": "🚨 SEVERE ALLERGIC REACTION (ANAPHYLAXIS) DETECTED — Use epinephrine (EpiPen) if "
                   "available and call emergency services (112/108) IMMEDIATELY.",
    },
}


class EmergencyDetector:
    """Detects emergency situations in user messages."""

    def __init__(self):
        # Pre-compile all patterns for performance
        self._compiled_patterns = {}
        for category, data in EMERGENCY_PATTERNS.items():
            self._compiled_patterns[category] = {
                "patterns": [
                    re.compile(kw, re.IGNORECASE | re.UNICODE)
                    for kw in data["keywords"]
                ],
                "severity": data["severity"],
                "message": data["message"],
            }

    def check_message(self, text: str) -> Optional[dict]:
        """
        Check a message for emergency indicators.

        Returns:
            dict with emergency details if detected, None otherwise.
            {
                "is_emergency": True,
                "category": "cardiac",
                "severity": "critical",
                "message": "...",
                "matched_pattern": "chest pain"
            }
        """
        if not text:
            return None

        text_lower = text.lower().strip()

        for category, data in self._compiled_patterns.items():
            for pattern in data["patterns"]:
                match = pattern.search(text_lower)
                if match:
                    return {
                        "is_emergency": True,
                        "category": category,
                        "severity": data["severity"],
                        "message": data["message"],
                        "matched_pattern": match.group(0),
                    }

        return None

    def get_emergency_response(self, detection_result: dict) -> str:
        """Format the emergency response message for the chatbot."""
        return (
            f"{detection_result['message']}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ **Important**: This AI assistant cannot provide emergency medical care. "
            "The above is an automated safety alert. Please contact emergency services "
            "or go to the nearest hospital immediately.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )


# Singleton instance
emergency_detector = EmergencyDetector()
