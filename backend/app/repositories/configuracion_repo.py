"""
Repository de Configuración.
"""
from typing import Optional
from sqlmodel import Session, select
from datetime import datetime

from app.repositories.base import BaseRepository
from app.models.configuracion import ConfiguracionSistema, LogActividad


class ConfiguracionRepository(BaseRepository[ConfiguracionSistema]):
    """Repository para operaciones de configuración."""
    
    def __init__(self, session: Session):
        super().__init__(session, ConfiguracionSistema)
    
    def obtener_configuracion(self) -> Optional[ConfiguracionSistema]:
        """
        Obtiene la configuración del sistema.
        
        Returns:
            La configuración o None
        """
        return self.session.exec(select(ConfiguracionSistema)).first()
    
    def obtener_o_crear(self) -> ConfiguracionSistema:
        """
        Obtiene la configuración o crea una por defecto.
        
        Returns:
            La configuración
        """
        config = self.obtener_configuracion()
        if not config:
            config = ConfiguracionSistema()
            self.session.add(config)
            self.session.commit()
            self.session.refresh(config)
        return config
    
    def actualizar_configuracion(
        self,
        modo_manual: Optional[bool] = None,
        tiempo_limpieza: Optional[int] = None,
        tiempo_oxigeno: Optional[int] = None
    ) -> ConfiguracionSistema:
        """
        Actualiza la configuración del sistema.
        
        Args:
            modo_manual: Nuevo valor para modo manual
            tiempo_limpieza: Nuevo tiempo de limpieza
            tiempo_oxigeno: Nuevo tiempo de espera oxígeno
        
        Returns:
            La configuración actualizada
        """
        config = self.obtener_o_crear()
        
        if modo_manual is not None:
            config.modo_manual = modo_manual
        if tiempo_limpieza is not None:
            config.tiempo_limpieza_segundos = tiempo_limpieza
        if tiempo_oxigeno is not None:
            config.tiempo_espera_oxigeno_segundos = tiempo_oxigeno
        
        config.updated_at = datetime.utcnow()
        
        return self.guardar(config)
    
    def es_modo_manual(self) -> bool:
        """
        Verifica si el sistema está en modo manual.
        
        Returns:
            True si está en modo manual
        """
        config = self.obtener_configuracion()
        return config.modo_manual if config else False


class LogActividadRepository(BaseRepository[LogActividad]):
    """Repository para logs de actividad."""
    
    def __init__(self, session: Session):
        super().__init__(session, LogActividad)
    
    def registrar(
        self,
        tipo: str,
        descripcion: str,
        hospital_id: Optional[str] = None,
        paciente_id: Optional[str] = None,
        cama_id: Optional[str] = None,
        datos_extra: Optional[str] = None
    ) -> LogActividad:
        """
        Registra una actividad.
        
        Args:
            tipo: Tipo de actividad
            descripcion: Descripción
            hospital_id: ID del hospital (opcional)
            paciente_id: ID del paciente (opcional)
            cama_id: ID de la cama (opcional)
            datos_extra: JSON con datos adicionales
        
        Returns:
            El log creado
        """
        log = LogActividad(
            tipo=tipo,
            descripcion=descripcion,
            hospital_id=hospital_id,
            paciente_id=paciente_id,
            cama_id=cama_id,
            datos_extra=datos_extra
        )
        self.session.add(log)
        self.session.commit()
        self.session.refresh(log)
        return log
    
    def obtener_por_hospital(
        self,
        hospital_id: str,
        limite: int = 100
    ) -> list:
        """
        Obtiene logs de un hospital.
        
        Args:
            hospital_id: ID del hospital
            limite: Máximo de registros
        
        Returns:
            Lista de logs
        """
        query = (
            select(LogActividad)
            .where(LogActividad.hospital_id == hospital_id)
            .order_by(LogActividad.created_at.desc())
            .limit(limite)
        )
        return list(self.session.exec(query).all())