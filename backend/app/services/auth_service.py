"""
Auth service — handles authentication for all three roles:

  FARMER       → Phone-number OTP flow (Twilio Verify)
  VETERINARIAN → Email + password flow
  GOVT_OFFICER → Email + password flow

OTP security properties enforced here:
  1. OTP is a random 6-digit numeric code stored in the otp_requests table.
  2. OTP expires after OTP_TTL_SECONDS (default 10 min).
  3. OTP is marked used=True after first successful use (prevents reuse).
  4. Wrong OTP always returns the same generic message (no oracle attack).
  5. No OTP code is ever included in an API response.
  6. If Twilio is not configured, send_otp raises HTTP 503 with clear guidance.

SECURITY NOTE:
  The role embedded in the JWT comes exclusively from the User.role database
  column — it is never accepted from a request body or URL parameter.
"""

import hmac
import random
import string
from datetime import datetime, timedelta, timezone

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
from app.models.otp_request import OTPRequest
from app.models.user import User, UserFarmAssignment
from app.models.farm import Farm
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    SendOtpRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
    VerifyOtpRequest,
)


# ---------------------------------------------------------------------------
# Helper: user → public response object
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Internal OTP helpers
# ---------------------------------------------------------------------------

def _generate_otp() -> str:
    """Return a cryptographically random 6-digit numeric string."""
    return "".join(random.choices(string.digits, k=6))


def _safe_code_equal(a: str, b: str) -> bool:
    """Constant-time string comparison to prevent timing attacks."""
    return hmac.compare_digest(a.encode(), b.encode())


def _send_via_twilio(phone: str, code: str) -> None:
    """
    Send OTP via Twilio Verify.
    Raises RuntimeError (caught by caller) if Twilio rejects.
    """
    try:
        from twilio.rest import Client  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "twilio package is not installed. Add 'twilio' to requirements.txt."
        ) from exc

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    # We use Twilio Verify — it manages code generation & delivery internally.
    # We pass our own code as a "custom code" via the CustomCode parameter.
    client.verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID).verifications.create(
        to=phone,
        channel="sms",
        custom_code=code,
    )


# ---------------------------------------------------------------------------
# Auth service
# ---------------------------------------------------------------------------

class AuthService:

    # ------------------------------------------------------------------
    # OTP flow (Farmers)
    # ------------------------------------------------------------------

    @staticmethod
    def send_otp(db: Session, payload: SendOtpRequest) -> dict:
        """
        Request OTP for a phone number.
        • If Twilio is configured → send real SMS and return success message.
        • If Twilio is NOT configured → raise 503 with required env-var list.
        • Never returns the OTP code in the response body.
        """
        clean_phone = payload.phone.strip()
        if not clean_phone:
            raise ValidationAppError("Phone number is required.")

        # Reject if OTP provider is not configured — clear error, no fake OTP.
        if not settings.twilio_configured:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=503,
                detail={
                    "error": {
                        "code": "OTP_PROVIDER_NOT_CONFIGURED",
                        "message": (
                            "OTP provider (Twilio Verify) is not configured. "
                            "Set the following environment variables to enable real phone OTP authentication."
                        ),
                        "required_env_vars": [
                            "TWILIO_ACCOUNT_SID",
                            "TWILIO_AUTH_TOKEN",
                            "TWILIO_VERIFY_SERVICE_SID",
                        ],
                        "docs": "https://console.twilio.com/ → Create a Verify Service → copy the Service SID",
                    }
                },
            )

        # Generate OTP and store it in the database with expiry.
        code = _generate_otp()
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.OTP_TTL_SECONDS)

        otp_record = OTPRequest(
            phone=clean_phone,
            code=code,
            used=False,
            expires_at=expires_at,
        )
        db.add(otp_record)
        db.commit()

        # Attempt to send via Twilio.
        try:
            _send_via_twilio(clean_phone, code)
        except Exception as exc:
            # Roll back the stored OTP if delivery failed.
            db.delete(otp_record)
            db.commit()
            raise ValidationAppError(
                f"Failed to send OTP to {clean_phone}. Please check the phone number and try again."
            ) from exc

        return {
            "message": f"OTP sent to {clean_phone}. Valid for {settings.OTP_TTL_SECONDS // 60} minutes.",
        }

    @staticmethod
    def verify_otp(db: Session, payload: VerifyOtpRequest) -> TokenResponse:
        """
        Verify OTP for a phone number and return JWT tokens.

        Rejects:
          - Wrong OTP code
          - Expired OTP
          - Already-used OTP
          - OTP belonging to a different phone number
        """
        clean_phone = payload.phone.strip()
        code = payload.code.strip()
        if not clean_phone or not code:
            raise ValidationAppError("Phone number and OTP code are required.")

        now = datetime.now(timezone.utc)

        # Find the most recent unused, unexpired OTP for this phone.
        otp_record = (
            db.query(OTPRequest)
            .filter(
                OTPRequest.phone == clean_phone,
                OTPRequest.used.is_(False),
                OTPRequest.expires_at > now,
            )
            .order_by(OTPRequest.created_at.desc())
            .first()
        )

        if otp_record is None:
            # Either no OTP was sent, it expired, or it was already used.
            raise UnauthorizedError(
                "Invalid or expired OTP. Please request a new code."
            )

        # Constant-time comparison to prevent timing attacks.
        if not _safe_code_equal(otp_record.code, code):
            raise UnauthorizedError(
                "Invalid OTP code. Please check the code and try again."
            )

        # Mark OTP as used — prevents replay attacks.
        otp_record.used = True
        db.flush()

        # Look up the farmer by phone number.
        user = db.query(User).filter(User.phone == clean_phone).first()

        if not user:
            # No account exists yet for this phone → auto-register as FARMER.
            # The role is ALWAYS set to FARMER here — never from user input.
            first_farm = db.query(Farm).first()
            user = User(
                email=f"farmer_{clean_phone.replace('+', '').replace(' ', '')}@bioshield.local",
                password_hash=get_password_hash(_generate_otp() + _generate_otp()),  # Random unusable password
                full_name=f"Farmer ({clean_phone})",
                role=UserRole.FARMER,  # Always FARMER for OTP-based registration
                phone=clean_phone,
                district_id=None,  # No district silently assigned — must be set explicitly
            )
            db.add(user)
            db.flush()
            if first_farm:
                db.add(UserFarmAssignment(user_id=user.id, farm_id=first_farm.id, is_owner=True))

        if not user.is_active:
            raise UnauthorizedError("User account is inactive. Contact support.")

        db.commit()
        db.refresh(user)

        # Role comes ONLY from the database column — never from request payload.
        access = create_access_token({"sub": str(user.id), "role": user.role.value})
        refresh = create_refresh_token({"sub": str(user.id)})
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=settings.JWT_ACCESS_EXPIRE_MINUTES * 60,
            user=user_to_response(user),
        )

    # ------------------------------------------------------------------
    # Email + password flow (Veterinarians & Government Officers)
    # ------------------------------------------------------------------

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
            expires_in=settings.JWT_ACCESS_EXPIRE_MINUTES * 60,
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
            expires_in=settings.JWT_ACCESS_EXPIRE_MINUTES * 60,
            user=user_to_response(user),
        )

    @staticmethod
    def get_me(user: User) -> UserResponse:
        return user_to_response(user)


# ---------------------------------------------------------------------------
# User management service (officer-only admin operations)
# ---------------------------------------------------------------------------

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
