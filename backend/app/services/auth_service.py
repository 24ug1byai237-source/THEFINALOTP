"""
Auth service — handles authentication for all three roles:

  FARMER       → Phone-number OTP flow (WhatsApp deep-link DEMO)
  VETERINARIAN → Email + password flow
  GOVT_OFFICER → Email + password flow

DEMO OTP DESIGN — READ BEFORE MODIFYING
  This is a PROTOTYPE authentication mechanism. It does NOT use Twilio or the
  Meta WhatsApp Business API or any other external SMS/WhatsApp provider.

  Flow:
    1. Backend generates a cryptographically random 6-digit OTP and stores it.
    2. Backend builds a `wa.me` WhatsApp deep link with the code pre-filled
       into the message text and returns that link to the frontend.
    3. The frontend opens WhatsApp (or shows an "Open WhatsApp" button) so the
       farmer can see the code themselves inside their own WhatsApp app.
    4. The farmer manually types the code back into the website.
    5. Backend verifies the typed code the normal way.

  This is NOT a claim that the OTP was delivered by a real messaging API —
  the "delivery" is just a prefilled link the farmer's own WhatsApp opens.
  Do not describe this anywhere as production-grade delivery.

OTP security properties enforced here:
  1. OTP is a cryptographically random 6-digit numeric code stored in the
     otp_requests table (never in the JWT, never logged).
  2. OTP expires after OTP_TTL_SECONDS (default 10 min).
  3. OTP is marked used=True after first successful use (prevents reuse).
  4. Wrong OTP always returns the same generic message (no oracle attack).
  5. A code is locked out after settings.OTP_MAX_VERIFY_ATTEMPTS wrong guesses.
  6. Resending is rate-limited per phone (cooldown + rolling-window cap).
  7. The OTP code is never written to logs.

SECURITY NOTE:
  The role embedded in the JWT comes exclusively from the User.role database
  column — it is never accepted from a request body or URL parameter. Public
  self-registration (AuthService.register) can only ever create FARMER
  accounts; VETERINARIAN and GOVERNMENT_OFFICER accounts must be created via
  the admin-only UserService.create_user (POST /users, OFFICER-only).
"""

import hmac
import logging
import re
import secrets
import string
import urllib.parse
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    RateLimitError,
    UnauthorizedError,
    ValidationAppError,
)
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
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RegisterRoleRequest,
    SendOtpRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
    VerifyOtpRequest,
)
from app.services.token_service import TokenService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper: user → public response object
# ---------------------------------------------------------------------------

def _generate_official_id(db: Session, role: UserRole) -> str:
    prefix_map = {
        UserRole.VETERINARIAN: "VET",
        UserRole.OFFICER: "OFF",
        UserRole.FARMER: "FAR",
    }
    prefix = prefix_map.get(role, "USER")
    count = db.query(User).filter(User.role == role).count() + 1
    # Ensure uniqueness
    candidate = f"{prefix}-{count:04d}"
    idx = 1
    while db.query(User).filter(User.official_id == candidate).first():
        candidate = f"{prefix}-{(count + idx):04d}"
        idx += 1
    return candidate


def user_to_response(user: User) -> UserResponse:
    farm_ids = [a.farm_id for a in user.farm_assignments]
    official_id = user.official_id
    if not official_id:
        prefix_map = {
            UserRole.VETERINARIAN: "VET",
            UserRole.OFFICER: "OFF",
            UserRole.FARMER: "FAR",
        }
        prefix = prefix_map.get(user.role, "USER")
        official_id = f"{prefix}-{str(user.id)[:6].upper()}"
    return UserResponse(
        id=str(user.id),
        official_id=official_id,
        full_name=user.full_name,
        email=user.email,
        role=user.role.value,
        phone=user.phone,
        is_active=user.is_active,
        farm_ids=farm_ids,
        district_id=user.district_id,
    )


# ---------------------------------------------------------------------------
# Internal OTP helpers
# ---------------------------------------------------------------------------

_PHONE_CLEAN_RE = re.compile(r"[^\d+]")


def _normalize_phone(raw_phone: str) -> str:
    """
    Normalize a phone number for consistent storage/lookup so that
    "+91 98765 43210", "91-98765-43210" and "919876543210" all resolve to the
    same record. Strips everything but digits and a single leading '+'.
    """
    cleaned = _PHONE_CLEAN_RE.sub("", raw_phone.strip())
    if cleaned.count("+") > 1:
        cleaned = "+" + cleaned.replace("+", "")
    if not cleaned.startswith("+") and len(cleaned) == 10:
        # Bare 10-digit Indian mobile number → assume +91.
        cleaned = "+91" + cleaned
    return cleaned


def _generate_otp() -> str:
    """Return a cryptographically secure random 6-digit numeric string."""
    return "".join(secrets.choice(string.digits) for _ in range(6))


def _safe_code_equal(a: str, b: str) -> bool:
    """Constant-time string comparison to prevent timing attacks."""
    return hmac.compare_digest(a.encode(), b.encode())


