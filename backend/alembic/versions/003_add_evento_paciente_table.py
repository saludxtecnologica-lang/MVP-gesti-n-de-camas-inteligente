"""Add evento_paciente table for tracking patient events

Revision ID: 003_add_evento_paciente
Revises: 002_add_cama_reservada
Create Date: 2026-01-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003_add_evento_paciente'
down_revision: Union[str, None] = '002_add_cama_reservada'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Crea la tabla evento_paciente para registrar todos los eventos
    importantes del paciente en el sistema.

    Esto permite trazabilidad completa y cálculos estadísticos precisos.
    """
    op.create_table(
        'evento_paciente',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tipo_evento', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('paciente_id', sa.String(), nullable=False),
        sa.Column('hospital_id', sa.String(), nullable=False),
        sa.Column('servicio_origen_id', sa.String(), nullable=True),
        sa.Column('servicio_destino_id', sa.String(), nullable=True),
        sa.Column('cama_origen_id', sa.String(), nullable=True),
        sa.Column('cama_destino_id', sa.String(), nullable=True),
        sa.Column('hospital_destino_id', sa.String(), nullable=True),
        sa.Column('datos_adicionales', sa.String(), nullable=True),
        sa.Column('dia_clinico', sa.DateTime(), nullable=True),
        sa.Column('duracion_segundos', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Crear índices para optimizar consultas
    op.create_index(
        'ix_evento_paciente_tipo_evento',
        'evento_paciente',
        ['tipo_evento']
    )
    op.create_index(
        'ix_evento_paciente_timestamp',
        'evento_paciente',
        ['timestamp']
    )
    op.create_index(
        'ix_evento_paciente_paciente_id',
        'evento_paciente',
        ['paciente_id']
    )
    op.create_index(
        'ix_evento_paciente_hospital_id',
        'evento_paciente',
        ['hospital_id']
    )
    op.create_index(
        'ix_evento_paciente_dia_clinico',
        'evento_paciente',
        ['dia_clinico']
    )

    # Crear foreign key constraints
    op.create_foreign_key(
        'fk_evento_paciente_paciente',
        'evento_paciente',
        'paciente',
        ['paciente_id'],
        ['id']
    )
    op.create_foreign_key(
        'fk_evento_paciente_hospital',
        'evento_paciente',
        'hospital',
        ['hospital_id'],
        ['id']
    )
    op.create_foreign_key(
        'fk_evento_paciente_servicio_origen',
        'evento_paciente',
        'servicio',
        ['servicio_origen_id'],
        ['id']
    )
    op.create_foreign_key(
        'fk_evento_paciente_servicio_destino',
        'evento_paciente',
        'servicio',
        ['servicio_destino_id'],
        ['id']
    )
    op.create_foreign_key(
        'fk_evento_paciente_cama_origen',
        'evento_paciente',
        'cama',
        ['cama_origen_id'],
        ['id']
    )
    op.create_foreign_key(
        'fk_evento_paciente_cama_destino',
        'evento_paciente',
        'cama',
        ['cama_destino_id'],
        ['id']
    )
    op.create_foreign_key(
        'fk_evento_paciente_hospital_destino',
        'evento_paciente',
        'hospital',
        ['hospital_destino_id'],
        ['id']
    )


def downgrade() -> None:
    """Elimina la tabla evento_paciente."""
    # Primero eliminar foreign keys
    op.drop_constraint('fk_evento_paciente_hospital_destino', 'evento_paciente', type_='foreignkey')
    op.drop_constraint('fk_evento_paciente_cama_destino', 'evento_paciente', type_='foreignkey')
    op.drop_constraint('fk_evento_paciente_cama_origen', 'evento_paciente', type_='foreignkey')
    op.drop_constraint('fk_evento_paciente_servicio_destino', 'evento_paciente', type_='foreignkey')
    op.drop_constraint('fk_evento_paciente_servicio_origen', 'evento_paciente', type_='foreignkey')
    op.drop_constraint('fk_evento_paciente_hospital', 'evento_paciente', type_='foreignkey')
    op.drop_constraint('fk_evento_paciente_paciente', 'evento_paciente', type_='foreignkey')

    # Luego eliminar índices
    op.drop_index('ix_evento_paciente_dia_clinico', 'evento_paciente')
    op.drop_index('ix_evento_paciente_hospital_id', 'evento_paciente')
    op.drop_index('ix_evento_paciente_paciente_id', 'evento_paciente')
    op.drop_index('ix_evento_paciente_timestamp', 'evento_paciente')
    op.drop_index('ix_evento_paciente_tipo_evento', 'evento_paciente')

    # Finalmente eliminar la tabla
    op.drop_table('evento_paciente')
