"""
Repository de Cama.
"""
from typing import Optional, List
from sqlmodel import Session, select
from datetime import datetime

from app.repositories.base import BaseRepository
from app.models.cama import Cama
from app.models.sala import Sala
from app.models.servicio import Servicio
from app.models.enums import EstadoCamaEnum, TipoServicioEnum


class CamaRepository(BaseRepository[Cama]):
    """Repository para operaciones de camas."""
    
    def __init__(self, session: Session):
        super().__init__(session, Cama)
    
    def obtener_por_identificador(self, identificador: str) -> Optional[Cama]:
        """
        Obtiene una cama por su identificador.
        
        Args:
            identificador: Identificador de la cama (ej: "MED-501-A")
        
        Returns:
            La cama o None
        """
        query = select(Cama).where(Cama.identificador == identificador)
        return self.session.exec(query).first()
    
    def obtener_libres_por_hospital(self, hospital_id: str) -> List[Cama]:
        """
        Obtiene las camas libres de un hospital.
        
        Args:
            hospital_id: ID del hospital
        
        Returns:
            Lista de camas libres
        """
        query = (
            select(Cama)
            .join(Sala)
            .join(Servicio)
            .where(
                Servicio.hospital_id == hospital_id,
                Cama.estado == EstadoCamaEnum.LIBRE
            )
        )
        return list(self.session.exec(query).all())
    
    def obtener_por_servicio(
        self, 
        servicio_id: str, 
        solo_libres: bool = False
    ) -> List[Cama]:
        """
        Obtiene las camas de un servicio.
        
        Args:
            servicio_id: ID del servicio
            solo_libres: Si True, solo retorna camas libres
        
        Returns:
            Lista de camas
        """
        query = select(Cama).join(Sala).where(Sala.servicio_id == servicio_id)
        
        if solo_libres:
            query = query.where(Cama.estado == EstadoCamaEnum.LIBRE)
        
        return list(self.session.exec(query).all())
    
    def obtener_por_tipo_servicio(
        self,
        hospital_id: str,
        tipo_servicio: TipoServicioEnum,
        solo_libres: bool = False
    ) -> List[Cama]:
        """
        Obtiene camas por tipo de servicio.
        
        Args:
            hospital_id: ID del hospital
            tipo_servicio: Tipo de servicio
            solo_libres: Si True, solo retorna camas libres
        
        Returns:
            Lista de camas
        """
        query = (
            select(Cama)
            .join(Sala)
            .join(Servicio)
            .where(
                Servicio.hospital_id == hospital_id,
                Servicio.tipo == tipo_servicio
            )
        )
        
        if solo_libres:
            query = query.where(Cama.estado == EstadoCamaEnum.LIBRE)
        
        return list(self.session.exec(query).all())
    
    def obtener_en_limpieza(self) -> List[Cama]:
        """
        Obtiene camas en estado de limpieza.
        
        Returns:
            Lista de camas en limpieza
        """
        query = select(Cama).where(Cama.estado == EstadoCamaEnum.EN_LIMPIEZA)
        return list(self.session.exec(query).all())
    
    def cambiar_estado(
        self,
        cama: Cama,
        nuevo_estado: EstadoCamaEnum,
        mensaje: Optional[str] = None
    ) -> Cama:
        """
        Cambia el estado de una cama.
        
        Args:
            cama: La cama a modificar
            nuevo_estado: Nuevo estado
            mensaje: Mensaje de estado opcional
        
        Returns:
            La cama actualizada
        """
        cama.estado = nuevo_estado
        cama.mensaje_estado = mensaje
        cama.estado_updated_at = datetime.utcnow()
        
        # Si entra en limpieza, registrar inicio
        if nuevo_estado == EstadoCamaEnum.EN_LIMPIEZA:
            cama.limpieza_inicio = datetime.utcnow()
        elif nuevo_estado == EstadoCamaEnum.LIBRE:
            cama.limpieza_inicio = None
        
        return self.guardar(cama)
    
    def contar_por_estado(self, hospital_id: str) -> dict:
        """
        Cuenta camas por estado en un hospital.
        
        Args:
            hospital_id: ID del hospital
        
        Returns:
            Diccionario con conteos por estado
        """
        from app.repositories.hospital_repo import HospitalRepository
        
        hospital_repo = HospitalRepository(self.session)
        camas = hospital_repo.obtener_camas_hospital(hospital_id)
        
        conteos = {estado.value: 0 for estado in EstadoCamaEnum}
        for cama in camas:
            conteos[cama.estado.value] += 1
        
        return conteos