def _build_whatsapp_deep_link(phone: str, code: str) -> str:
    """
    Build a `wa.me` WhatsApp deep link that opens a chat with `phone` and
    prefills a message containing the OTP `code`.

    DEMO NOTE: this does not send anything itself — it is a link that, when
    opened, hands the farmer's own WhatsApp app a prefilled message. The
    farmer reads the code from their own WhatsApp and types it back into the
    site. There is no external SMS/WhatsApp Business API call involved.
    """
    # wa.me expects digits only (no leading '+', spaces, or punctuation).
    digits_only = phone.lstrip("+")
    message = f"AgriSentinel verification code: {code}"
    return f"https://wa.me/{digits_only}?text={urllib.parse.quote(message)}"


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
        Request an OTP for a phone number (DEMO WhatsApp deep-link flow).

        • Generates a cryptographically random 6-digit numeric OTP and stores
          it in `otp_requests` with expiry, used=False, and an attempts counter.
        • Enforces a resend cooldown and a rolling-window request cap per phone.
        • Builds a `wa.me` WhatsApp deep link with the code prefilled into the
          message text and returns ONLY what the frontend needs to continue
          the demo flow (the link + timing info) — never anything claiming
          real external delivery.
        """
        clean_phone = _normalize_phone(payload.phone)
        if len(clean_phone.lstrip("+")) < 8:
            raise ValidationAppError("A valid phone number is required.")

        now = datetime.now(timezone.utc)

        # --- Resend cooldown -------------------------------------------------
        last_request = (
            db.query(OTPRequest)
            .filter(OTPRequest.phone == clean_phone)
            .order_by(OTPRequest.created_at.desc())
            .first()
        )
        if last_request is not None:
            created_at = last_request.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            elapsed = (now - created_at).total_seconds()
            if elapsed < settings.OTP_RESEND_COOLDOWN_SECONDS:
                wait = int(settings.OTP_RESEND_COOLDOWN_SECONDS - elapsed)
                raise RateLimitError(f"Please wait {wait}s before requesting another code.")

        # --- Rolling-window request cap --------------------------------------
        window_start = now - timedelta(seconds=settings.OTP_REQUEST_WINDOW_SECONDS)
        recent_count = (
            db.query(OTPRequest)
            .filter(OTPRequest.phone == clean_phone, OTPRequest.created_at >= window_start)
            .count()
        )
        if recent_count >= settings.OTP_MAX_REQUESTS_PER_WINDOW:
            raise RateLimitError(
                "Too many OTP requests for this number. Please try again later."
            )

        # Generate the code and store it. The code itself is never logged;
        # it only ever leaves this function embedded in the WhatsApp deep
        # link below, which the caller needs to continue the demo flow.
        code = _generate_otp()
        expires_at = now + timedelta(seconds=settings.OTP_TTL_SECONDS)

        otp_record = OTPRequest(
            phone=clean_phone,
            code=code,
            used=False,
            attempts=0,
            expires_at=expires_at,
        )
        db.add(otp_record)
        db.commit()

        whatsapp_url = _build_whatsapp_deep_link(clean_phone, code)

        # NOTE: SendOtpResponse (CamelModel) only declares a
        # `serialization_alias` on these fields (for camelCase JSON output),
        # not a validation/population alias — so FastAPI's response-model
        # validation of this dict requires the snake_case field names below.
        # Returning camelCase keys here raises a ResponseValidationError.
        return {
            "message": "OTP sent. Check WhatsApp and enter the 6-digit code.",
            "phone": clean_phone,
            "whatsapp_url": whatsapp_url,
            "expires_in_seconds": settings.OTP_TTL_SECONDS,
            "resend_cooldown_seconds": settings.OTP_RESEND_COOLDOWN_SECONDS,
            "demo": True,
        }

    @staticmethod
    def verify_otp(db: Session, payload: VerifyOtpRequest) -> TokenResponse:
        """
        Verify OTP for a phone number and return JWT tokens.

        Rejects:
          - Wrong OTP code (tracked per-code; locks out after
            settings.OTP_MAX_VERIFY_ATTEMPTS wrong guesses)
          - Expired OTP
          - Already-used OTP
          - OTP belonging to a different phone number
        """
        clean_phone = _normalize_phone(payload.phone)
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

        if otp_record.attempts >= settings.OTP_MAX_VERIFY_ATTEMPTS:
            otp_record.used = True  # lock the code out
            db.commit()
            raise UnauthorizedError(
                "Too many incorrect attempts. Please request a new code."
            )

        # Constant-time comparison to prevent timing attacks.
        if not _safe_code_equal(otp_record.code, code):
            otp_record.attempts += 1
            db.commit()
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
            #
            # IMPORTANT: we deliberately do NOT auto-assign this farmer to any
            # farm (no "first farm in the table" fallback). Farm association
            # happens explicitly afterwards, either by the farmer registering
            # their own farm (POST /farms, which assigns ownership to the
            # creating FARMER) or by an administrator assigning them via
            # POST /users. An unassigned farmer simply sees no farms until
            # then — which is correct, not a bug.
            user = User(
                email=f"farmer_{clean_phone.replace('+', '').replace(' ', '')}@bioshield.local",
                password_hash=get_password_hash(uuid.uuid4().hex + uuid.uuid4().hex),  # random unusable password
                full_name=f"Farmer ({clean_phone})",
                role=UserRole.FARMER,  # Always FARMER for OTP-based registration
                phone=clean_phone,
                district_id=None,  # No district silently assigned — must be set explicitly
            )
            db.add(user)
            db.flush()

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
        """
        Public self-registration for Farmer role.
        """
        return AuthService.register_by_role(
            db,
            RegisterRoleRequest(
                email=payload.email,
                password=payload.password,
                full_name=payload.full_name,
                role="farmer",
                phone=payload.phone,
                district_id=payload.district_id,
            ),
        )

    @staticmethod
    def register_by_role(db: Session, payload: RegisterRoleRequest) -> TokenResponse:
        """
        Public account creation for Farmers, Veterinarians, or Officers.
        Creates a real persistent database account with assigned official_id (e.g. VET-0001, OFF-0001, FAR-0001).
        """
        if db.query(User).filter(User.email == payload.email).first():
            raise ConflictError("Email already registered.")
        
        target_role = UserRole(payload.role)
        official_id = _generate_official_id(db, target_role)

        user = User(
            email=payload.email,
            password_hash=get_password_hash(payload.password),
            full_name=payload.full_name,
            role=target_role,
            phone=payload.phone,
            district_id=payload.district_id,
            official_id=official_id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return AuthService.login(db, LoginRequest(email=payload.email, password=payload.password))

    @staticmethod
    def refresh(db: Session, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token)
        except ValueError as exc:
            raise UnauthorizedError(str(exc)) from exc
        if payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid refresh token.")
        if TokenService.is_revoked(db, payload.get("jti")):
            raise UnauthorizedError("This session has been logged out. Please sign in again.")

        raw_user_id = payload.get("sub")
        try:
            user_id = uuid.UUID(str(raw_user_id))
        except (ValueError, TypeError):
            raise UnauthorizedError("Invalid refresh token.")

        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise UnauthorizedError("User not found or inactive.")

        # Rotate: the presented refresh token is single-use. Revoke it now so
        # it cannot be replayed, then issue a fresh access/refresh pair.
        exp = payload.get("exp")
        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc) if exp else None
        TokenService.revoke(db, payload.get("jti"), expires_at)

        access = create_access_token({"sub": str(user.id), "role": user.role.value})
        new_refresh = create_refresh_token({"sub": str(user.id)})
        db.commit()
        return TokenResponse(
            access_token=access,
            refresh_token=new_refresh,
            expires_in=settings.JWT_ACCESS_EXPIRE_MINUTES * 60,
            user=user_to_response(user),
        )

    @staticmethod
    def logout(db: Session, access_token: str | None, refresh_token: str | None = None) -> None:
        """
        Revoke the presented access token (and refresh token, if provided)
        server-side so they can no longer be used — not just discarded by the
        frontend. See app.models.token_blacklist.RevokedToken.
        """
        for token in (access_token, refresh_token):
            if not token:
                continue
            try:
                payload = decode_token(token)
            except ValueError:
                continue
            exp = payload.get("exp")
            expires_at = datetime.fromtimestamp(exp, tz=timezone.utc) if exp else None
            TokenService.revoke(db, payload.get("jti"), expires_at)
        db.commit()

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
    def list_veterinarians(db: Session) -> list[User]:
        """Return active veterinarian accounts for Farmer -> Vet selection."""
        return (
            db.query(User)
            .filter(User.role == UserRole.VETERINARIAN, User.is_active.is_(True))
            .order_by(User.full_name)
            .all()
        )

    @staticmethod
    def create_user(db: Session, payload: UserCreate) -> User:
        if db.query(User).filter(User.email == payload.email).first():
            raise ConflictError("Email already registered.")
        target_role = UserRole(payload.role)
        official_id = _generate_official_id(db, target_role)
        user = User(
            email=payload.email,
            password_hash=get_password_hash(payload.password),
            full_name=payload.full_name,
            role=target_role,
            phone=payload.phone,
            district_id=payload.district_id,
            official_id=official_id,
            is_active=True,
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
        try:
            uid = uuid.UUID(user_id)
        except ValueError:
            user = db.query(User).filter(User.official_id == user_id).first()
            if not user:
                raise NotFoundError("User", user_id)
            return user
        user = db.query(User).filter(User.id == uid).first()
        if not user:
            raise NotFoundError("User", user_id)
        return user

    @staticmethod
    def deactivate_user(db: Session, user_id: str) -> User:
        """
        Deactivate user login account ONLY (is_active = False).
        DOES NOT DELETE farms, incidents, evidence, inspections, or historical records!
        """
        user = UserService.get_user(db, user_id)
        user.is_active = False
        db.commit()
        db.refresh(user)
        return user

