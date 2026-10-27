"""rename apikeys to api_keys

Revision ID: 7c1a2f6e9b3d
Revises: 6ef37cc54efd
Create Date: 2026-09-06 14:30:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7c1a2f6e9b3d"
down_revision: Union[str, Sequence[str], None] = "6ef37cc54efd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table("apikeys", "api_keys")


def downgrade() -> None:
    """Downgrade schema."""
    op.rename_table("api_keys", "apikeys")
