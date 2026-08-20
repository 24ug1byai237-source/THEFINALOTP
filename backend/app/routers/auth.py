from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, security
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterRoleRequest,
    SendOtpRequest,
    SendOtpResponse,
    TokenResponse,
    UserResponse,
    VerifyOtpRequest,
)
from app.services.auth_service import AuthService, UserService, user_to_response

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/otp/send", response_model=SendOtpResponse)
def send_otp(payload: SendOtpRequest, db: Session = Depends(get_db)):
    return AuthService.send_otp(db, payload)


@router.post("/otp/verify", response_model=TokenResponse)
def verify_otp(payload: VerifyOtpRequest, db: Session = Depends(get_db)):
    return AuthService.verify_otp(db, payload)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    return AuthService.login(db, payload)


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRoleRequest, db: Session = Depends(get_db)):
    return AuthService.register_by_role(db, payload)


@router.get("/veterinarians", response_model=list[UserResponse])
def list_veterinarians(db: Session = Depends(get_db)):
    """Return active veterinarian accounts for Farmer veterinarian selection."""
    return [user_to_response(u) for u in UserService.list_veterinarians(db)]


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    return AuthService.refresh(db, payload.refresh_token)


@router.get("/me", response_model=UserResponse)
def me(current_user: Annotated[User, Depends(get_current_user)]):
    return user_to_response(current_user)


@router.post("/logout")
def logout(
    payload: LogoutRequest | None = None,
    db: Session = Depends(get_db),
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
):
    """
    Revokes the presented access token (and refresh token, if supplied)
    server-side. Requires a bearer token so we know what to revoke — a
    client with no token has nothing meaningful to log out of.
    """
    access_token = credentials.credentials if credentials else None
    refresh_token = payload.refresh_token if payload else None
    AuthService.logout(db, access_token, refresh_token)
    return {"message": "Logged out successfully."}
