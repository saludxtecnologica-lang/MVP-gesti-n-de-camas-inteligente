"""
Servicio de Asignación de Camas.
Contiene la lógica principal de asignación.
"""
from typing import Optional, List, Tuple
from sqlmodel import Session, select
from dataclasses import dataclass
from datetime import datetime
import json
import logging

from app.models.paciente import Paciente
from app.models.cama import Cama
from app.models.sala import Sala
from app.models.servicio import Servicio
from app.models.hospital import Hospital
from app.models.enums import (
    EstadoCamaEnum,
    EstadoListaEsperaEnum,
    ComplejidadEnum,
    TipoServicioEnum,
    TipoAislamientoEnum,
    TipoEnfermedadEnum,
    SexoEnum,
    MAPEO_COMPLEJIDAD_SERVICIO,
    MAPEO_ENFERMEDAD_SERVICIO,
    AISLAMIENTOS_SALA_INDIVIDUAL,
    AISLAMIENTOS_SALA_COMPARTIDA,
    SERVICIOS_SOLO_ADULTOS,
    SERVICIOS_PEDIATRICOS,
    TODOS_REQUERIMIENTOS_OXIGENO,
    NIVEL_COMPLEJIDAD_OXIGENO,
)
from app.repositories.paciente_repo import PacienteRepository
from app.repositories.cama_repo import CamaRepository
from app.repositories.hospital_repo import HospitalRepository
from app.core.exceptions import (
    ValidationError,
    PacienteNotFoundError,
    CamaNotFoundError,
    CamaNoDisponibleError,
)

from app.services.compatibilidad_service import (
    CompatibilidadService,
    verificar_y_actualizar_sexo_sala_al_egreso,
    verificar_y_actualizar_sexo_sala_al_ingreso,
)

from app.core.websocket_manager import manager

logger = logging.getLogger("gestion_camas.asignacion")


@dataclass
class ResultadoAsignacion:
    """Resultado de una operación de asignación."""
    exito: bool
    mensaje: str
    cama_id: Optional[str] = None
    paciente_id: Optional[str] = None


@dataclass
class ResultadoDescalajeOxigeno:
    """Resultado del análisis de descalaje de oxígeno."""
    hubo_descalaje: bool
    nivel_anterior: int  # 0=ninguno, 1=baja, 2=UTI, 3=UCI
    nivel_nuevo: int
    requerimientos_anteriores: List[str]
    requerimientos_nuevos: List[str]


@dataclass
class CamaDisponibleRed:
    """Representa una cama disponible en la red hospitalaria."""
    cama_id: str
    cama_identificador: str
    hospital_id: str
    hospital_nombre: str
    hospital_codigo: str
    servicio_id: str
    servicio_nombre: str
    servicio_tipo: str
    sala_id: str
    sala_numero: int
    sala_es_individual: bool


@dataclass
class ResultadoBusquedaRed:
    """Resultado de búsqueda de camas en la red hospitalaria."""
    encontradas: bool
    camas: List[CamaDisponibleRed]
    mensaje: str
    hospital_origen_id: str
    paciente_id: str


