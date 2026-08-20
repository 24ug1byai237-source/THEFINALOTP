"""add official_id to users

Revision ID: 005_user_official_id
Revises: 004_otp_token_rev
Create Date: 2026-08-20

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005_user_official_id'
down_revision = '004_otp_token_rev'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('official_id', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_users_official_id'), 'users', ['official_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_official_id'), table_name='users')
    op.drop_column('users', 'official_id')
