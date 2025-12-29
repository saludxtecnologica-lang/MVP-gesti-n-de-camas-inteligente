"""Migración inicial - Crear todas las tablas

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crea todas las tablas del sistema."""
    
    # Tabla Hospital
    op.create_table(
        'hospital',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('nombre', sa.String(), nullable=False),
        sa.Column('codigo', sa.String(), nullable=False),
        sa.Column('es_central', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('codigo')
    )
    op.create_index('ix_hospital_nombre', 'hospital', ['nombre'])
    
    # Tabla Servicio
    op.create_table(
        'servicio',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('nombre', sa.String(), nullable=False),
        sa.Column('codigo', sa.String(), nullable=False),
        sa.Column('tipo', sa.String(), nullable=False),
        sa.Column('hospital_id', sa.String(), nullable=False),
        sa.Column('numero_inicio_camas', sa.Integer(), nullable=False, default=100),
        sa.Column('es_uci', sa.Boolean(), nullable=False, default=False),
        sa.Column('es_uti', sa.Boolean(), nullable=False, default=False),
        sa.Column('permite_pediatria', sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospital.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_servicio_hospital_id', 'servicio', ['hospital_id'])
    
    # Tabla Sala
    op.create_table(
        'sala',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('numero', sa.Integer(), nullable=False),
        sa.Column('es_individual', sa.Boolean(), nullable=False, default=False),
        sa.Column('servicio_id', sa.String(), nullable=False),
        sa.Column('sexo_asignado', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['servicio_id'], ['servicio.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sala_servicio_id', 'sala', ['servicio_id'])
    
    # Tabla Cama
    op.create_table(
        'cama',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('numero', sa.Integer(), nullable=False),
        sa.Column('letra', sa.String(), nullable=True),
        sa.Column('identificador', sa.String(), nullable=False),
        sa.Column('sala_id', sa.String(), nullable=False),
        sa.Column('estado', sa.String(), nullable=False, default='libre'),
        sa.Column('estado_updated_at', sa.DateTime(), nullable=False),
        sa.Column('limpieza_inicio', sa.DateTime(), nullable=True),
        sa.Column('mensaje_estado', sa.String(), nullable=True),
        sa.Column('cama_asignada_destino', sa.String(), nullable=True),
        sa.Column('paciente_derivado_id', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['sala_id'], ['sala.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_cama_identificador', 'cama', ['identificador'])
    op.create_index('ix_cama_sala_id', 'cama', ['sala_id'])
    op.create_index('ix_cama_estado', 'cama', ['estado'])
    
    # Tabla Paciente
    op.create_table(
        'paciente',
        sa.Column('id', sa.String(), nullable=False),
        # Datos personales
        sa.Column('nombre', sa.String(), nullable=False),
        sa.Column('run', sa.String(), nullable=False),
        sa.Column('sexo', sa.String(), nullable=False),
        sa.Column('edad', sa.Integer(), nullable=False),
        sa.Column('edad_categoria', sa.String(), nullable=False),
        sa.Column('es_embarazada', sa.Boolean(), nullable=False, default=False),
        # Datos clínicos
        sa.Column('diagnostico', sa.String(), nullable=False),
        sa.Column('tipo_enfermedad', sa.String(), nullable=False),
        sa.Column('tipo_aislamiento', sa.String(), nullable=False, default='ninguno'),
        sa.Column('notas_adicionales', sa.String(), nullable=True),
        sa.Column('documento_adjunto', sa.String(), nullable=True),
        # Requerimientos (JSON)
        sa.Column('requerimientos_no_definen', sa.String(), nullable=True),
        sa.Column('requerimientos_baja', sa.String(), nullable=True),
        sa.Column('requerimientos_uti', sa.String(), nullable=True),
        sa.Column('requerimientos_uci', sa.String(), nullable=True),
        sa.Column('casos_especiales', sa.String(), nullable=True),
        # Observación y monitorización
        sa.Column('motivo_observacion', sa.String(), nullable=True),
        sa.Column('justificacion_observacion', sa.String(), nullable=True),
        sa.Column('motivo_monitorizacion', sa.String(), nullable=True),
        sa.Column('justificacion_monitorizacion', sa.String(), nullable=True),
        sa.Column('procedimiento_invasivo', sa.String(), nullable=True),
        # Complejidad y tipo
        sa.Column('complejidad_requerida', sa.String(), nullable=False, default='baja'),
        sa.Column('tipo_paciente', sa.String(), nullable=False),
        sa.Column('hospital_id', sa.String(), nullable=False),
        # Asignación de camas
        sa.Column('cama_id', sa.String(), nullable=True),
        sa.Column('cama_destino_id', sa.String(), nullable=True),
        sa.Column('cama_origen_derivacion_id', sa.String(), nullable=True),
        # Lista de espera
        sa.Column('en_lista_espera', sa.Boolean(), nullable=False, default=False),
        sa.Column('estado_lista_espera', sa.String(), nullable=False, default='esperando'),
        sa.Column('prioridad_calculada', sa.Float(), nullable=False, default=0.0),
        sa.Column('timestamp_lista_espera', sa.DateTime(), nullable=True),
        # Estados especiales
        sa.Column('requiere_nueva_cama', sa.Boolean(), nullable=False, default=False),
        sa.Column('en_espera', sa.Boolean(), nullable=False, default=False),
        sa.Column('oxigeno_desactivado_at', sa.DateTime(), nullable=True),
        sa.Column('requerimientos_oxigeno_previos', sa.String(), nullable=True),
        sa.Column('esperando_evaluacion_oxigeno', sa.Boolean(), nullable=False, default=False),
        # Derivación
        sa.Column('derivacion_hospital_destino_id', sa.String(), nullable=True),
        sa.Column('derivacion_motivo', sa.String(), nullable=True),
        sa.Column('derivacion_estado', sa.String(), nullable=True),
        sa.Column('derivacion_motivo_rechazo', sa.String(), nullable=True),
        # Alta
        sa.Column('alta_solicitada', sa.Boolean(), nullable=False, default=False),
        sa.Column('alta_motivo', sa.String(), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        # Constraints
        sa.ForeignKeyConstraint(['hospital_id'], ['hospital.id']),
        sa.ForeignKeyConstraint(['cama_id'], ['cama.id']),
        sa.ForeignKeyConstraint(['cama_destino_id'], ['cama.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_paciente_run', 'paciente', ['run'])
    op.create_index('ix_paciente_hospital_id', 'paciente', ['hospital_id'])
    op.create_index('ix_paciente_cama_id', 'paciente', ['cama_id'])
    op.create_index('ix_paciente_en_lista_espera', 'paciente', ['en_lista_espera'])
    op.create_index('ix_paciente_derivacion_estado', 'paciente', ['derivacion_estado'])
    
    # Tabla ConfiguracionSistema
    op.create_table(
        'configuracionsistema',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('modo_manual', sa.Boolean(), nullable=False, default=False),
        sa.Column('tiempo_limpieza_segundos', sa.Integer(), nullable=False, default=60),
        sa.Column('tiempo_espera_oxigeno_segundos', sa.Integer(), nullable=False, default=120),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Tabla LogActividad
    op.create_table(
        'logactividad',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tipo', sa.String(), nullable=False),
        sa.Column('descripcion', sa.String(), nullable=False),
        sa.Column('hospital_id', sa.String(), nullable=True),
        sa.Column('paciente_id', sa.String(), nullable=True),
        sa.Column('cama_id', sa.String(), nullable=True),
        sa.Column('datos_extra', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_logactividad_hospital_id', 'logactividad', ['hospital_id'])
    op.create_index('ix_logactividad_paciente_id', 'logactividad', ['paciente_id'])
    op.create_index('ix_logactividad_created_at', 'logactividad', ['created_at'])


def downgrade() -> None:
    """Elimina todas las tablas del sistema."""
    op.drop_table('logactividad')
    op.drop_table('configuracionsistema')
    op.drop_table('paciente')
    op.drop_table('cama')
    op.drop_table('sala')
    op.drop_table('servicio')
    op.drop_table('hospital')
