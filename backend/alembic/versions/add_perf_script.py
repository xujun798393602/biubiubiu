"""add perf_script column

Revision ID: add_perf_script
Revises: add_ui_screenshots
Create Date: 2026-05-24
"""
from alembic import op
import sqlalchemy as sa

revision = "add_perf_script"
down_revision = "add_ui_screenshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("test_cases", sa.Column("perf_script", sa.Text, nullable=True, comment="性能测试脚本"))


def downgrade() -> None:
    op.drop_column("test_cases", "perf_script")
