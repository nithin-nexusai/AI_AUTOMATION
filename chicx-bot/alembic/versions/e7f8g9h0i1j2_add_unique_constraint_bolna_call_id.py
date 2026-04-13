"""add unique constraint on bolna_call_id

Revision ID: e7f8g9h0i1j2
Revises: d5e6f7g8h9i0
Create Date: 2026-04-12 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e7f8g9h0i1j2'
down_revision = 'd5e6f7g8h9i0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add unique constraint on calls.bolna_call_id to prevent duplicate call records.
    
    This fixes a race condition where multiple webhooks for the same call
    could create duplicate records.
    
    Note: The column already has unique=True in the model, but this migration
    ensures the database constraint is actually created.
    """
    # Add the unique constraint if it doesn't already exist
    # Note: The constraint may already exist from the model definition,
    # so we use IF NOT EXISTS (PostgreSQL 9.5+)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'uq_calls_bolna_call_id'
            ) THEN
                ALTER TABLE calls 
                ADD CONSTRAINT uq_calls_bolna_call_id 
                UNIQUE (bolna_call_id);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """Remove unique constraint on calls.bolna_call_id."""
    op.execute("""
        ALTER TABLE calls 
        DROP CONSTRAINT IF EXISTS uq_calls_bolna_call_id
    """)

# Made with Bob
