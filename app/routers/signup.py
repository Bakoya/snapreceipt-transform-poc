from fastapi import APIRouter, HTTPException
from app.models.schemas import UserCreate, UserResponse
from app.services import db_service

router = APIRouter(prefix="/signup", tags=["signup"])


@router.post("", response_model=UserResponse)
def signup(payload: UserCreate):
    existing = db_service.get_user_by_email(payload.email)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"An account with this email already exists. Sign in with your API key.",
        )
    user = db_service.create_user(email=payload.email, name=payload.name)
    return user
