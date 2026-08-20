from pydantic import Field

from app.schemas.common import CamelModel


class SendOtpRequest(CamelModel):
    phone: str = Field(min_length=8)


class SendOtpResponse(CamelModel):
    """
    DEMO response for POST /auth/otp/send.

    Contains only what the frontend needs to continue the WhatsApp deep-link
    demo flow — a message to show, the wa.me link (which carries the OTP as
    its prefilled text), and timing info. `demo=True` always, as a reminder
    this is a prototype mechanism and not a real delivery guarantee.
    """
    message: str
    phone: str
    whatsapp_url: str = Field(serialization_alias="whatsappUrl")
    expires_in_seconds: int = Field(serialization_alias="expiresInSeconds")
    resend_cooldown_seconds: int = Field(serialization_alias="resendCooldownSeconds")
    demo: bool = True


class VerifyOtpRequest(CamelModel):
    phone: str = Field(min_length=8)
    code: str = Field(min_length=4)


class LoginRequest(CamelModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=6)


class RegisterRequest(CamelModel):
    """
    Public self-registration. Deliberately has NO role field — this endpoint
    can only ever create a FARMER account (enforced in AuthService.register).
    Privileged roles are provisioned by an OFFICER via POST /users.
    """
    email: str = Field(min_length=3)
    password: str = Field(min_length=6)
    full_name: str
    phone: str | None = None
    district_id: str | None = None


class TokenResponse(CamelModel):
    access_token: str = Field(serialization_alias="accessToken")
    refresh_token: str = Field(serialization_alias="refreshToken")
    expires_in: int = Field(serialization_alias="expiresIn")
    user: "UserResponse"


class RefreshRequest(CamelModel):
    refresh_token: str = Field(alias="refreshToken")


class LogoutRequest(CamelModel):
    # Optional: if the frontend also has the refresh token handy, sending it
    # lets logout revoke it immediately instead of waiting for it to expire.
    refresh_token: str | None = Field(default=None, alias="refreshToken")


class RegisterRoleRequest(CamelModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=6)
    full_name: str = Field(alias="fullName")
    role: str  # "farmer", "veterinarian", "officer"
    phone: str | None = None
    district_id: str | None = Field(default=None, alias="districtId")


class UserResponse(CamelModel):
    id: str
    official_id: str | None = Field(default=None, serialization_alias="officialId")
    full_name: str = Field(serialization_alias="fullName")
    email: str
    role: str
    phone: str | None = None
    is_active: bool = Field(default=True, serialization_alias="isActive")
    farm_ids: list[str] = Field(default_factory=list, serialization_alias="farmIds")
    district_id: str | None = Field(default=None, serialization_alias="districtId")


class UserCreate(CamelModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=6)
    full_name: str
    role: str
    phone: str | None = None
    district_id: str | None = None
    farm_ids: list[str] = Field(default_factory=list)


class UserUpdate(CamelModel):
    full_name: str | None = None
    phone: str | None = None
    is_active: bool | None = None
