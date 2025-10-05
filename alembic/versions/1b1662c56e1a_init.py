"""init

Revision ID: 1b1662c56e1a
Revises: 
Create Date: 2025-09-05 14:36:00.115151

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b1662c56e1a'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Crée la table de base 'users' pour permettre les migrations suivantes.
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('first_name', sa.String(), nullable=False),
        sa.Column('last_name', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password', sa.String(), nullable=False),
    )

    # Indexes de base (alignés sur le modèle actuel, non uniques par défaut)
    op.create_index('ix_users_first_name', 'users', ['first_name'], unique=False)
    op.create_index('ix_users_last_name', 'users', ['last_name'], unique=False)
    op.create_index('ix_users_email', 'users', ['email'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Supprime les indexes puis la table users
    with op.batch_alter_table('users'):
        pass
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_last_name', table_name='users')
    op.drop_index('ix_users_first_name', table_name='users')
    op.drop_table('users')
