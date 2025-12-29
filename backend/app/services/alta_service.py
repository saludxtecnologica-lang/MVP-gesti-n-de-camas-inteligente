"""
Servicio de Altas.
Gestiona el proceso de alta de pacientes.

ACTUALIZADO: Incluye actualización de sexo de sala al liberar camas.

Ubicación: app/services/alta_service.py
"""
from typing import Optional
from sqlmodel import Session
from dataclasses import dataclass
from datetime import datetime
import logging

from app.models.paciente import Paciente
from app.models.cama import Cama
from app.models.enums import EstadoCamaEnum
from app.repositories.paciente_repo import PacienteRepository
from app.repositories.cama_repo import CamaRepository
from app.core.exceptions import (
    ValidationError,
    PacienteNotFoundError,
    AltaNoPermitidaError,
)

# NUEVO IMPORT
from app.services.compatibilidad_service import verificar_y_actualizar_sexo_sala_al_egreso

logger = logging.getLogger("gestion_camas.alta")


@dataclass
class ResultadoAlta:
    """Resultado de una operación de alta."""
    exito: bool
    mensaje: str
    paciente_id: Optional[str] = None
    cama_id: Optional[str] = None


class AltaService:
    """
    Servicio para gestión de altas.
    
    Maneja:
    - Sugerencia de alta
    - Inicio del proceso de alta
    - Ejecución del alta (con actualización de sexo de sala)
    - Cancelación del alta
    - Egreso manual (con actualización de sexo de sala)
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.paciente_repo = PacienteRepository(session)
        self.cama_repo = CamaRepository(session)
    
    def verificar_alta_sugerida(self, paciente: Paciente) -> bool:
        """
        Verifica si se debe sugerir alta para un paciente.
        
        Args:
            paciente: El paciente a verificar
        
        Returns:
            True si se debe sugerir alta
        """
        # Sin requerimientos de hospitalización
        if paciente.tiene_requerimientos():
            return False
        
        # Sin casos especiales
        if paciente.tiene_casos_especiales():
            return False
        
        return True
    
    def iniciar_alta(self, paciente_id: str) -> ResultadoAlta:
        """
        Inicia el proceso de alta.
        
        Args:
            paciente_id: ID del paciente
        
        Returns:
            Resultado de la operación
        """
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            raise PacienteNotFoundError(paciente_id)
        
        if not paciente.cama_id:
            raise ValidationError("El paciente no tiene cama asignada")
        
        cama = self.cama_repo.obtener_por_id(paciente.cama_id)
        if not cama:
            raise ValidationError("No se encontró la cama del paciente")
        
        # Verificar estado válido para iniciar alta
        estados_validos = [
            EstadoCamaEnum.OCUPADA,
            EstadoCamaEnum.ALTA_SUGERIDA,
            EstadoCamaEnum.CAMA_EN_ESPERA,
        ]
        
        if cama.estado not in estados_validos:
            raise ValidationError(
                f"No se puede iniciar alta. Estado actual: {cama.estado.value}"
            )
        
        # Cambiar estado
        cama.estado = EstadoCamaEnum.CAMA_ALTA
        cama.mensaje_estado = "Proceso de alta en curso"
        cama.estado_updated_at = datetime.utcnow()
        self.session.add(cama)
        
        paciente.alta_solicitada = True
        self.session.add(paciente)
        
        self.session.commit()
        
        logger.info(f"Alta iniciada para {paciente.nombre}")
        
        return ResultadoAlta(
            exito=True,
            mensaje="Proceso de alta iniciado",
            paciente_id=paciente_id,
            cama_id=cama.id
        )
    
    def ejecutar_alta(self, paciente_id: str) -> ResultadoAlta:
        """
        Ejecuta el alta y libera la cama.
        
        ACTUALIZADO: Incluye actualización de sexo de sala.
        
        Args:
            paciente_id: ID del paciente
        
        Returns:
            Resultado de la operación
        """
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            raise PacienteNotFoundError(paciente_id)
        
        if not paciente.cama_id:
            raise ValidationError("El paciente no tiene cama asignada")
        
        cama = self.cama_repo.obtener_por_id(paciente.cama_id)
        if not cama:
            raise ValidationError("No se encontró la cama del paciente")
        
        # Verificar que está en proceso de alta
        if cama.estado != EstadoCamaEnum.CAMA_ALTA:
            raise ValidationError(
                "El paciente no está en proceso de alta"
            )
        
        # Liberar cama (poner en limpieza)
        cama.estado = EstadoCamaEnum.EN_LIMPIEZA
        cama.limpieza_inicio = datetime.utcnow()
        cama.mensaje_estado = "En limpieza"
        cama.estado_updated_at = datetime.utcnow()
        self.session.add(cama)
        
        # NUEVO: Actualizar sexo de sala
        verificar_y_actualizar_sexo_sala_al_egreso(self.session, cama)
        
        # Desasociar paciente de cama
        cama_id = paciente.cama_id
        paciente.cama_id = None
        paciente.alta_solicitada = False
        self.session.add(paciente)
        
        self.session.commit()
        
        logger.info(f"Alta ejecutada para {paciente.nombre}")
        
        return ResultadoAlta(
            exito=True,
            mensaje="Alta completada, cama en limpieza",
            paciente_id=paciente_id,
            cama_id=cama_id
        )
    
    def cancelar_alta(self, paciente_id: str) -> ResultadoAlta:
        """
        Cancela el proceso de alta.
        
        Args:
            paciente_id: ID del paciente
        
        Returns:
            Resultado de la operación
        """
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            raise PacienteNotFoundError(paciente_id)
        
        if not paciente.cama_id:
            raise ValidationError("El paciente no tiene cama asignada")
        
        cama = self.cama_repo.obtener_por_id(paciente.cama_id)
        if not cama:
            raise ValidationError("No se encontró la cama del paciente")
        
        # Restaurar estado
        cama.estado = EstadoCamaEnum.OCUPADA
        cama.mensaje_estado = None
        cama.estado_updated_at = datetime.utcnow()
        self.session.add(cama)
        
        paciente.alta_solicitada = False
        self.session.add(paciente)
        
        self.session.commit()
        
        logger.info(f"Alta cancelada para {paciente.nombre}")
        
        return ResultadoAlta(
            exito=True,
            mensaje="Alta cancelada",
            paciente_id=paciente_id,
            cama_id=cama.id
        )
    
    def egreso_manual(self, paciente_id: str) -> ResultadoAlta:
        """
        Egresa un paciente manualmente (sin proceso de alta).
        
        ACTUALIZADO: Incluye actualización de sexo de sala.
        
        Args:
            paciente_id: ID del paciente
        
        Returns:
            Resultado de la operación
        """
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            raise PacienteNotFoundError(paciente_id)
        
        cama_id = paciente.cama_id
        
        if cama_id:
            cama = self.cama_repo.obtener_por_id(cama_id)
            if cama:
                cama.estado = EstadoCamaEnum.EN_LIMPIEZA
                cama.limpieza_inicio = datetime.utcnow()
                cama.mensaje_estado = "En limpieza"
                self.session.add(cama)
                
                # NUEVO: Actualizar sexo de sala
                verificar_y_actualizar_sexo_sala_al_egreso(self.session, cama)
        
        # Desasociar paciente
        paciente.cama_id = None
        paciente.cama_destino_id = None
        paciente.en_lista_espera = False
        self.session.add(paciente)
        
        self.session.commit()
        
        logger.info(f"Egreso manual para {paciente.nombre}")
        
        return ResultadoAlta(
            exito=True,
            mensaje="Egreso completado",
            paciente_id=paciente_id,
            cama_id=cama_id
        )