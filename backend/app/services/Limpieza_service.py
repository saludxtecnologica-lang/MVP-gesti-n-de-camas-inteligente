"""
Servicio de Limpieza.
Gestiona el proceso de limpieza de camas.
"""
from typing import List, Optional
from sqlmodel import Session, select
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from app.models.cama import Cama
from app.models.paciente import Paciente
from app.models.enums import EstadoCamaEnum
from app.repositories.cama_repo import CamaRepository
from app.repositories.paciente_repo import PacienteRepository
from app.config import settings

logger = logging.getLogger("gestion_camas.limpieza")


@dataclass
class ResultadoLimpieza:
    """Resultado de operación de limpieza."""
    camas_procesadas: int
    camas_liberadas: List[str]
    mensaje: str


class LimpiezaService:
    """
    Servicio para gestión de limpieza de camas.
    
    Maneja:
    - Inicio de limpieza
    - Procesamiento automático de camas en limpieza
    - Finalización de limpieza
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.cama_repo = CamaRepository(session)
    
    def iniciar_limpieza(self, cama_id: str) -> Cama:
        """
        Inicia el proceso de limpieza de una cama.
        
        Args:
            cama_id: ID de la cama
        
        Returns:
            La cama actualizada
        """
        cama = self.cama_repo.obtener_por_id(cama_id)
        if not cama:
            raise ValueError(f"Cama {cama_id} no encontrada")
        
        cama.estado = EstadoCamaEnum.EN_LIMPIEZA
        cama.limpieza_inicio = datetime.utcnow()
        cama.mensaje_estado = "En limpieza"
        cama.estado_updated_at = datetime.utcnow()
        
        self.session.add(cama)
        self.session.commit()
        
        logger.info(f"Limpieza iniciada para cama {cama.identificador}")
        
        return cama
    
    def finalizar_limpieza(self, cama_id: str) -> Cama:
        """
        Finaliza el proceso de limpieza de una cama.
        
        Args:
            cama_id: ID de la cama
        
        Returns:
            La cama actualizada
        """
        cama = self.cama_repo.obtener_por_id(cama_id)
        if not cama:
            raise ValueError(f"Cama {cama_id} no encontrada")
        
        if cama.estado != EstadoCamaEnum.EN_LIMPIEZA:
            raise ValueError(f"Cama {cama_id} no está en limpieza")
        
        cama.estado = EstadoCamaEnum.LIBRE
        cama.limpieza_inicio = None
        cama.mensaje_estado = None
        cama.estado_updated_at = datetime.utcnow()
        
        self.session.add(cama)
        self.session.commit()
        
        logger.info(f"Limpieza finalizada para cama {cama.identificador}")
        
        return cama
    
    def procesar_camas_en_limpieza(
        self, 
        tiempo_limpieza_segundos: Optional[int] = None
    ) -> ResultadoLimpieza:
        """
        Procesa camas que han terminado su tiempo de limpieza.
        
        Args:
            tiempo_limpieza_segundos: Tiempo de limpieza (usa config si no se especifica)
        
        Returns:
            Resultado del procesamiento
        """
        if tiempo_limpieza_segundos is None:
            tiempo_limpieza_segundos = settings.TIEMPO_LIMPIEZA_DEFAULT
        
        ahora = datetime.utcnow()
        limite = ahora - timedelta(seconds=tiempo_limpieza_segundos)
        
        # Buscar camas en limpieza
        camas = self.cama_repo.obtener_en_limpieza()
        camas_liberadas = []
        
        for cama in camas:
            if cama.limpieza_inicio and cama.limpieza_inicio <= limite:
                cama.estado = EstadoCamaEnum.LIBRE
                cama.limpieza_inicio = None
                cama.mensaje_estado = None
                cama.estado_updated_at = ahora
                self.session.add(cama)
                camas_liberadas.append(cama.id)
                
                logger.info(f"Cama {cama.identificador} liberada tras limpieza")
        
        if camas_liberadas:
            self.session.commit()
        
        return ResultadoLimpieza(
            camas_procesadas=len(camas),
            camas_liberadas=camas_liberadas,
            mensaje=f"{len(camas_liberadas)} camas liberadas"
        )
    
    def obtener_camas_en_limpieza(self) -> List[Cama]:
        """
        Obtiene todas las camas en limpieza.
        
        Returns:
            Lista de camas en limpieza
        """
        return self.cama_repo.obtener_en_limpieza()
    
    def tiempo_restante_limpieza(
        self, 
        cama: Cama,
        tiempo_limpieza_segundos: Optional[int] = None
    ) -> int:
        """
        Calcula el tiempo restante de limpieza en segundos.
        
        Args:
            cama: La cama a verificar
            tiempo_limpieza_segundos: Tiempo total de limpieza
        
        Returns:
            Segundos restantes (0 si ya terminó o no está en limpieza)
        """
        if cama.estado != EstadoCamaEnum.EN_LIMPIEZA or not cama.limpieza_inicio:
            return 0
        
        if tiempo_limpieza_segundos is None:
            tiempo_limpieza_segundos = settings.TIEMPO_LIMPIEZA_DEFAULT
        
        transcurrido = (datetime.utcnow() - cama.limpieza_inicio).total_seconds()
        restante = tiempo_limpieza_segundos - transcurrido
        
        return max(0, int(restante))


class OxigenoService:
    """
    Servicio para gestión de espera por oxígeno.
    
    Cuando un paciente deja de necesitar oxígeno, se espera un tiempo
    antes de cambiar el estado de la cama.
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.paciente_repo = PacienteRepository(session)
        self.cama_repo = CamaRepository(session)
    
    def iniciar_espera_oxigeno(self, paciente_id: str) -> Paciente:
        """
        Inicia la espera post-desactivación de oxígeno.
        
        Args:
            paciente_id: ID del paciente
        
        Returns:
            El paciente actualizado
        """
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            raise ValueError(f"Paciente {paciente_id} no encontrado")
        
        paciente.oxigeno_desactivado_at = datetime.utcnow()
        paciente.esperando_evaluacion_oxigeno = True
        
        self.session.add(paciente)
        self.session.commit()
        
        logger.info(f"Espera de oxígeno iniciada para {paciente.nombre}")
        
        return paciente
    
    def procesar_pacientes_espera_oxigeno(
        self,
        tiempo_espera_segundos: Optional[int] = None
    ) -> List[str]:
        """
        Procesa pacientes que han completado la espera de oxígeno.
        
        Args:
            tiempo_espera_segundos: Tiempo de espera (usa config si no se especifica)
        
        Returns:
            Lista de IDs de pacientes procesados
        """
        if tiempo_espera_segundos is None:
            tiempo_espera_segundos = settings.TIEMPO_ESPERA_OXIGENO_DEFAULT
        
        ahora = datetime.utcnow()
        limite = ahora - timedelta(seconds=tiempo_espera_segundos)
        
        pacientes_procesados = []
        
        # Buscar pacientes esperando
        pacientes = self.paciente_repo.obtener_en_espera_oxigeno()
        
        for paciente in pacientes:
            if paciente.oxigeno_desactivado_at and paciente.oxigeno_desactivado_at <= limite:
                # Limpiar campos de espera
                paciente.oxigeno_desactivado_at = None
                paciente.esperando_evaluacion_oxigeno = False
                paciente.requerimientos_oxigeno_previos = None
                
                # Determinar nuevo estado de cama
                if paciente.cama_id:
                    cama = self.cama_repo.obtener_por_id(paciente.cama_id)
                    if cama:
                        self._actualizar_estado_cama_post_oxigeno(paciente, cama)
                
                self.session.add(paciente)
                pacientes_procesados.append(paciente.id)
                
                logger.info(f"Espera de oxígeno completada para {paciente.nombre}")
        
        if pacientes_procesados:
            self.session.commit()
        
        return pacientes_procesados
    
    def _actualizar_estado_cama_post_oxigeno(
        self, 
        paciente: Paciente, 
        cama: Cama
    ) -> None:
        """Actualiza el estado de la cama después de la espera de oxígeno."""
        from app.services.asignacion_service import AsignacionService
        
        service = AsignacionService(self.session)
        
        if service.paciente_requiere_nueva_cama(paciente, cama):
            cama.estado = EstadoCamaEnum.CAMA_EN_ESPERA
            cama.mensaje_estado = "Paciente requiere traslado"
            paciente.requiere_nueva_cama = True
        elif service.puede_sugerir_alta(paciente):
            cama.estado = EstadoCamaEnum.ALTA_SUGERIDA
            cama.mensaje_estado = "Se sugiere evaluar alta"
        
        cama.estado_updated_at = datetime.utcnow()
        self.session.add(cama)
    
    def omitir_espera_oxigeno(self, paciente_id: str) -> Paciente:
        """
        Omite la espera de oxígeno y procesa inmediatamente.
        
        Args:
            paciente_id: ID del paciente
        
        Returns:
            El paciente actualizado
        """
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            raise ValueError(f"Paciente {paciente_id} no encontrado")
        
        # Limpiar campos de espera
        paciente.oxigeno_desactivado_at = None
        paciente.esperando_evaluacion_oxigeno = False
        paciente.requerimientos_oxigeno_previos = None
        
        # Actualizar cama si existe
        if paciente.cama_id:
            cama = self.cama_repo.obtener_por_id(paciente.cama_id)
            if cama:
                self._actualizar_estado_cama_post_oxigeno(paciente, cama)
        
        self.session.add(paciente)
        self.session.commit()
        
        logger.info(f"Espera de oxígeno omitida para {paciente.nombre}")
        
        return paciente