class AsignacionService:
    """
    Servicio para gestión de asignación de camas.
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.paciente_repo = PacienteRepository(session)
        self.cama_repo = CamaRepository(session)
        self.hospital_repo = HospitalRepository(session)
    
    # ============================================
    # CÁLCULO DE COMPLEJIDAD
    # ============================================
    
    def calcular_complejidad(self, paciente: Paciente) -> ComplejidadEnum:
        """Calcula la complejidad requerida del paciente."""
        reqs_uci = paciente.get_requerimientos_lista("requerimientos_uci")
        reqs_uti = paciente.get_requerimientos_lista("requerimientos_uti")
        reqs_baja = paciente.get_requerimientos_lista("requerimientos_baja")
        
        if reqs_uci:
            return ComplejidadEnum.ALTA
        if reqs_uti:
            return ComplejidadEnum.MEDIA
        if reqs_baja:
            return ComplejidadEnum.BAJA
        return ComplejidadEnum.NINGUNA
    
    # ============================================
    # DETECCIÓN DE DESCALAJE DE OXÍGENO
    # ============================================
    
    def obtener_nivel_oxigeno_maximo(self, requerimientos: List[str]) -> int:
        """
        Obtiene el nivel máximo de oxígeno de una lista de requerimientos.
        
        Retorna:
            0 = sin oxígeno
            1 = baja (naricera, multiventuri)
            2 = UTI (reservorio, CNAF, VMNI)
            3 = UCI (VMI)
        """
        nivel_max = 0
        for req in requerimientos:
            if req in NIVEL_COMPLEJIDAD_OXIGENO:
                nivel = NIVEL_COMPLEJIDAD_OXIGENO[req]
                nivel_max = max(nivel_max, nivel)
        return nivel_max
    
    def detectar_descalaje_oxigeno(
        self,
        reqs_anteriores_baja: List[str],
        reqs_anteriores_uti: List[str],
        reqs_anteriores_uci: List[str],
        reqs_nuevos_baja: List[str],
        reqs_nuevos_uti: List[str],
        reqs_nuevos_uci: List[str]
    ) -> ResultadoDescalajeOxigeno:
        """
        Detecta si hubo un descalaje de oxígeno (bajada de nivel).
        
        Un descalaje ocurre cuando:
        - Se desmarca un oxígeno de nivel superior y se marca uno inferior
        - O se desmarca un oxígeno y no se marca ninguno
        """
        # Combinar todos los requerimientos anteriores y nuevos
        todos_anteriores = reqs_anteriores_baja + reqs_anteriores_uti + reqs_anteriores_uci
        todos_nuevos = reqs_nuevos_baja + reqs_nuevos_uti + reqs_nuevos_uci
        
        # Filtrar solo requerimientos de oxígeno
        oxigeno_anterior = [r for r in todos_anteriores if r in TODOS_REQUERIMIENTOS_OXIGENO]
        oxigeno_nuevo = [r for r in todos_nuevos if r in TODOS_REQUERIMIENTOS_OXIGENO]
        
        # Calcular nivel máximo anterior y nuevo
        nivel_anterior = self.obtener_nivel_oxigeno_maximo(oxigeno_anterior)
        nivel_nuevo = self.obtener_nivel_oxigeno_maximo(oxigeno_nuevo)
        
        # Hay descalaje si el nivel bajó (y antes había algún oxígeno)
        hubo_descalaje = nivel_anterior > 0 and nivel_nuevo < nivel_anterior
        
        logger.debug(
            f"Análisis descalaje O2: anterior={oxigeno_anterior} (nivel {nivel_anterior}), "
            f"nuevo={oxigeno_nuevo} (nivel {nivel_nuevo}), descalaje={hubo_descalaje}"
        )
        
        return ResultadoDescalajeOxigeno(
            hubo_descalaje=hubo_descalaje,
            nivel_anterior=nivel_anterior,
            nivel_nuevo=nivel_nuevo,
            requerimientos_anteriores=oxigeno_anterior,
            requerimientos_nuevos=oxigeno_nuevo
        )
    
    # ============================================
    # BÚSQUEDA DE CAMAS
    # ============================================
    
    def buscar_cama_compatible(
        self,
        paciente: Paciente,
        hospital_id: str
    ) -> Optional[Cama]:
        """Busca una cama compatible para el paciente."""
        camas_libres = self.cama_repo.obtener_libres_por_hospital(hospital_id)
        
        if not camas_libres:
            logger.debug(f"No hay camas libres en hospital {hospital_id}")
            return None
        
        camas_ordenadas = self._ordenar_camas_por_preferencia(camas_libres, paciente)
        
        for cama in camas_ordenadas:
            if self._es_cama_compatible(cama, paciente):
                servicio = cama.sala.servicio if cama.sala else None
                logger.info(
                    f"Cama compatible encontrada: {cama.identificador} "
                    f"(servicio: {servicio.tipo.value if servicio else 'N/A'}) "
                    f"para paciente {paciente.nombre}"
                )
                return cama
        
        logger.info(f"No se encontró cama compatible para {paciente.nombre}")
        return None
    
    def _ordenar_camas_por_preferencia(
        self,
        camas: List[Cama],
        paciente: Paciente
    ) -> List[Cama]:
        """Ordena camas por preferencia según el paciente."""
        complejidad = self.calcular_complejidad(paciente)
        servicios_complejidad = MAPEO_COMPLEJIDAD_SERVICIO.get(complejidad, [])
        servicios_enfermedad = MAPEO_ENFERMEDAD_SERVICIO.get(paciente.tipo_enfermedad, [])
        
        def puntaje_cama(cama: Cama) -> int:
            puntaje = 0
            sala = cama.sala
            servicio = sala.servicio if sala else None
            
            if not servicio:
                return -1000
            
            if servicio.tipo in servicios_complejidad:
                indice = servicios_complejidad.index(servicio.tipo)
                puntaje += 100 - (indice * 20)
            
            if servicio.tipo in servicios_enfermedad:
                indice = servicios_enfermedad.index(servicio.tipo)
                puntaje += 50 - (indice * 10)
            
            if sala and sala.sexo_asignado == paciente.sexo:
                puntaje += 40
            elif sala and not sala.sexo_asignado:
                puntaje += 20
            
            if paciente.tipo_aislamiento in AISLAMIENTOS_SALA_INDIVIDUAL:
                if sala and sala.es_individual:
                    puntaje += 75
            
            if servicio.tipo == TipoServicioEnum.AISLAMIENTO:
                if paciente.tipo_aislamiento not in AISLAMIENTOS_SALA_INDIVIDUAL:
                    puntaje -= 30
            
            return puntaje
        
        return sorted(camas, key=puntaje_cama, reverse=True)
    
    def _es_cama_compatible(self, cama: Cama, paciente: Paciente) -> bool:
        """
        Verifica si una cama es compatible con un paciente.
        
        INCLUYE verificación de tipo de enfermedad vs servicio.
        """
        sala = cama.sala
        if not sala:
            return False
        
        servicio = sala.servicio
        if not servicio:
            return False
        
        tipo_servicio = servicio.tipo
        complejidad = self.calcular_complejidad(paciente)
        
        # 1. VERIFICAR COMPLEJIDAD vs SERVICIO
        servicios_validos = MAPEO_COMPLEJIDAD_SERVICIO.get(complejidad, [])
        if tipo_servicio not in servicios_validos:
            logger.debug(f"Cama {cama.identificador}: complejidad incompatible")
            return False
        
        # 2. VERIFICAR EDAD (PEDIÁTRICO vs ADULTO)
        if paciente.es_pediatrico:
            if tipo_servicio != TipoServicioEnum.PEDIATRIA:
                logger.debug(f"Cama {cama.identificador}: paciente pediátrico no puede ir a {tipo_servicio.value}")
                return False
        else:
            if tipo_servicio == TipoServicioEnum.PEDIATRIA:
                logger.debug(f"Cama {cama.identificador}: paciente adulto no puede ir a pediatría")
                return False
        
        # 3. VERIFICAR SEXO DE SALA
        if tipo_servicio == TipoServicioEnum.OBSTETRICIA:
            if paciente.sexo != SexoEnum.MUJER:
                logger.debug(f"Cama {cama.identificador}: obstetricia solo acepta mujeres")
                return False
        
        if sala.sexo_asignado and sala.sexo_asignado != paciente.sexo:
            logger.debug(f"Cama {cama.identificador}: sexo de sala incompatible")
            return False
        
        # 4. VERIFICAR AISLAMIENTO vs TIPO DE SALA
        requiere_individual = paciente.tipo_aislamiento in AISLAMIENTOS_SALA_INDIVIDUAL
        if requiere_individual:
            if not sala.es_individual:
                if tipo_servicio not in [TipoServicioEnum.UCI, TipoServicioEnum.UTI, TipoServicioEnum.AISLAMIENTO]:
                    logger.debug(f"Cama {cama.identificador}: requiere aislamiento individual")
                    return False
        
        # 5. VERIFICAR TIPO DE ENFERMEDAD vs SERVICIO
        tipo_enfermedad = paciente.tipo_enfermedad
        
        # Obstetricia: SOLO enfermedad obstétrica o embarazadas
        if tipo_servicio == TipoServicioEnum.OBSTETRICIA:
            if tipo_enfermedad != TipoEnfermedadEnum.OBSTETRICA and not paciente.es_embarazada:
                logger.debug(f"Cama {cama.identificador}: obstetricia solo acepta obstétrica/embarazada")
                return False
        
        # Enfermedad obstétrica solo va a obstetricia (excepto UCI/UTI)
        if tipo_enfermedad == TipoEnfermedadEnum.OBSTETRICA:
            if tipo_servicio not in [TipoServicioEnum.OBSTETRICIA, TipoServicioEnum.UCI, TipoServicioEnum.UTI]:
                logger.debug(f"Cama {cama.identificador}: obstétrica debe ir a obstetricia")
                return False
        
        # ============================================
        # NUEVO: Verificar compatibilidad enfermedad-servicio para Medicina/Cirugía
        # ============================================
        
        # UCI, UTI, Aislamiento y Pediatría aceptan cualquier tipo de enfermedad
        if tipo_servicio in [TipoServicioEnum.UCI, TipoServicioEnum.UTI, 
                             TipoServicioEnum.AISLAMIENTO, TipoServicioEnum.PEDIATRIA]:
            pass  # Aceptan cualquier tipo de enfermedad
        
        # Medicina: solo enfermedades médicas y geriátricas (y como segunda opción otras)
        elif tipo_servicio == TipoServicioEnum.MEDICINA:
            servicios_enfermedad = MAPEO_ENFERMEDAD_SERVICIO.get(tipo_enfermedad, [])
            if TipoServicioEnum.MEDICINA not in servicios_enfermedad:
                logger.debug(
                    f"Cama {cama.identificador}: enfermedad {tipo_enfermedad.value} "
                    f"no es compatible con Medicina"
                )
                return False
        
        # Cirugía: no acepta obstétricas (ya verificado arriba) y tiene prioridad para quirúrgicas
        elif tipo_servicio == TipoServicioEnum.CIRUGIA:
            servicios_enfermedad = MAPEO_ENFERMEDAD_SERVICIO.get(tipo_enfermedad, [])
            if TipoServicioEnum.CIRUGIA not in servicios_enfermedad:
                logger.debug(
                    f"Cama {cama.identificador}: enfermedad {tipo_enfermedad.value} "
                    f"no es compatible con Cirugía"
                )
                return False
        
        # Médico-Quirúrgico: acepta la mayoría excepto obstétrica
        elif tipo_servicio == TipoServicioEnum.MEDICO_QUIRURGICO:
            if tipo_enfermedad == TipoEnfermedadEnum.OBSTETRICA:
                return False  # Ya verificado arriba, pero por seguridad
        
        logger.debug(f"Cama {cama.identificador}: COMPATIBLE con paciente {paciente.nombre}")
        return True
    
    # ============================================
    # VERIFICACIÓN DE DISPONIBILIDAD EN RED
    # ============================================
    
    def verificar_disponibilidad_tipo_cama_hospital(
        self,
        paciente: Paciente,
        hospital_id: str
    ) -> Tuple[bool, str]:
        """
        Verifica si un hospital tiene el tipo de cama que requiere el paciente.
        
        MEJORADO: Ahora verifica si realmente hay camas LIBRES compatibles,
        no solo si existe el tipo de servicio.
        
        Args:
            paciente: Paciente a verificar
            hospital_id: ID del hospital a verificar
        
        Returns:
            Tuple (tiene_tipo_cama, mensaje_explicativo)
        """
        complejidad = self.calcular_complejidad(paciente)
        servicios_requeridos = MAPEO_COMPLEJIDAD_SERVICIO.get(complejidad, [])
        
        # Buscar servicios del hospital
        query = select(Servicio).where(Servicio.hospital_id == hospital_id)
        servicios = self.session.exec(query).all()
        tipos_servicios = [s.tipo for s in servicios]
        
        # ============================================
        # 1. Verificar si existe el tipo de servicio requerido
        # ============================================
        
        # Verificar complejidad
        tiene_servicio_complejidad = any(s in tipos_servicios for s in servicios_requeridos)
        if servicios_requeridos and not tiene_servicio_complejidad:
            nombres = [s.value for s in servicios_requeridos]
            return False, f"El hospital no cuenta con servicios de {', '.join(nombres)} requeridos para complejidad {complejidad.value}"
        
        # Verificar pediátrico
        if paciente.es_pediatrico:
            if TipoServicioEnum.PEDIATRIA not in tipos_servicios:
                return False, "El hospital no cuenta con servicio de Pediatría"
        
        # Verificar aislamiento individual
        if paciente.tipo_aislamiento in AISLAMIENTOS_SALA_INDIVIDUAL:
            tiene_individual = any(s.tipo in [
                TipoServicioEnum.UCI, 
                TipoServicioEnum.UTI, 
                TipoServicioEnum.AISLAMIENTO
            ] for s in servicios)
            
            if not tiene_individual:
                query_salas = (
                    select(Sala)
                    .join(Servicio)
                    .where(Servicio.hospital_id == hospital_id, Sala.es_individual == True)
                )
                salas_ind = self.session.exec(query_salas).all()
                if not salas_ind:
                    return False, f"El hospital no cuenta con salas de aislamiento individual requeridas para {paciente.tipo_aislamiento.value}"
        
        # ============================================
        # 2. Verificar si hay camas LIBRES compatibles
        # ============================================
        camas_libres = self.cama_repo.obtener_libres_por_hospital(hospital_id)
        
        if not camas_libres:
            # No hay camas libres, pero el hospital SÍ tiene el tipo de servicio
            # Dejar que continúe con la búsqueda normal (esperará en lista)
            logger.info(f"Hospital {hospital_id}: tiene servicio requerido pero sin camas libres")
            return True, "El hospital tiene el tipo de cama requerido (sin camas libres actualmente)"
        
        # Verificar si alguna cama libre es compatible
        tiene_cama_compatible = False
        for cama in camas_libres:
            if self._es_cama_compatible(cama, paciente):
                tiene_cama_compatible = True
                break
        
        if not tiene_cama_compatible:
            # Hay camas libres pero NINGUNA es compatible
            # Esto significa que el hospital NO puede atender a este paciente
            logger.info(
                f"Hospital {hospital_id}: tiene camas libres pero ninguna compatible "
                f"para paciente {paciente.nombre} (complejidad={complejidad.value}, "
                f"pediatrico={paciente.es_pediatrico}, aislamiento={paciente.tipo_aislamiento.value})"
            )
            
            # Construir mensaje explicativo
            razones = []
            if paciente.es_pediatrico:
                razones.append("paciente pediátrico")
            if complejidad in [ComplejidadEnum.ALTA, ComplejidadEnum.MEDIA]:
                razones.append(f"complejidad {complejidad.value}")
            if paciente.tipo_aislamiento in AISLAMIENTOS_SALA_INDIVIDUAL:
                razones.append(f"aislamiento {paciente.tipo_aislamiento.value}")
            
            mensaje = f"No hay camas compatibles para {', '.join(razones) if razones else 'este paciente'}"
            return False, mensaje
        
        return True, "El hospital tiene el tipo de cama requerido"
    
    def buscar_camas_en_red(
        self,
        paciente_id: str,
        hospital_origen_id: str
    ) -> ResultadoBusquedaRed:
        """
        Busca camas compatibles para un paciente en TODOS los hospitales de la red.
        
        Esta función se usa cuando el hospital de origen no tiene el tipo de cama
        que requiere el paciente.
        
        Args:
            paciente_id: ID del paciente
            hospital_origen_id: ID del hospital de origen (se excluye de la búsqueda)
        
        Returns:
            ResultadoBusquedaRed con las camas encontradas
        """
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            raise PacienteNotFoundError(paciente_id)
        
        # Obtener todos los hospitales excepto el de origen
        query_hospitales = select(Hospital).where(Hospital.id != hospital_origen_id)
        hospitales = self.session.exec(query_hospitales).all()
        
        camas_encontradas = []
        
        for hospital in hospitales:
            # Verificar si este hospital tiene el tipo de cama
            tiene_tipo, _ = self.verificar_disponibilidad_tipo_cama_hospital(paciente, hospital.id)
            if not tiene_tipo:
                continue
            
            # Buscar camas libres compatibles en este hospital
            camas_libres = self.cama_repo.obtener_libres_por_hospital(hospital.id)
            camas_ordenadas = self._ordenar_camas_por_preferencia(camas_libres, paciente)
            
            for cama in camas_ordenadas:
                if self._es_cama_compatible(cama, paciente):
                    sala = cama.sala
                    servicio = sala.servicio if sala else None
                    
                    if servicio:
                        camas_encontradas.append(CamaDisponibleRed(
                            cama_id=cama.id,
                            cama_identificador=cama.identificador,
                            hospital_id=hospital.id,
                            hospital_nombre=hospital.nombre,
                            hospital_codigo=hospital.codigo,
                            servicio_id=servicio.id,
                            servicio_nombre=servicio.nombre,
                            servicio_tipo=servicio.tipo.value,
                            sala_id=sala.id,
                            sala_numero=sala.numero,
                            sala_es_individual=sala.es_individual
                        ))
        
        encontradas = len(camas_encontradas) > 0
        
        if encontradas:
            mensaje = f"Se encontraron {len(camas_encontradas)} cama(s) disponible(s) en la red"
        else:
            mensaje = "No se encontraron camas compatibles en ningún hospital de la red"
        
        logger.info(f"Búsqueda en red para {paciente.nombre}: {mensaje}")
        
        return ResultadoBusquedaRed(
            encontradas=encontradas,
            camas=camas_encontradas,
            mensaje=mensaje,
            hospital_origen_id=hospital_origen_id,
            paciente_id=paciente_id
        )
    
    # ============================================
    # ASIGNACIÓN
    # ============================================

    def ejecutar_asignacion(
        self,
        paciente: Paciente,
        cama: Cama
    ) -> ResultadoAsignacion:
        """
        Ejecuta la asignación de un paciente a una cama.
        
               
        1. Cama destino pasa a TRASLADO_ENTRANTE con botón "completar traslado" y "cancelar"
        
        2. Si paciente HOSPITALIZADO (tiene cama_id):
           - Cama origen pasa a TRASLADO_CONFIRMADO con botón "ver" y "cancelar"
           
        3. Si paciente DERIVADO (derivacion_estado == "aceptada"):
           - Cama origen (en hospital origen) se mantiene en DERIVACION_CONFIRMADA
           - Se actualiza mensaje para mostrar botón "confirmar egreso"
        """
        if cama.estado != EstadoCamaEnum.LIBRE:
            return ResultadoAsignacion(
                exito=False,
                mensaje=f"La cama {cama.identificador} no está disponible"
            )
        
        # Actualizar cama destino a TRASLADO_ENTRANTE
        cama.estado = EstadoCamaEnum.TRASLADO_ENTRANTE
        cama.mensaje_estado = f"Esperando a {paciente.nombre}"
        cama.estado_updated_at = datetime.utcnow()
        self.session.add(cama)
        
        es_derivado = paciente.derivacion_estado == "aceptada"
        
        # Si paciente HOSPITALIZADO (tiene cama en este hospital)
        if paciente.cama_id and not es_derivado:
            cama_origen = self.cama_repo.obtener_por_id(paciente.cama_id)
            if cama_origen:
                cama_origen.estado = EstadoCamaEnum.TRASLADO_CONFIRMADO
                cama_origen.mensaje_estado = f"Traslado confirmado a {cama.identificador}"
                cama_origen.cama_asignada_destino = cama.id  # Referencia a cama destino
                cama_origen.estado_updated_at = datetime.utcnow()
                self.session.add(cama_origen)
                logger.info(f"Cama origen {cama_origen.identificador} -> TRASLADO_CONFIRMADO")
        
        # Si paciente DERIVADO (tiene cama en hospital origen)
        elif es_derivado and paciente.cama_origen_derivacion_id:
            cama_origen_derivacion = self.cama_repo.obtener_por_id(paciente.cama_origen_derivacion_id)
            if cama_origen_derivacion:
                # Actualizar mensaje para indicar que puede confirmar egreso
                cama_origen_derivacion.mensaje_estado = f"Cama asignada en destino - Confirmar egreso"
                cama_origen_derivacion.cama_asignada_destino = cama.id  # Referencia a cama destino
                cama_origen_derivacion.estado_updated_at = datetime.utcnow()
                self.session.add(cama_origen_derivacion)
                logger.info(f"Cama origen derivación {cama_origen_derivacion.identificador} - actualizado mensaje egreso")
        
        # Actualizar paciente
        paciente.cama_destino_id = cama.id
        paciente.estado_lista_espera = EstadoListaEsperaEnum.ASIGNADO
        self.session.add(paciente)
        
        from app.services.compatibilidad_service import verificar_y_actualizar_sexo_sala_al_ingreso
        verificar_y_actualizar_sexo_sala_al_ingreso(self.session, cama, paciente)

        self.session.commit()
        
        logger.info(f"Paciente {paciente.nombre} asignado a cama {cama.identificador}")
        
        return ResultadoAsignacion(
            exito=True,
            mensaje=f"Paciente asignado a cama {cama.identificador}",
            cama_id=cama.id,
            paciente_id=paciente.id
        )
    
    async def ejecutar_asignacion_automatica(
        self,
        hospital_id: str
    ) -> List[ResultadoAsignacion]:
        """Ejecuta asignación automática para pacientes en espera."""
        resultados = []
        pacientes = self.paciente_repo.obtener_en_lista_espera(hospital_id)
        
        for paciente in pacientes:
            if paciente.estado_lista_espera == EstadoListaEsperaEnum.ASIGNADO:
                continue
            
            # Saltar pacientes en espera de evaluación de oxígeno
            if paciente.esperando_evaluacion_oxigeno:
                continue
            
            cama = self.buscar_cama_compatible(paciente, hospital_id)
            
            if cama:
                resultado = self.ejecutar_asignacion(paciente, cama)
                resultados.append(resultado)
                
                if resultado.exito:
                    await manager.send_notification(
                        {
                            "tipo": "asignacion_automatica",
                            "paciente_id": paciente.id,
                            "paciente_nombre": paciente.nombre,
                            "cama_id": cama.id,
                            "cama_identificador": cama.identificador,
                            "hospital_id": hospital_id,
                        },
                        notification_type="asignacion",
                        play_sound=True
                    )
        
        return resultados
    
    # ============================================
    # LISTA DE ESPERA
    # ============================================
    
    def agregar_a_cola(self, paciente: Paciente) -> None:
        """Agrega un paciente a la cola de espera."""
        from app.services.prioridad_service import PrioridadService, gestor_colas_global
        
        prioridad_service = PrioridadService(self.session)
        prioridad = prioridad_service.calcular_prioridad(paciente)
        
        cola = gestor_colas_global.obtener_cola(paciente.hospital_id)
        cola.agregar(paciente.id, prioridad)
        
        self.paciente_repo.agregar_a_lista_espera(paciente, prioridad)
        
        logger.info(f"Paciente {paciente.nombre} agregado a lista con prioridad {prioridad}")
    
    def remover_de_cola(self, paciente: Paciente) -> None:
        """Remueve un paciente de la cola de espera."""
        from app.services.prioridad_service import gestor_colas_global
        
        cola = gestor_colas_global.obtener_cola(paciente.hospital_id)
        cola.remover(paciente.id)
        
        self.paciente_repo.remover_de_lista_espera(paciente)
        
        logger.info(f"Paciente {paciente.nombre} removido de lista de espera")
    
    # ============================================
    # BÚSQUEDA DE CAMA PARA HOSPITALIZADO
    # ============================================
    
    def iniciar_busqueda_cama(self, paciente_id: str) -> ResultadoAsignacion:
        """Inicia búsqueda de nueva cama para paciente hospitalizado."""
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            raise PacienteNotFoundError(paciente_id)
        
        if not paciente.cama_id:
            raise ValidationError("El paciente no tiene cama asignada")
        
        cama_actual = self.cama_repo.obtener_por_id(paciente.cama_id)
        if cama_actual:
            cama_actual.estado = EstadoCamaEnum.TRASLADO_SALIENTE
            cama_actual.mensaje_estado = "Paciente buscando nueva cama"
            cama_actual.estado_updated_at = datetime.utcnow()
            self.session.add(cama_actual)
            
            # Guardar servicio de origen para priorización
            if cama_actual.sala and cama_actual.sala.servicio:
                paciente.origen_servicio_nombre = cama_actual.sala.servicio.nombre

        # Limpiar flag de espera de oxígeno
        paciente.esperando_evaluacion_oxigeno = False
        paciente.oxigeno_desactivado_at = None
        
        self.agregar_a_cola(paciente)
        
        self.session.commit()
        
        return ResultadoAsignacion(
            exito=True,
            mensaje="Búsqueda de cama iniciada",
            paciente_id=paciente_id
        )
    
    def cancelar_busqueda(self, paciente_id: str) -> ResultadoAsignacion:
        """Cancela la búsqueda de cama."""
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            raise PacienteNotFoundError(paciente_id)
        
        if paciente.cama_id:
            cama = self.cama_repo.obtener_por_id(paciente.cama_id)
            if cama:
                cama.estado = EstadoCamaEnum.CAMA_EN_ESPERA
                cama.mensaje_estado = "Paciente requiere nueva cama"
                cama.estado_updated_at = datetime.utcnow()
                self.session.add(cama)
        
        self.remover_de_cola(paciente)
        
        self.session.commit()
        
        return ResultadoAsignacion(
            exito=True,
            mensaje="Búsqueda cancelada",
            paciente_id=paciente_id
        )
    
    # ============================================
    # OMITIR PAUSA DE OXÍGENO
    # ============================================
    
    def omitir_pausa_oxigeno(self, paciente_id: str) -> ResultadoAsignacion:
        """
        Omite la pausa de evaluación de oxígeno.
        Permite al paciente buscar nueva cama inmediatamente.
        """
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            raise PacienteNotFoundError(paciente_id)
        
        if not paciente.esperando_evaluacion_oxigeno:
            raise ValidationError("El paciente no está en espera de evaluación de oxígeno")
        
        # Limpiar flags de espera
        paciente.esperando_evaluacion_oxigeno = False
        paciente.oxigeno_desactivado_at = None
        paciente.requerimientos_oxigeno_previos = None
        self.session.add(paciente)
        
        # Actualizar mensaje de cama
        if paciente.cama_id:
            cama = self.cama_repo.obtener_por_id(paciente.cama_id)
            if cama and cama.estado == EstadoCamaEnum.CAMA_EN_ESPERA:
                cama.mensaje_estado = "Paciente requiere nueva cama"
                cama.estado_updated_at = datetime.utcnow()
                self.session.add(cama)
        
        self.session.commit()
        
        logger.info(f"Pausa de oxígeno omitida para paciente {paciente.nombre}")
        
        return ResultadoAsignacion(
            exito=True,
            mensaje="Evaluación de oxígeno completada",
            paciente_id=paciente_id
        )
    
    # ============================================
    # UTILIDADES
    # ============================================
    
    def paciente_requiere_nueva_cama(
        self,
        paciente: 'Paciente',
        cama_actual: 'Cama'
    ) -> bool:
        """Verifica si el paciente necesita cambiar de cama."""
        from app.services.compatibilidad_service import CompatibilidadService
        
        compatibilidad_service = CompatibilidadService(self.session)
        
        # Verificación completa de compatibilidad
        es_compatible, problemas = compatibilidad_service.verificar_compatibilidad_completa(
            paciente, cama_actual
        )
        
        if not es_compatible:
            logger.info(
                f"Paciente {paciente.nombre} requiere nueva cama: "
                f"{'; '.join(problemas)}"
            )
            return True
        
        # Verificación original de compatibilidad básica
        compatible_basica = self._es_cama_compatible(cama_actual, paciente)
        
        if not compatible_basica:
            logger.info(
                f"Paciente {paciente.nombre} requiere nueva cama: "
                f"cama {cama_actual.identificador} no es compatible (verificación básica)"
            )
            return True
        
        return False
    
    def puede_sugerir_alta(self, paciente: Paciente) -> bool:
        """Verifica si se puede sugerir alta para un paciente."""
        reqs_uci = paciente.get_requerimientos_lista("requerimientos_uci")
        reqs_uti = paciente.get_requerimientos_lista("requerimientos_uti")
        reqs_baja = paciente.get_requerimientos_lista("requerimientos_baja")
        
        if reqs_uci or reqs_uti or reqs_baja:
            return False
        
        if paciente.tipo_aislamiento == TipoAislamientoEnum.AEREO:
            return False
        
        if paciente.tiene_casos_especiales():
            return False
        
        logger.info(f"Paciente {paciente.nombre}: puede sugerir alta")
        return True
    
    def evaluar_estado_post_reevaluacion(
        self,
        paciente: 'Paciente',
        cama_actual: 'Cama'
    ) -> Tuple['EstadoCamaEnum', Optional[str]]:
        """Evalúa qué estado debe tener la cama después de una reevaluación."""
        from app.services.compatibilidad_service import CompatibilidadService
        from app.models.enums import EstadoCamaEnum
        
        if self.puede_sugerir_alta(paciente):
            return EstadoCamaEnum.ALTA_SUGERIDA, "Se sugiere evaluar alta"
        
        compatibilidad_service = CompatibilidadService(self.session)
        es_compatible, problemas = compatibilidad_service.verificar_compatibilidad_completa(
            paciente, cama_actual
        )
        
        if not es_compatible:
            paciente.requiere_nueva_cama = True
            self.session.add(paciente)
            mensaje = "Paciente requiere nueva cama: " + "; ".join(problemas)
            logger.info(f"Reevaluación {paciente.nombre}: {mensaje}")
            return EstadoCamaEnum.CAMA_EN_ESPERA, mensaje
        
        if self._es_cama_compatible(cama_actual, paciente) == False:
            paciente.requiere_nueva_cama = True
            self.session.add(paciente)
            return EstadoCamaEnum.CAMA_EN_ESPERA, "Paciente requiere nueva cama"
        
        paciente.requiere_nueva_cama = False
        self.session.add(paciente)
        return EstadoCamaEnum.OCUPADA, None