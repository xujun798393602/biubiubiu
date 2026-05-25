"""add skipped_count column

Revision ID: add_skipped_count
Revises: add_perf_script
Create Date: 2026-05-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "add_skipped_count"
down_revision = "add_perf_script"
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    if not column_exists('tasks', 'skipped_count'):
        op.add_column("tasks", sa.Column("skipped_count", sa.Integer, nullable=False, server_default="0", comment="跳过数"))


def downgrade() -> None:
    if column_exists('tasks', 'skipped_count'):
        op.drop_column("tasks", "skipped_count")
