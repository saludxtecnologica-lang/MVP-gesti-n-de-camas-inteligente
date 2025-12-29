"""
Repository de Hospital.
"""
from typing import Optional, List
from sqlmodel import Session, select

from app.repositories.base import BaseRepository
from app.models.hospital import Hospital
from app.models.servicio import Servicio
from app.models.sala import Sala
from app.models.cama import Cama


class HospitalRepository(BaseRepository[Hospital]):
    """Repository para operaciones de hospitales."""
    
    def __init__(self, session: Session):
        super().__init__(session, Hospital)
    
    def obtener_por_codigo(self, codigo: str) -> Optional[Hospital]:
        """
        Obtiene un hospital por su código.
        
        Args:
            codigo: Código del hospital (ej: "PM", "LL")
        
        Returns:
            El hospital o None
        """
        query = select(Hospital).where(Hospital.codigo == codigo)
        return self.session.exec(query).first()
    
    def obtener_central(self) -> Optional[Hospital]:
        """
        Obtiene el hospital central.
        
        Returns:
            El hospital central o None
        """
        query = select(Hospital).where(Hospital.es_central == True)
        return self.session.exec(query).first()
    
    def obtener_camas_hospital(self, hospital_id: str) -> List[Cama]:
        """
        Obtiene todas las camas de un hospital.
        
        Args:
            hospital_id: ID del hospital
        
        Returns:
            Lista de camas
        """
        query = (
            select(Cama)
            .join(Sala)
            .join(Servicio)
            .where(Servicio.hospital_id == hospital_id)
            .order_by(Cama.identificador)
        )
        return list(self.session.exec(query).all())
    
    def obtener_servicios_hospital(self, hospital_id: str) -> List[Servicio]:
        """
        Obtiene los servicios de un hospital.
        
        Args:
            hospital_id: ID del hospital
        
        Returns:
            Lista de servicios
        """
        query = select(Servicio).where(Servicio.hospital_id == hospital_id)
        return list(self.session.exec(query).all())