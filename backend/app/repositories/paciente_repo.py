"""
Repository de Paciente.
"""
from typing import Optional, List
from sqlmodel import Session, select
from datetime import datetime

from app.repositories.base import BaseRepository
from app.models.paciente import Paciente
from app.models.enums import (
    EstadoListaEsperaEnum, 
    TipoPacienteEnum,
    EdadCategoriaEnum,
)


class PacienteRepository(BaseRepository[Paciente]):
    """Repository para operaciones de pacientes."""
    
    def __init__(self, session: Session):
        super().__init__(session, Paciente)
    
    def obtener_por_run(self, run: str) -> Optional[Paciente]:
        """
        Obtiene un paciente por su RUN.
        
        Args:
            run: RUN del paciente
        
        Returns:
            El paciente o None
        """
        query = select(Paciente).where(Paciente.run == run)
        return self.session.exec(query).first()
    
    def obtener_por_cama(self, cama_id: str) -> Optional[Paciente]:
        """
        Obtiene el paciente asignado a una cama.
        
        Args:
            cama_id: ID de la cama
        
        Returns:
            El paciente o None
        """
        query = select(Paciente).where(Paciente.cama_id == cama_id)
        return self.session.exec(query).first()
    
    def obtener_por_cama_destino(self, cama_id: str) -> Optional[Paciente]:
        """
        Obtiene el paciente que tiene como destino una cama.
        
        Args:
            cama_id: ID de la cama destino
        
        Returns:
            El paciente o None
        """
        query = select(Paciente).where(Paciente.cama_destino_id == cama_id)
        return self.session.exec(query).first()
    
    def obtener_en_lista_espera(self, hospital_id: str) -> List[Paciente]:
        """
        Obtiene pacientes en lista de espera de un hospital.
        
        Args:
            hospital_id: ID del hospital
        
        Returns:
            Lista de pacientes
        """
        query = select(Paciente).where(
            Paciente.hospital_id == hospital_id,
            Paciente.en_lista_espera == True
        ).order_by(Paciente.prioridad_calculada.desc())
        
        return list(self.session.exec(query).all())
    
    def obtener_derivados_pendientes(self, hospital_id: str) -> List[Paciente]:
        """
        Obtiene pacientes derivados pendientes hacia un hospital.
        
        Args:
            hospital_id: ID del hospital destino
        
        Returns:
            Lista de pacientes derivados
        """
        query = select(Paciente).where(
            Paciente.derivacion_hospital_destino_id == hospital_id,
            Paciente.derivacion_estado == "pendiente"
        )
        return list(self.session.exec(query).all())
    
    def obtener_derivados_aceptados(self, hospital_id: str) -> List[Paciente]:
        """
        Obtiene pacientes derivados aceptados hacia un hospital.
        
        Args:
            hospital_id: ID del hospital destino
        
        Returns:
            Lista de pacientes
        """
        query = select(Paciente).where(
            Paciente.derivacion_hospital_destino_id == hospital_id,
            Paciente.derivacion_estado == "aceptada"
        )
        return list(self.session.exec(query).all())
    
    def obtener_en_espera_oxigeno(self) -> List[Paciente]:
        """
        Obtiene pacientes esperando evaluación de oxígeno.
        
        Returns:
            Lista de pacientes
        """
        query = select(Paciente).where(
            Paciente.esperando_evaluacion_oxigeno == True,
            Paciente.oxigeno_desactivado_at.isnot(None)
        )
        return list(self.session.exec(query).all())
    
    def contar_por_tipo(self, hospital_id: str) -> dict:
        """
        Cuenta pacientes en espera por tipo.
        
        Args:
            hospital_id: ID del hospital
        
        Returns:
            Diccionario con conteos por tipo
        """
        pacientes = self.obtener_en_lista_espera(hospital_id)
        
        conteos = {
            "urgencia": 0,
            "ambulatorio": 0,
            "hospitalizado": 0,
            "derivado": 0,
        }
        
        for paciente in pacientes:
            if paciente.tipo_paciente:
                conteos[paciente.tipo_paciente.value] += 1
        
        return conteos
    
    def agregar_a_lista_espera(
        self,
        paciente: Paciente,
        prioridad: float = 0.0
    ) -> Paciente:
        """
        Agrega un paciente a la lista de espera.
        
        Args:
            paciente: El paciente
            prioridad: Prioridad calculada
        
        Returns:
            El paciente actualizado
        """
        paciente.en_lista_espera = True
        paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
        paciente.prioridad_calculada = prioridad
        paciente.timestamp_lista_espera = datetime.utcnow()
        
        return self.guardar(paciente)
    
    def remover_de_lista_espera(self, paciente: Paciente) -> Paciente:
        """
        Remueve un paciente de la lista de espera.
        
        Args:
            paciente: El paciente
        
        Returns:
            El paciente actualizado
        """
        paciente.en_lista_espera = False
        paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
        paciente.prioridad_calculada = 0.0
        paciente.timestamp_lista_espera = None
        
        return self.guardar(paciente)
    
    def marcar_asignado(self, paciente: Paciente) -> Paciente:
        """
        Marca un paciente como asignado en lista de espera.
        
        Args:
            paciente: El paciente
        
        Returns:
            El paciente actualizado
        """
        paciente.estado_lista_espera = EstadoListaEsperaEnum.ASIGNADO
        return self.guardar(paciente)
    
    @staticmethod
    def determinar_categoria_edad(edad: int) -> EdadCategoriaEnum:
        """
        Determina la categoría de edad.
        
        Args:
            edad: Edad en años
        
        Returns:
            Categoría de edad
        """
        if edad < 15:
            return EdadCategoriaEnum.PEDIATRICO
        elif edad < 60:
            return EdadCategoriaEnum.ADULTO
        else:
            return EdadCategoriaEnum.ADULTO_MAYOR