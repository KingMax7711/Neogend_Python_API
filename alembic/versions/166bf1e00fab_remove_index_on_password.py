"""Remove index on password

Revision ID: 166bf1e00fab
Revises: 2855b1aec972
Create Date: 2025-10-05 14:41:52.833879

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '166bf1e00fab'
down_revision: Union[str, Sequence[str], None] = '2855b1aec972'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rendez l'opération idempotente: ne droppez l'index que s'il existe
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    schema = getattr(inspector, "default_schema_name", None)
    indexes = inspector.get_indexes('users', schema=schema)
    existing_index_names = {idx.get('name') for idx in indexes}
    target_index_name = op.f('ix_users_password')

    if target_index_name in existing_index_names:
        op.drop_index(target_index_name, table_name='users')


def downgrade() -> None:
    """Downgrade schema."""
    # Ne recréer l'index que s'il n'existe pas déjà
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    schema = getattr(inspector, "default_schema_name", None)
    indexes = inspector.get_indexes('users', schema=schema)
    existing_index_names = {idx.get('name') for idx in indexes}
    target_index_name = op.f('ix_users_password')

    if target_index_name not in existing_index_names:
        op.create_index(target_index_name, 'users', ['password'], unique=False)
