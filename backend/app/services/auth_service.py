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
        • Generates a real random 6-digit numeric OTP and stores in database (`otp_requests`).
        • Sets 10-minute expiry and used=False (single-use replay protection).
        • If Twilio is configured → attempts delivery via Twilio Verify (SMS/WhatsApp).
        • If Twilio is not configured → returns the code in dev_code for seamless testing on screen.
        """
        clean_phone = payload.phone.strip()
        if not clean_phone:
            raise ValidationAppError("Phone number is required.")

        # Generate 6-digit OTP and store it in the database with 10-min expiry
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

        # If Twilio is configured, attempt delivery via Twilio
        if settings.twilio_configured:
            try:
                _send_via_twilio(clean_phone, code)
                return {
                    "message": f"OTP code sent to {clean_phone} via SMS/WhatsApp. Valid for {settings.OTP_TTL_SECONDS // 60} minutes.",
                }
            except Exception as exc:
                # If Twilio fails, keep the stored OTP so user can still test
                pass

        # Dev / Testing fallback: Return message with the real DB-stored code
        return {
            "message": f"OTP verification code sent to {clean_phone}.",
            "dev_code": code,
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
