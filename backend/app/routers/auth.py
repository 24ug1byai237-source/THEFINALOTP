from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, SendOtpRequest, TokenResponse, UserResponse, VerifyOtpRequest
from app.services.auth_service import AuthService, user_to_response

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/otp/send")
def send_otp(payload: SendOtpRequest, db: Session = Depends(get_db)):
    return AuthService.send_otp(db, payload)


@router.post("/otp/verify", response_model=TokenResponse)
def verify_otp(payload: VerifyOtpRequest, db: Session = Depends(get_db)):
    return AuthService.verify_otp(db, payload)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    return AuthService.login(db, payload)


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    return AuthService.register(db, payload)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    return AuthService.refresh(db, payload.refresh_token)


@router.get("/me", response_model=UserResponse)
def me(current_user: Annotated[User, Depends(get_current_user)]):
    return user_to_response(current_user)


@router.post("/logout")
def logout():
    return {"message": "Logged out successfully."}
