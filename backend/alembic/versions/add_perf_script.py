"""add perf_script column

Revision ID: add_perf_script
Revises: add_ui_screenshots
Create Date: 2026-05-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "add_perf_script"
down_revision = "add_ui_screenshots"
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    if not column_exists('test_cases', 'perf_script'):
        op.add_column("test_cases", sa.Column("perf_script", sa.Text, nullable=True, comment="性能测试脚本"))


def downgrade() -> None:
    if column_exists('test_cases', 'perf_script'):
        op.drop_column("test_cases", "perf_script")
