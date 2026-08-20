"""
RevokedToken — server-side record of JWTs that must no longer be honoured.

Every access and refresh token now carries a unique `jti` claim. On logout we
record the presented token's jti here; on refresh we rotate (revoke the old
refresh jti, issue a new access/refresh pair). `get_current_user` and the
refresh flow both check this table before trusting a token, so logout has a
real server-side effect instead of only clearing the frontend's copy.

Rows are small and looked up by primary key (jti), so the extra check adds a
single indexed lookup per request — no meaningful performance regression.
Expired rows are safe to prune periodically (expires_at is stored for that
purpose) but are harmless if left in place.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
