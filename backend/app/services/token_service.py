from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.token_blacklist import RevokedToken


class TokenService:
    @staticmethod
    def is_revoked(db: Session, jti: str | None) -> bool:
        if not jti:
            return False
        return db.query(RevokedToken.jti).filter(RevokedToken.jti == jti).first() is not None

    @staticmethod
    def revoke(db: Session, jti: str | None, expires_at: datetime | None) -> None:
        if not jti:
            return
        if db.query(RevokedToken.jti).filter(RevokedToken.jti == jti).first() is not None:
            return
        db.add(
            RevokedToken(
                jti=jti,
                expires_at=expires_at or datetime.now(timezone.utc),
                revoked_at=datetime.now(timezone.utc),
            )
        )
        db.flush()
