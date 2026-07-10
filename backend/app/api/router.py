"""
MedAI Assistant - API Router
Aggregates all v1 API routes.
"""
from fastapi import APIRouter
from app.api.v1 import auth, chat, reports, prediction, patients, dashboard, admin, summary

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(reports.router)
api_router.include_router(prediction.router)
api_router.include_router(patients.router)
api_router.include_router(dashboard.router)
api_router.include_router(admin.router)
api_router.include_router(summary.router)
