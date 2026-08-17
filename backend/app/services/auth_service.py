from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError, ValidationAppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models.enums import UserRole
from app.models.user import User, UserFarmAssignment
from app.models.farm import Farm
from app.schemas.auth import LoginRequest, RegisterRequest, SendOtpRequest, TokenResponse, UserCreate, UserResponse, VerifyOtpRequest


def user_to_response(user: User) -> UserResponse:
    farm_ids = [a.farm_id for a in user.farm_assignments]
    return UserResponse(
        id=str(user.id),
        full_name=user.full_name,
        email=user.email,
        role=user.role.value,
        farm_ids=farm_ids,
        district_id=user.district_id,
    )


class AuthService:
    @staticmethod
    def send_otp(db: Session, payload: SendOtpRequest) -> dict:
        clean_phone = payload.phone.strip()
        if not clean_phone:
            raise ValidationAppError("Phone number is required.")
        return {"message": f"OTP code sent successfully to {clean_phone}.", "demo_code": "123456"}

    @staticmethod
    def verify_otp(db: Session, payload: VerifyOtpRequest) -> TokenResponse:
        clean_phone = payload.phone.strip()
        code = payload.code.strip()
        if not clean_phone or not code:
            raise ValidationAppError("Phone number and OTP code are required.")

        # Find user by phone number or check default farmer
        user = db.query(User).filter(User.phone == clean_phone).first()
        if not user:
            user = db.query(User).filter(User.email == "farmer@bioshield.local").first()
            if user:
                user.phone = clean_phone
                db.commit()

        if not user:
            first_farm = db.query(Farm).first()
            user = User(
                email=f"farmer_{clean_phone.replace('+', '')}@bioshield.local",
                password_hash=get_password_hash("farmer123"),
                full_name=f"Farmer ({clean_phone})",
                role=UserRole.FARMER,
                phone=clean_phone,
                district_id=settings.DEFAULT_DISTRICT_ID,
            )
            db.add(user)
            db.flush()
            if first_farm:
                db.add(UserFarmAssignment(user_id=user.id, farm_id=first_farm.id, is_owner=True))
            db.commit()
            db.refresh(user)

        if not user.is_active:
            raise UnauthorizedError("User account is inactive.")

        access = create_access_token({"sub": str(user.id), "role": user.role.value})
        refresh = create_refresh_token({"sub": str(user.id)})
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=3600,
            user=user_to_response(user),
        )

    @staticmethod
    def login(db: Session, payload: LoginRequest) -> TokenResponse:
        user = db.query(User).filter(User.email == payload.email).first()
        if not user or not verify_password(payload.password, user.password_hash):
            raise UnauthorizedError("Invalid email or password.")
        if not user.is_active:
            raise UnauthorizedError("User account is inactive.")
        access = create_access_token({"sub": str(user.id), "role": user.role.value})
        refresh = create_refresh_token({"sub": str(user.id)})
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=3600,
            user=user_to_response(user),
        )

    @staticmethod
    def register(db: Session, payload: RegisterRequest) -> TokenResponse:
        if db.query(User).filter(User.email == payload.email).first():
            raise ConflictError("Email already registered.")
        try:
            role = UserRole(payload.role)
        except ValueError as exc:
            raise ValidationAppError("Invalid role.") from exc
        user = User(
            email=payload.email,
            password_hash=get_password_hash(payload.password),
            full_name=payload.full_name,
            role=role,
            phone=payload.phone,
            district_id=payload.district_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return AuthService.login(db, LoginRequest(email=payload.email, password=payload.password))

    @staticmethod
    def refresh(db: Session, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid refresh token.")
        user = db.query(User).filter(User.id == payload.get("sub")).first()
        if not user or not user.is_active:
            raise UnauthorizedError("User not found or inactive.")
        access = create_access_token({"sub": str(user.id), "role": user.role.value})
        refresh = create_refresh_token({"sub": str(user.id)})
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=3600,
            user=user_to_response(user),
        )

    @staticmethod
    def get_me(user: User) -> UserResponse:
        return user_to_response(user)


class UserService:
    @staticmethod
    def list_users(db: Session) -> list[User]:
        return db.query(User).order_by(User.full_name).all()

    @staticmethod
    def create_user(db: Session, payload: UserCreate) -> User:
        if db.query(User).filter(User.email == payload.email).first():
            raise ConflictError("Email already registered.")
        user = User(
            email=payload.email,
            password_hash=get_password_hash(payload.password),
            full_name=payload.full_name,
            role=UserRole(payload.role),
            phone=payload.phone,
            district_id=payload.district_id,
        )
        db.add(user)
        db.flush()
        for farm_id in payload.farm_ids:
            db.add(UserFarmAssignment(user_id=user.id, farm_id=farm_id, is_owner=True))
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_user(db: Session, user_id: str) -> User:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundError("User", user_id)
        return user
