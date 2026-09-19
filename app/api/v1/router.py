from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.documents import router as documents_router
from app.api.v1.questions import router as questions_router
from app.api.v1.answers import router as answers_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.relationships import router as relationships_router

api_router = APIRouter()

# Mount all endpoint routers
api_router.include_router(auth_router)
api_router.include_router(documents_router)
api_router.include_router(questions_router)
api_router.include_router(answers_router)
api_router.include_router(reviews_router)
api_router.include_router(relationships_router)
