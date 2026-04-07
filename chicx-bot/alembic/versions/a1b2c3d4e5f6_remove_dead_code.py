"""remove_dead_code

Revision ID: a1b2c3d4e5f6
Revises: c4f8f2e06cf5
Create Date: 2025-01-10

Cleanup migration:
- Remove deprecated exotel_call_id column from calls table
- Drop unused templates table
- Drop unused search_logs table
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'c4f8f2e06cf5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove deprecated exotel_call_id column and index
    op.drop_index('ix_calls_exotel_call_id', table_name='calls')
    op.drop_column('calls', 'exotel_call_id')

    # Drop unused templates table
    op.drop_table('templates')

    # Drop unused search_logs table
    op.drop_index('ix_search_logs_query', table_name='search_logs')
    op.drop_index('ix_search_logs_created_at', table_name='search_logs')
    op.drop_table('search_logs')

    # Drop unused enums
    op.execute('DROP TYPE IF EXISTS templatetype')
    op.execute('DROP TYPE IF EXISTS templatestatus')


def downgrade() -> None:
    # Recreate templates table
    op.create_table('templates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('type', sa.Enum('utility', 'marketing', name='templatetype'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('meta_template_id', sa.String(length=100), nullable=True),
        sa.Column('status', sa.Enum('pending', 'approved', 'rejected', name='templatestatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Recreate search_logs table
    op.create_table('search_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('query', sa.String(length=255), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=True),
        sa.Column('results_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_search_logs_created_at', 'search_logs', ['created_at'], unique=False)
    op.create_index('ix_search_logs_query', 'search_logs', ['query'], unique=False)

    # Recreate exotel_call_id column
    op.add_column('calls', sa.Column('exotel_call_id', sa.String(length=100), nullable=True))
    op.create_index('ix_calls_exotel_call_id', 'calls', ['exotel_call_id'], unique=True)
