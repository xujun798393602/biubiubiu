"""add ui_screenshots column

Revision ID: add_ui_screenshots
Revises:
Create Date: 2026-05-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "add_ui_screenshots"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("test_cases", sa.Column("ui_screenshots", JSONB, nullable=True, comment="UI 录制截图"))


def downgrade() -> None:
    op.drop_column("test_cases", "ui_screenshots")
