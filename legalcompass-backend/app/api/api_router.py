from fastapi import APIRouter
from app.api.routes import upload, chat, simulate, export_brief

api_router = APIRouter()

api_router.include_router(upload.router, tags=["Document Ingestion"])
api_router.include_router(chat.router, tags=["Conversational Copilot"])
api_router.include_router(simulate.router, tags=["Scenario Simulation"])
api_router.include_router(export_brief.router, tags=["Attorney Brief Export"])
