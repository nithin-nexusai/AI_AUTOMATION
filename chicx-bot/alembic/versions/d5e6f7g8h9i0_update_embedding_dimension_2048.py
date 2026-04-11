"""update embedding dimension to 2048

Revision ID: d5e6f7g8h9i0
Revises: a1b2c3d4e5f6
Create Date: 2026-04-10 17:29:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd5e6f7g8h9i0'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Update embedding vector dimension from 768 to 2048 for NVIDIA model."""
    # Drop existing embeddings (they're invalid with old dimension anyway)
    op.execute("DELETE FROM embeddings")
    
    # Alter the vector column dimension
    op.execute("ALTER TABLE embeddings ALTER COLUMN embedding TYPE vector(2048)")


def downgrade() -> None:
    """Revert embedding vector dimension from 2048 to 768."""
    # Drop existing embeddings
    op.execute("DELETE FROM embeddings")
    
    # Alter the vector column dimension back
    op.execute("ALTER TABLE embeddings ALTER COLUMN embedding TYPE vector(768)")

# Made with Bob
