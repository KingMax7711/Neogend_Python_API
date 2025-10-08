"""Fix Notifications.created_at to DateTime(timezone=True) with server default now()

Revision ID: e1c2f3a4b5c6
Revises: d4bb75ac9618
Create Date: 2025-10-08 17:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1c2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = 'd4bb75ac9618'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: alter notifications.created_at to timestamptz with default now() and not null."""
    # For PostgreSQL: use USING to cast from date or timestamp without time zone to timestamptz
    # 1) Set default
    op.execute("ALTER TABLE notifications ALTER COLUMN created_at SET DEFAULT now();")
    # 2) Convert type to timestamptz if not already
    op.execute("ALTER TABLE notifications ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at::timestamptz;")
    # 3) Backfill nulls to now() if any
    op.execute("UPDATE notifications SET created_at = now() WHERE created_at IS NULL;")
    # 4) Set NOT NULL
    op.execute("ALTER TABLE notifications ALTER COLUMN created_at SET NOT NULL;")


def downgrade() -> None:
    """Downgrade schema: relax to timestamp without tz and drop default/not null (best-effort)."""
    # Remove NOT NULL
    op.execute("ALTER TABLE notifications ALTER COLUMN created_at DROP NOT NULL;")
    # Convert back to timestamp without time zone
    op.execute("ALTER TABLE notifications ALTER COLUMN created_at TYPE TIMESTAMP USING created_at::timestamp;")
    # Drop default
    op.execute("ALTER TABLE notifications ALTER COLUMN created_at DROP DEFAULT;")
