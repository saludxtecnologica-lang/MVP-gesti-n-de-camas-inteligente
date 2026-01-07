"""
Servicio de Asignación de Camas.
Contiene la lógica principal de asignación.

ACTUALIZADO v3.0:
- PROBLEMA 1: Corregida verificación de cambio de cama con requerimientos especiales
- PROBLEMA 7: Ajustada regla de embarazada para siempre ir a obstetricia si baja complejidad
"""
from typing import Optional, List, Tuple
from sqlmodel import Session, select
from sqlmodel.orm import selectinload
from dataclasses import dataclass
from datetime import datetime
import json
import logging

from app.models.paciente import Paciente
from app.models.cama import Cama
from app.models.sala import Sala
from app.models.servicio import Servicio
from app.models.hospital import Hospital
from app.core.eventos_audibles import crear_evento_asignacion
import asyncio
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
    recalcular_sexo_sala_al_cancelar_asignacion,
    NIVEL_COMPLEJIDAD,
    _obtener_nivel_complejidad,
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
    estado: str  # Estado de la cama (libre, ocupada, reservada, etc.)
    disponible: bool  # True si está libre, False si está ocupada


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
    # OBTENER COMPLEJIDAD DE CAMA
    # ============================================
    
    def obtener_complejidad_cama(self, cama: Cama) -> ComplejidadEnum:
        """
        Obtiene la complejidad de una cama basándose en su servicio.
        
        Returns:
            ComplejidadEnum correspondiente al servicio de la cama
        """
        if not cama.sala or not cama.sala.servicio:
            return ComplejidadEnum.BAJA
        
        tipo_servicio = cama.sala.servicio.tipo
        
        if tipo_servicio == TipoServicioEnum.UCI:
            return ComplejidadEnum.ALTA
        elif tipo_servicio == TipoServicioEnum.UTI:
            return ComplejidadEnum.MEDIA
        else:
            return ComplejidadEnum.BAJA
    
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
            
            # PROBLEMA 7: Boost para obstetricia si es embarazada de baja complejidad
            if paciente.es_embarazada and complejidad in [ComplejidadEnum.BAJA, ComplejidadEnum.NINGUNA]:
                if servicio.tipo == TipoServicioEnum.OBSTETRICIA:
                    puntaje += 200  # Máxima prioridad
            
            return puntaje
        
        return sorted(camas, key=puntaje_cama, reverse=True)
    
    def _es_cama_compatible(self, cama: Cama, paciente: Paciente) -> bool:
        """
        Verifica si una cama es compatible con un paciente.

        INCLUYE verificación de tipo de enfermedad vs servicio.
        PROBLEMA 7: Embarazada de baja complejidad SIEMPRE va a obstetricia.
        """
        logger.debug(f"=== Verificando compatibilidad de {cama.identificador} para {paciente.nombre} ===")

        sala = cama.sala
        if not sala:
            logger.debug(f"Cama {cama.identificador}: Sin sala")
            return False

        servicio = sala.servicio
        if not servicio:
            logger.debug(f"Cama {cama.identificador}: Sin servicio")
            return False

        tipo_servicio = servicio.tipo
        complejidad = self.calcular_complejidad(paciente)
        logger.debug(
            f"Cama {cama.identificador}: Servicio={tipo_servicio.value}, "
            f"Complejidad paciente={complejidad.value}"
        )
        
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

        # Solo verificar sexo_asignado para camas LIBRES
        # Para camas ocupadas, el sexo puede cambiar cuando se liberen
        if cama.estado == EstadoCamaEnum.LIBRE:
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
        
        # ============================================
        # PROBLEMA 7: REGLA DE EMBARAZADA AJUSTADA
        # Embarazada de baja complejidad SOLO va a obstetricia
        # ============================================
        if paciente.es_embarazada and complejidad in [ComplejidadEnum.BAJA, ComplejidadEnum.NINGUNA]:
            if tipo_servicio != TipoServicioEnum.OBSTETRICIA:
                logger.debug(
                    f"Cama {cama.identificador}: embarazada de baja complejidad "
                    f"solo puede ir a obstetricia, no a {tipo_servicio.value}"
                )
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
        # Verificar compatibilidad enfermedad-servicio para Medicina/Cirugía
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
    ) -> Tuple[bool, bool, str]:
        """
        Verifica si un hospital tiene el tipo de cama que requiere el paciente.

        ACTUALIZADO v4.0: Ahora distingue entre:
        - No tener el tipo de servicio (debe buscar en red)
        - Tener el servicio pero sin camas libres (solo lista de espera)

        Args:
            paciente: Paciente a verificar
            hospital_id: ID del hospital a verificar

        Returns:
            Tuple (tiene_tipo_servicio, tiene_camas_libres, mensaje_explicativo)

            Casos:
            - (False, False, msg): No tiene el tipo de servicio → BUSCAR EN RED
            - (True, True, msg): Tiene servicio y camas libres → PROCEDER NORMAL
            - (True, False, msg): Tiene servicio sin camas → LISTA DE ESPERA ÚNICAMENTE
        """
        complejidad = self.calcular_complejidad(paciente)
        servicios_requeridos = MAPEO_COMPLEJIDAD_SERVICIO.get(complejidad, [])

        # Buscar servicios del hospital
        query = select(Servicio).where(Servicio.hospital_id == hospital_id)
        servicios = self.session.exec(query).all()
        tipos_servicios = [s.tipo for s in servicios]

        # Verificar si tiene al menos un servicio compatible
        servicios_disponibles = [s for s in servicios_requeridos if s in tipos_servicios]

        if not servicios_disponibles:
            # CASO 1: NO TIENE EL TIPO DE SERVICIO → BUSCAR EN RED
            nombres_requeridos = [s.value for s in servicios_requeridos]
            nombres_hospital = [s.value for s in tipos_servicios]
            return False, False, (
                f"Hospital no tiene servicios compatibles. "
                f"Requiere: {', '.join(nombres_requeridos)}. "
                f"Disponibles: {', '.join(nombres_hospital)}"
            )

        # Verificar si hay camas LIBRES en esos servicios
        cama_compatible = self.buscar_cama_compatible(paciente, hospital_id)

        if cama_compatible:
            # CASO 2: TIENE SERVICIO Y CAMAS LIBRES → PROCEDER NORMAL
            return True, True, f"Hay camas libres compatibles en el hospital"
        else:
            # CASO 3: TIENE SERVICIO PERO SIN CAMAS → SOLO LISTA DE ESPERA
            nombres_requeridos = [s.value for s in servicios_requeridos]
            return True, False, (
                f"Hospital tiene servicios compatibles ({', '.join(nombres_requeridos)}) "
                f"pero no hay camas libres disponibles actualmente"
            )
    
    def buscar_camas_en_red(
        self,
        paciente_id: str,
        hospital_origen_id: str
    ) -> ResultadoBusquedaRed:
        """
        Busca camas compatibles en toda la red hospitalaria.

        ACTUALIZADO v5.0:
        - Ahora busca TODAS las camas del tipo compatible (libres Y ocupadas)
        - Incluye información de disponibilidad
        - Ordena: libres primero, luego ocupadas

        Args:
            paciente_id: ID del paciente
            hospital_origen_id: Hospital del que excluir

        Returns:
            ResultadoBusquedaRed con las camas encontradas
        """
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            raise PacienteNotFoundError(paciente_id)

        # Calcular complejidad del paciente para obtener servicios compatibles
        complejidad = self.calcular_complejidad(paciente)
        servicios_compatibles = MAPEO_COMPLEJIDAD_SERVICIO.get(complejidad, [])

        # Obtener todos los hospitales excepto el de origen
        query = select(Hospital).where(Hospital.id != hospital_origen_id)
        hospitales = self.session.exec(query).all()

        camas_libres: List[CamaDisponibleRed] = []
        camas_ocupadas: List[CamaDisponibleRed] = []

        for hospital in hospitales:
            # Obtener TODAS las camas de servicios compatibles (no solo libres)
            # Cargar explícitamente las relaciones
            query_camas = (
                select(Cama)
                .join(Sala)
                .join(Servicio)
                .where(
                    Servicio.hospital_id == hospital.id,
                    Servicio.tipo.in_(servicios_compatibles)
                )
                .options(
                    selectinload(Cama.sala).selectinload(Sala.servicio)
                )
            )
            todas_las_camas = self.session.exec(query_camas).all()

            for cama in todas_las_camas:
                # DEBUG: Log de cada cama encontrada
                logger.debug(
                    f"Evaluando cama {cama.identificador} en {hospital.nombre}, "
                    f"estado: {cama.estado.value if hasattr(cama.estado, 'value') else cama.estado}"
                )

                # Verificar compatibilidad básica
                if self._es_cama_compatible(cama, paciente):
                    servicio = cama.sala.servicio if cama.sala else None

                    # Determinar si está disponible
                    esta_libre = cama.estado == EstadoCamaEnum.LIBRE

                    logger.debug(
                        f"Cama {cama.identificador} es compatible. Esta libre: {esta_libre}, "
                        f"Estado: {cama.estado.value if hasattr(cama.estado, 'value') else cama.estado}"
                    )

                    cama_info = CamaDisponibleRed(
                        cama_id=cama.id,
                        cama_identificador=cama.identificador,
                        hospital_id=hospital.id,
                        hospital_nombre=hospital.nombre,
                        hospital_codigo=hospital.codigo,
                        servicio_id=servicio.id if servicio else "",
                        servicio_nombre=servicio.nombre if servicio else "",
                        servicio_tipo=servicio.tipo.value if servicio else "",
                        sala_id=cama.sala.id if cama.sala else "",
                        sala_numero=cama.sala.numero if cama.sala else 0,
                        sala_es_individual=cama.sala.es_individual if cama.sala else False,
                        estado=cama.estado.value if hasattr(cama.estado, 'value') else str(cama.estado),
                        disponible=esta_libre
                    )

                    # Separar en libres y ocupadas
                    if esta_libre:
                        camas_libres.append(cama_info)
                    else:
                        camas_ocupadas.append(cama_info)
                else:
                    logger.debug(f"Cama {cama.identificador} NO es compatible")

        # Combinar: libres primero, luego ocupadas
        camas_encontradas = camas_libres + camas_ocupadas

        # Generar mensaje descriptivo
        total_camas = len(camas_encontradas)
        total_libres = len(camas_libres)
        total_ocupadas = len(camas_ocupadas)

        if total_camas == 0:
            mensaje = "No se encontraron camas compatibles en la red hospitalaria"
        elif total_libres > 0:
            mensaje = f"Se encontraron {total_libres} cama(s) libre(s) y {total_ocupadas} ocupada(s) en la red"
        else:
            mensaje = f"Se encontraron {total_ocupadas} cama(s) del tipo compatible en la red, pero todas están ocupadas"

        encontradas = total_camas > 0

        return ResultadoBusquedaRed(
            encontradas=encontradas,
            camas=camas_encontradas,
            mensaje=mensaje,
            hospital_origen_id=hospital_origen_id,
            paciente_id=paciente_id
        )
    
    # ============================================
    # ASIGNACIÓN AUTOMÁTICA
    # ============================================
    
    async def ejecutar_asignacion_automatica(
        self,
        hospital_id: str
    ) -> List[ResultadoAsignacion]:
        """Ejecuta asignación automática para un hospital."""
        from app.services.prioridad_service import gestor_colas_global
        
        resultados = []
        cola = gestor_colas_global.obtener_cola(hospital_id)
        
        # Procesar hasta que no haya más asignaciones posibles
        max_iteraciones = 100
        iteracion = 0
        
        while iteracion < max_iteraciones:
            iteracion += 1
            
            # Obtener siguiente paciente
            paciente_id = cola.obtener_siguiente()
            if not paciente_id:
                break
            
            paciente = self.paciente_repo.obtener_por_id(paciente_id)
            if not paciente:
                cola.remover(paciente_id)
                continue
            
            # Verificar que siga en lista de espera
            if not paciente.en_lista_espera:
                cola.remover(paciente_id)
                continue
            
            # Verificar si está esperando evaluación de oxígeno
            if paciente.esperando_evaluacion_oxigeno:
                continue
            
            # Buscar cama compatible
            cama = self.buscar_cama_compatible(paciente, hospital_id)
            
            if cama:
                resultado = self.asignar_cama(paciente_id, cama.id)
                resultados.append(resultado)
                
                if resultado.exito:
                    cola.remover(paciente_id)
            else:
                # No hay cama disponible, seguir con el siguiente
                break
        
        return resultados
    
    def asignar_cama(
        self,
        paciente_id: str,
        cama_id: str
    ) -> ResultadoAsignacion:
        """Asigna una cama a un paciente."""
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            raise PacienteNotFoundError(paciente_id)
        
        cama = self.cama_repo.obtener_por_id(cama_id)
        if not cama:
            raise CamaNotFoundError(cama_id)
        
        if cama.estado != EstadoCamaEnum.LIBRE:
            raise CamaNoDisponibleError(f"Cama {cama.identificador} no está libre")
        
        # ============================================
        # GUARDAR INFO PARA TTS ANTES DE MODIFICAR
        # ============================================
        servicio_origen_id = None
        servicio_origen_nombre = None
        cama_origen_identificador = None
        servicio_destino_id = None
        servicio_destino_nombre = None
        hospital_id = paciente.hospital_id  # <-- CORREGIDO: Definir hospital_id aquí
        
        # Obtener info de cama origen ANTES de modificar
        if paciente.cama_id:
            cama_origen_temp = self.cama_repo.obtener_por_id(paciente.cama_id)
            if cama_origen_temp:
                cama_origen_identificador = cama_origen_temp.identificador
                if cama_origen_temp.sala and cama_origen_temp.sala.servicio:
                    servicio_origen_id = cama_origen_temp.sala.servicio.nombre
                    servicio_origen_nombre = cama_origen_temp.sala.servicio.nombre
        
        # Obtener info del servicio destino
        if cama.sala and cama.sala.servicio:
            servicio_destino_id = cama.sala.servicio.nombre
            servicio_destino_nombre = cama.sala.servicio.nombre
        
        # Si el paciente ya tiene cama (traslado interno)
        if paciente.cama_id:
            cama_origen = self.cama_repo.obtener_por_id(paciente.cama_id)
            if cama_origen:
                # Marcar como traslado confirmado
                cama_origen.estado = EstadoCamaEnum.TRASLADO_CONFIRMADO
                cama_origen.mensaje_estado = f"Traslado a {cama.identificador}"
                cama_origen.cama_asignada_destino = cama_id
                cama_origen.estado_updated_at = datetime.utcnow()
                self.session.add(cama_origen)
        
        # Actualizar cama destino
        cama.estado = EstadoCamaEnum.TRASLADO_ENTRANTE
        cama.mensaje_estado = f"Esperando a {paciente.nombre}"
        cama.estado_updated_at = datetime.utcnow()
        self.session.add(cama)
        
        # Guardar servicio destino
        if cama.sala and cama.sala.servicio:
            paciente.servicio_destino = cama.sala.servicio.nombre
        
        # Actualizar paciente
        paciente.cama_destino_id = cama_id
        paciente.estado_lista_espera = EstadoListaEsperaEnum.ASIGNADO
        paciente.requiere_nueva_cama = False
        self.session.add(paciente)
        
        # Actualizar sexo de sala destino al momento de la asignación
        # Esto asegura que la sala quede marcada con el sexo correcto
        # antes de que el paciente llegue físicamente
        verificar_y_actualizar_sexo_sala_al_ingreso(self.session, cama, paciente)

        self.session.commit()

        logger.info(f"Cama {cama.identificador} asignada a {paciente.nombre}")

        # ============================================
        # BROADCAST TTS
        # ============================================
        try:
            evento_tts = crear_evento_asignacion(
                cama_destino_identificador=cama.identificador,
                paciente_nombre=paciente.nombre,
                servicio_origen_id=servicio_origen_id,
                servicio_origen_nombre=servicio_origen_nombre,
                servicio_destino_id=servicio_destino_id,
                servicio_destino_nombre=servicio_destino_nombre or "destino",
                cama_origen_identificador=cama_origen_identificador,
                hospital_id=hospital_id,  # <-- Ahora sí está definido
                paciente_id=str(paciente.id),
                cama_id=str(cama.id)
            )
            
            # Broadcast asíncrono
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(manager.broadcast(evento_tts))
            except RuntimeError:
                asyncio.run(manager.broadcast(evento_tts))
                
            logger.info(f"Evento TTS de asignación emitido")
        except Exception as e:
            logger.warning(f"Error emitiendo evento TTS: {e}")
            # Fallback sin TTS
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(manager.broadcast({
                    "tipo": "asignacion_completada",
                    "hospital_id": hospital_id,
                    "reload": True,
                    "play_sound": True
                }))
            except:
                pass
        
        return ResultadoAsignacion(
            exito=True,
            mensaje=f"Cama {cama.identificador} asignada",
            cama_id=cama_id,
            paciente_id=paciente_id
        )
    
    def asignar_manual_desde_lista(
        self,
        paciente_id: str,
        cama_id: str
    ) -> ResultadoAsignacion:
        """Asigna manualmente un paciente de lista de espera a una cama."""
        return self.asignar_cama(paciente_id, cama_id)
    
    def asignar_manual_desde_cama(
        self,
        paciente_id: str,
        cama_destino_id: str
    ) -> ResultadoAsignacion:
        """Inicia traslado manual desde una cama a otra."""
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            raise PacienteNotFoundError(paciente_id)
        
        if not paciente.cama_id:
            raise ValidationError("El paciente no tiene cama asignada")
        
        # Agregar a lista de espera primero
        self.agregar_a_cola(paciente)
        
        # Luego asignar la cama
        return self.asignar_cama(paciente_id, cama_destino_id)
    
    # ============================================
    # GESTIÓN DE COLA
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
                cama.estado = EstadoCamaEnum.OCUPADA
                cama.mensaje_estado = None
                cama.estado_updated_at = datetime.utcnow()
                self.session.add(cama)
        
        self.remover_de_cola(paciente)
        
        # Limpiar flags
        paciente.requiere_nueva_cama = False
        self.session.add(paciente)
        
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
        """
        Verifica si el paciente necesita cambiar de cama.
        
        PROBLEMA 1 CORREGIDO: Ahora verifica si la complejidad del paciente
        es compatible con la complejidad de la cama actual antes de decidir
        que requiere nueva cama.
        """
        from app.services.compatibilidad_service import CompatibilidadService
        
        compatibilidad_service = CompatibilidadService(self.session)
        
        # Obtener complejidades
        complejidad_paciente = self.calcular_complejidad(paciente)
        complejidad_cama = self.obtener_complejidad_cama(cama_actual)
        
        nivel_paciente = _obtener_nivel_complejidad(complejidad_paciente)
        nivel_cama = _obtener_nivel_complejidad(complejidad_cama)
        
        # Si el paciente solo tiene casos especiales y la complejidad de la cama
        # es >= a la del paciente, NO requiere nueva cama
        tiene_solo_casos_especiales = (
            paciente.tiene_casos_especiales() and
            not paciente.get_requerimientos_lista("requerimientos_uci") and
            not paciente.get_requerimientos_lista("requerimientos_uti") and
            not paciente.get_requerimientos_lista("requerimientos_baja")
        )
        
        if tiene_solo_casos_especiales and nivel_cama >= nivel_paciente:
            logger.info(
                f"Paciente {paciente.nombre}: solo tiene casos especiales y "
                f"cama actual es compatible (nivel cama: {nivel_cama}, nivel paciente: {nivel_paciente})"
            )
            return False
        
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
        """
        Evalúa qué estado debe tener la cama después de una reevaluación.
        
        PROBLEMA 1 CORREGIDO: Verifica compatibilidad de complejidad 
        antes de cambiar a CAMA_EN_ESPERA.
        """
        from app.services.compatibilidad_service import CompatibilidadService
        from app.models.enums import EstadoCamaEnum
        
        if self.puede_sugerir_alta(paciente):
            return EstadoCamaEnum.ALTA_SUGERIDA, "Se sugiere evaluar alta"
        
        # Obtener complejidades
        complejidad_paciente = self.calcular_complejidad(paciente)
        complejidad_cama = self.obtener_complejidad_cama(cama_actual)
        
        nivel_paciente = _obtener_nivel_complejidad(complejidad_paciente)
        nivel_cama = _obtener_nivel_complejidad(complejidad_cama)
        
        # PROBLEMA 1: Si solo tiene casos especiales y la cama es compatible, quedarse
        tiene_solo_casos_especiales = (
            paciente.tiene_casos_especiales() and
            not paciente.get_requerimientos_lista("requerimientos_uci") and
            not paciente.get_requerimientos_lista("requerimientos_uti") and
            not paciente.get_requerimientos_lista("requerimientos_baja")
        )
        
        if tiene_solo_casos_especiales:
            if nivel_cama >= nivel_paciente:
                logger.info(
                    f"Paciente {paciente.nombre}: solo casos especiales, "
                    f"cama compatible - permanece OCUPADA"
                )
                paciente.requiere_nueva_cama = False
                self.session.add(paciente)
                return EstadoCamaEnum.OCUPADA, None
        
        compatibilidad_service = CompatibilidadService(self.session)
        es_compatible, problemas = compatibilidad_service.verificar_compatibilidad_completa(
            paciente, cama_actual
        )
        
        if not es_compatible:
            # VERIFICAR si el problema es solo de complejidad SUPERIOR (no inferior)
            # Si está en cama de mayor complejidad y no hay alternativas, quedarse
            if nivel_cama >= nivel_paciente:
                # Verificar si hay camas del nivel correcto disponibles
                if not compatibilidad_service.hay_camas_nivel_correcto_disponibles(
                    paciente, paciente.hospital_id
                ):
                    logger.info(
                        f"Paciente {paciente.nombre}: cama de complejidad superior "
                        f"pero no hay alternativas - permanece OCUPADA"
                    )
                    paciente.requiere_nueva_cama = False
                    self.session.add(paciente)
                    return EstadoCamaEnum.OCUPADA, None
            
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
    
    def verificar_compatibilidad_cama_actual(
        self,
        paciente: 'Paciente',
        cama_actual: 'Cama'
    ) -> bool:
        """
        Verifica si la cama actual sigue siendo compatible con el paciente.
        
        Usado después de finalizar pausa de oxígeno o timers.
        
        Returns:
            True si la cama sigue siendo compatible
        """
        complejidad_paciente = self.calcular_complejidad(paciente)
        complejidad_cama = self.obtener_complejidad_cama(cama_actual)
        
        nivel_paciente = _obtener_nivel_complejidad(complejidad_paciente)
        nivel_cama = _obtener_nivel_complejidad(complejidad_cama)
        
        # Si el nivel de la cama es >= al del paciente, es compatible
        if nivel_cama >= nivel_paciente:
            return True
        
        return False