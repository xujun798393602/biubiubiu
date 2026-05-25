"""Add node scaling fields

Revision ID: add_node_scaling_fields
Revises: add_skipped_count
Create Date: 2026-05-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'add_node_scaling_fields'
down_revision: Union[str, None] = 'add_skipped_count'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def index_exists(table_name: str, index_name: str) -> bool:
    """Check if an index exists on a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
    return index_name in indexes


def upgrade() -> None:
    # Add node_type column if it doesn't exist
    if not column_exists('test_nodes', 'node_type'):
        op.add_column('test_nodes', sa.Column(
            'node_type',
            sa.String(16),
            nullable=False,
            server_default='MIXED',
            comment='节点类型: PLAYWRIGHT/LOCUST/MIXED'
        ))

    # Add capabilities column if it doesn't exist
    if not column_exists('test_nodes', 'capabilities'):
        op.add_column('test_nodes', sa.Column(
            'capabilities',
            postgresql.JSONB(),
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
            comment='节点能力配置'
        ))

    # Add api_key column if it doesn't exist
    if not column_exists('test_nodes', 'api_key'):
        op.add_column('test_nodes', sa.Column(
            'api_key',
            sa.String(64),
            nullable=True,
            comment='节点认证密钥'
        ))

    # Create index on node_type if it doesn't exist
    if not index_exists('test_nodes', 'idx_test_nodes_node_type'):
        op.create_index(
            'idx_test_nodes_node_type',
            'test_nodes',
            ['node_type']
        )


def downgrade() -> None:
    # Drop index
    if index_exists('test_nodes', 'idx_test_nodes_node_type'):
        op.drop_index('idx_test_nodes_node_type', table_name='test_nodes')

    # Drop columns
    if column_exists('test_nodes', 'api_key'):
        op.drop_column('test_nodes', 'api_key')
    if column_exists('test_nodes', 'capabilities'):
        op.drop_column('test_nodes', 'capabilities')
    if column_exists('test_nodes', 'node_type'):
        op.drop_column('test_nodes', 'node_type')
