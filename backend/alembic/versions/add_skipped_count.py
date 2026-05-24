"""add skipped_count column

Revision ID: add_skipped_count
Revises: add_perf_script
Create Date: 2026-05-24
"""
from alembic import op
import sqlalchemy as sa

revision = "add_skipped_count"
down_revision = "add_perf_script"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("skipped_count", sa.Integer, nullable=False, server_default="0", comment="跳过数"))


def downgrade() -> None:
    op.drop_column("tasks", "skipped_count")
