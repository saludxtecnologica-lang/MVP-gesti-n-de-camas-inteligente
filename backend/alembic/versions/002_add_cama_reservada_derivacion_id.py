"""Add cama_reservada_derivacion_id to paciente table

Revision ID: 002_add_cama_reservada
Revises: 001_initial
Create Date: 2026-01-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_add_cama_reservada'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Agrega campo cama_reservada_derivacion_id a la tabla paciente.

    Este campo almacena la referencia a la cama que se reservó para una derivación,
    permitiendo asignación automática cuando se acepta la derivación.
    """
    op.add_column(
        'paciente',
        sa.Column('cama_reservada_derivacion_id', sa.String(), nullable=True)
    )

    # Agregar foreign key constraint
    op.create_foreign_key(
        'fk_paciente_cama_reservada_derivacion',
        'paciente',
        'cama',
        ['cama_reservada_derivacion_id'],
        ['id']
    )


def downgrade() -> None:
    """Remueve campo cama_reservada_derivacion_id de la tabla paciente."""
    # Primero remover la foreign key constraint
    op.drop_constraint(
        'fk_paciente_cama_reservada_derivacion',
        'paciente',
        type_='foreignkey'
    )

    # Luego remover la columna
    op.drop_column('paciente', 'cama_reservada_derivacion_id')
