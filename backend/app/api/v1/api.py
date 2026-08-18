from fastapi import APIRouter

from app.api.v1.endpoints import analysis, assistant, datasets, health, longitudinal, phenotyping, studies, system, uploads

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(datasets.router)
api_router.include_router(studies.router)
api_router.include_router(uploads.router)
api_router.include_router(analysis.router)
api_router.include_router(phenotyping.router)
api_router.include_router(longitudinal.router)
api_router.include_router(assistant.router)
api_router.include_router(system.router)
