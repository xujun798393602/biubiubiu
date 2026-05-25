"""add ui_screenshots column

Revision ID: add_ui_screenshots
Revises:
Create Date: 2026-05-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import inspect


revision = "add_ui_screenshots"
down_revision = None
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    if not column_exists('test_cases', 'ui_screenshots'):
        op.add_column("test_cases", sa.Column("ui_screenshots", JSONB, nullable=True, comment="UI 录制截图"))


def downgrade() -> None:
    if column_exists('test_cases', 'ui_screenshots'):
        op.drop_column("test_cases", "ui_screenshots")
