"""Add otp_requests.attempts column and revoked_tokens table

Adds the pieces needed for:
  - OTP verification attempt-limiting / lockout (Step 4 of the backend audit)
  - Real server-side logout + refresh-token rotation (Step 13)

This migration is purely additive: it does not touch or drop any existing
column, table, or row. Safe to run against a database with existing data.

Revision ID: 004_otp_token_rev
Revises: 003_otp_requests
Create Date: 2026-08-18
"""
from alembic import op
import sqlalchemy as sa

revision = "004_otp_token_rev"
down_revision = "003_otp_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "otp_requests",
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "revoked_tokens",
        sa.Column("jti", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("jti"),
    )
    op.create_index("ix_revoked_tokens_expires_at", "revoked_tokens", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_revoked_tokens_expires_at", table_name="revoked_tokens")
    op.drop_table("revoked_tokens")
    op.drop_column("otp_requests", "attempts")
