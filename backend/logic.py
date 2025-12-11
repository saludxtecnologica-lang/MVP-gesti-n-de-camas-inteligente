"""
Lógica de Asignación de Camas para el Sistema de Gestión Hospitalaria.
Contiene las reglas de negocio para asignar camas según características.

SECCIÓN CORREGIDA: Funciones de Cancelación (líneas 580-750 aprox)
- Unificación de lógica
- Corrección de bugs
- Eliminación de duplicación
"""

from typing import Optional, List, Dict, Tuple
from sqlmodel import Session, select
from datetime import datetime, timedelta
import json

from models import (
    Paciente, Cama, Sala, Servicio, Hospital,
    TipoServicioEnum, TipoEnfermedadEnum, TipoAislamientoEnum,
    ComplejidadEnum, SexoEnum, EdadCategoriaEnum, EstadoCamaEnum,
    EstadoListaEsperaEnum, ConfiguracionSistema, TipoPacienteEnum
)
from cola_prioridad import gestor_colas_global, calcular_prioridad_paciente


# ============================================
# CONSTANTES DE REQUERIMIENTOS DE OXÍGENO
# ============================================

REQUERIMIENTOS_OXIGENO = [
    "oxigeno_naricera",
    "o2_naricera",
    "oxigeno_mascarilla_multivent",
    "o2_multiventuri",
    "oxigeno_mascarilla_reservorio",
    "o2_reservorio",
    "cnaf",
    "vmni",
    "vmi"
]

# ============================================
# MAPEO TIPO ENFERMEDAD A SERVICIO
# ============================================

MAPEO_ENFERMEDAD_SERVICIO = {
    TipoEnfermedadEnum.MEDICA: [TipoServicioEnum.MEDICINA, TipoServicioEnum.MEDICO_QUIRURGICO],
    TipoEnfermedadEnum.QUIRURGICA: [TipoServicioEnum.CIRUGIA, TipoServicioEnum.MEDICO_QUIRURGICO],
    TipoEnfermedadEnum.TRAUMATOLOGICA: [TipoServicioEnum.CIRUGIA, TipoServicioEnum.MEDICO_QUIRURGICO],
    TipoEnfermedadEnum.NEUROLOGICA: [TipoServicioEnum.CIRUGIA, TipoServicioEnum.MEDICO_QUIRURGICO],
    TipoEnfermedadEnum.UROLOGICA: [TipoServicioEnum.CIRUGIA, TipoServicioEnum.MEDICO_QUIRURGICO],
    TipoEnfermedadEnum.GERIATRICA: [TipoServicioEnum.MEDICINA, TipoServicioEnum.MEDICO_QUIRURGICO],
    TipoEnfermedadEnum.GINECOLOGICA: [TipoServicioEnum.CIRUGIA, TipoServicioEnum.OBSTETRICIA, TipoServicioEnum.MEDICO_QUIRURGICO],
    TipoEnfermedadEnum.OBSTETRICA: [TipoServicioEnum.OBSTETRICIA],
}


# ============================================
# FUNCIONES DE COMPLEJIDAD
# ============================================

def calcular_complejidad(paciente: Paciente) -> ComplejidadEnum:
    """Calcula la complejidad requerida basada en los requerimientos clínicos."""
    reqs_uci = json.loads(paciente.requerimientos_uci or "[]")
    reqs_uti = json.loads(paciente.requerimientos_uti or "[]")
    reqs_baja = json.loads(paciente.requerimientos_baja or "[]")
    
    if reqs_uci and len(reqs_uci) > 0:
        return ComplejidadEnum.ALTA
    if reqs_uti and len(reqs_uti) > 0:
        return ComplejidadEnum.MEDIA
    if reqs_baja and len(reqs_baja) > 0:
        return ComplejidadEnum.BAJA
    return ComplejidadEnum.NINGUNA


def paciente_tiene_requerimientos_hospitalizacion(paciente: Paciente) -> bool:
    """Verifica si el paciente tiene requerimientos que requieren hospitalización."""
    reqs_uci = json.loads(paciente.requerimientos_uci or "[]")
    reqs_uti = json.loads(paciente.requerimientos_uti or "[]")
    reqs_baja = json.loads(paciente.requerimientos_baja or "[]")
    tiene_aislamiento_aereo = paciente.tipo_aislamiento == TipoAislamientoEnum.AEREO
    return bool(reqs_uci or reqs_uti or reqs_baja or tiene_aislamiento_aereo)


def obtener_requerimientos_oxigeno_actuales(paciente: Paciente) -> List[str]:
    """Obtiene los requerimientos de oxígeno actuales del paciente."""
    reqs_oxigeno = []
    for campo in ['requerimientos_baja', 'requerimientos_uti', 'requerimientos_uci']:
        reqs = json.loads(getattr(paciente, campo) or "[]")
        for req in reqs:
            req_lower = req.lower().replace(" ", "_")
            for oxigeno in REQUERIMIENTOS_OXIGENO:
                if oxigeno in req_lower or req_lower in oxigeno:
                    reqs_oxigeno.append(req)
                    break
    return reqs_oxigeno


def verificar_desactivacion_oxigeno(reqs_oxigeno_previos: List[str], reqs_oxigeno_actuales: List[str]) -> bool:
    """
    Verifica si se ha DESACTIVADO algún requerimiento de oxígeno.
    Retorna True solo si se desmarcó algún oxígeno (había antes y ahora no está).
    """
    if not reqs_oxigeno_previos:
        return False
    
    for req_previo in reqs_oxigeno_previos:
        if req_previo not in reqs_oxigeno_actuales:
            return True
    return False


def verificar_activacion_oxigeno(reqs_oxigeno_previos: List[str], reqs_oxigeno_actuales: List[str]) -> bool:
    """
    Verifica si se ha ACTIVADO algún requerimiento de oxígeno.
    Retorna True si se marcó un nuevo oxígeno (no estaba antes y ahora sí).
    """
    for req_actual in reqs_oxigeno_actuales:
        if req_actual not in (reqs_oxigeno_previos or []):
            return True
    return False


def paciente_en_periodo_espera_oxigeno(paciente: Paciente, tiempo_espera_segundos: int = 120) -> bool:
    """Verifica si el paciente está en periodo de espera post-desactivación de oxígeno."""
    if not paciente.oxigeno_desactivado_at:
        return False
    tiempo_transcurrido = (datetime.utcnow() - paciente.oxigeno_desactivado_at).total_seconds()
    return tiempo_transcurrido < tiempo_espera_segundos


# ============================================
# FUNCIONES DE COMPATIBILIDAD DE SERVICIO
# ============================================

def obtener_tipo_servicio_cama(cama: Cama, session: Session) -> Optional[TipoServicioEnum]:
    """Obtiene el tipo de servicio de una cama."""
    sala = session.get(Sala, cama.sala_id)
    if not sala:
        return None
    servicio = session.get(Servicio, sala.servicio_id)
    if not servicio:
        return None
    return servicio.tipo


def servicio_compatible_con_enfermedad(tipo_servicio: TipoServicioEnum, tipo_enfermedad: TipoEnfermedadEnum) -> bool:
    """CORRECCIÓN PROBLEMA 6: Verifica si un tipo de servicio es compatible con un tipo de enfermedad."""
    if tipo_servicio in [TipoServicioEnum.UCI, TipoServicioEnum.UTI]:
        return True
    if tipo_servicio == TipoServicioEnum.PEDIATRIA:
        return True
    if tipo_servicio == TipoServicioEnum.AISLAMIENTO:
        return True
    if tipo_servicio == TipoServicioEnum.MEDICO_QUIRURGICO:
        return True
    servicios_compatibles = MAPEO_ENFERMEDAD_SERVICIO.get(tipo_enfermedad, [])
    return tipo_servicio in servicios_compatibles


def verificar_cambio_tipo_enfermedad_requiere_traslado(
    paciente: Paciente, 
    cama_actual: Cama, 
    session: Session,
    tipo_enfermedad_previo: Optional[TipoEnfermedadEnum] = None
) -> Tuple[bool, str]:
    """CORRECCIÓN PROBLEMA 6: Verifica si un cambio de tipo de enfermedad requiere traslado."""
    tipo_servicio_actual = obtener_tipo_servicio_cama(cama_actual, session)
    if not tipo_servicio_actual:
        return False, ""
    
    # Servicios que no dependen del tipo de enfermedad
    if tipo_servicio_actual in [TipoServicioEnum.UCI, TipoServicioEnum.UTI, 
                                 TipoServicioEnum.AISLAMIENTO, TipoServicioEnum.PEDIATRIA,
                                 TipoServicioEnum.MEDICO_QUIRURGICO]:
        return False, ""
    
    if not servicio_compatible_con_enfermedad(tipo_servicio_actual, paciente.tipo_enfermedad):
        servicios_requeridos = MAPEO_ENFERMEDAD_SERVICIO.get(paciente.tipo_enfermedad, [])
        servicio_nombre = servicios_requeridos[0].value if servicios_requeridos else "otro servicio"
        return True, f"Cambio de tipo de enfermedad requiere cama en {servicio_nombre}"
    return False, ""


def verificar_cambio_aislamiento_requiere_traslado(
    paciente: Paciente,
    cama_actual: Cama,
    session: Session,
    tipo_aislamiento_previo: Optional[TipoAislamientoEnum] = None
) -> Tuple[bool, str]:
    """CORRECCIÓN PROBLEMA 6: Verifica si un cambio de aislamiento requiere traslado."""
    sala = session.get(Sala, cama_actual.sala_id)
    if not sala:
        return False, ""
    
    aislamientos_individuales = [
        TipoAislamientoEnum.AEREO,
        TipoAislamientoEnum.AMBIENTE_PROTEGIDO,
        TipoAislamientoEnum.ESPECIAL
    ]
    
    requiere_individual_ahora = paciente.tipo_aislamiento in aislamientos_individuales
    requeria_individual_antes = tipo_aislamiento_previo in aislamientos_individuales if tipo_aislamiento_previo else False
    
    # CASO 1: Ahora requiere individual pero está en sala compartida
    if requiere_individual_ahora and not sala.es_individual:
        return True, "Requiere aislamiento individual - sala actual es compartida"
    
    # CASO 2: Ya no requiere individual y está en sala individual
    if requeria_individual_antes and not requiere_individual_ahora and sala.es_individual:
        servicio = session.get(Servicio, sala.servicio_id)
        if servicio:
            pacientes_esperando = verificar_pacientes_aislamiento_en_espera(servicio.hospital_id, session)
            if pacientes_esperando:
                return True, "Cama individual puede ser requerida por otro paciente con aislamiento"
    
    return False, ""


def verificar_pacientes_aislamiento_en_espera(hospital_id: str, session: Session) -> bool:
    """Verifica si hay pacientes con aislamiento individual esperando cama."""
    query = select(Paciente).where(
        Paciente.hospital_id == hospital_id,
        Paciente.en_lista_espera == True,
        Paciente.tipo_aislamiento.in_([
            TipoAislamientoEnum.AEREO,
            TipoAislamientoEnum.AMBIENTE_PROTEGIDO,
            TipoAislamientoEnum.ESPECIAL
        ])
    )
    return session.exec(query).first() is not None


def verificar_pacientes_tipo_enfermedad_en_espera(
    hospital_id: str, tipo_enfermedad: TipoEnfermedadEnum, session: Session
) -> bool:
    """Verifica si hay pacientes con un tipo específico de enfermedad esperando."""
    query = select(Paciente).where(
        Paciente.hospital_id == hospital_id,
        Paciente.en_lista_espera == True,
        Paciente.tipo_enfermedad == tipo_enfermedad
    )
    return session.exec(query).first() is not None


def verificar_pacientes_quirurgicos_en_espera(hospital_id: str, session: Session) -> bool:
    """Verifica si hay pacientes quirúrgicos esperando."""
    tipos_quirurgicos = [
        TipoEnfermedadEnum.QUIRURGICA, TipoEnfermedadEnum.TRAUMATOLOGICA,
        TipoEnfermedadEnum.NEUROLOGICA, TipoEnfermedadEnum.UROLOGICA,
        TipoEnfermedadEnum.GERIATRICA, TipoEnfermedadEnum.GINECOLOGICA
    ]
    query = select(Paciente).where(
        Paciente.hospital_id == hospital_id,
        Paciente.en_lista_espera == True,
        Paciente.tipo_enfermedad.in_(tipos_quirurgicos)
    )
    return session.exec(query).first() is not None

# ============================================
# VALIDACIÓN DE COMPATIBILIDAD 
# ============================================

def cama_es_compatible(cama: Cama, paciente: Paciente, session: Session) -> Tuple[bool, str]:
    """
    Verifica si una cama es compatible con un paciente.
    Retorna (es_compatible, mensaje_razon)
    """
    sala = cama.sala
    if not sala:
        sala = session.get(Sala, cama.sala_id)
    if not sala:
        return False, "Sala no encontrada"
    
    servicio = sala.servicio if hasattr(sala, 'servicio') and sala.servicio else None
    if not servicio:
        servicio = session.get(Servicio, sala.servicio_id)
    if not servicio:
        return False, "Servicio no encontrado"
    
    tipo_servicio = servicio.tipo
    complejidad = paciente.complejidad_requerida
    es_pediatrico = paciente.edad_categoria == EdadCategoriaEnum.PEDIATRICO
    requiere_aislamiento_individual = paciente.tipo_aislamiento in [
        TipoAislamientoEnum.AEREO,
        TipoAislamientoEnum.AMBIENTE_PROTEGIDO,
        TipoAislamientoEnum.ESPECIAL
    ]
    
    # ========== REGLAS POR TIPO DE SERVICIO ==========
    
    # UCI: Solo complejidad ALTA, no pediátricos
    if tipo_servicio == TipoServicioEnum.UCI:
        if complejidad != ComplejidadEnum.ALTA:
            return False, "Cama UCI solo para pacientes con requerimientos UCI"
        if es_pediatrico:
            return False, "UCI no admite pacientes pediátricos"
        return True, "Compatible con UCI"
    
    # UTI: Solo complejidad MEDIA, no pediátricos
    if tipo_servicio == TipoServicioEnum.UTI:
        if complejidad != ComplejidadEnum.MEDIA:
            return False, "Cama UTI solo para pacientes con requerimientos UTI"
        if es_pediatrico:
            return False, "UTI no admite pacientes pediátricos"
        return True, "Compatible con UTI"
    
    # Pediatría: Solo pediátricos, solo complejidad BAJA o NINGUNA
    if tipo_servicio == TipoServicioEnum.PEDIATRIA:
        if not es_pediatrico:
            return False, "Cama pediátrica solo para pacientes pediátricos"
        if complejidad in [ComplejidadEnum.ALTA, ComplejidadEnum.MEDIA]:
            return False, "Sin disponibilidad de cama UTI/UCI pediátrica"
        if requiere_aislamiento_individual:
            return False, "Sin disponibilidad de aislamiento individual pediátrico"
        if not sala.es_individual and sala.sexo_asignado:
            if sala.sexo_asignado != paciente.sexo:
                return False, f"Sala asignada a {sala.sexo_asignado.value}s"
        return True, "Compatible con Pediatría"
    
    # Aislamiento 
    if tipo_servicio == TipoServicioEnum.AISLAMIENTO:
        if es_pediatrico:
            return False, "Aislamiento no admite pediátricos"
        if complejidad in [ComplejidadEnum.ALTA, ComplejidadEnum.MEDIA]:
            return False, "Pacientes UTI/UCI van a sus servicios específicos"
        
        # Verificar si requiere individual pero sala no lo es
        if requiere_aislamiento_individual and not sala.es_individual:
            return False, "Requiere aislamiento individual"
               
        # Si el paciente NO tiene ningún tipo de aislamiento,
        # debería estar en un servicio según su tipo de enfermedad, no en aislamiento
        if paciente.tipo_aislamiento == TipoAislamientoEnum.NINGUNO:
            return False, "Paciente sin aislamiento debe ir a servicio según tipo de enfermedad"
        
        # Si es sala individual pero el paciente no requiere aislamiento individual,
        # debería liberar la cama para quien sí la necesite
        if sala.es_individual and not requiere_aislamiento_individual:
            return False, "Cama individual de aislamiento - paciente no requiere aislamiento individual"
        
        return True, "Compatible con Aislamiento"
    
    # Obstetricia
    if tipo_servicio == TipoServicioEnum.OBSTETRICIA:
        if paciente.sexo != SexoEnum.MUJER:
            return False, "Obstetricia solo admite mujeres"
        if paciente.tipo_enfermedad != TipoEnfermedadEnum.OBSTETRICA and not paciente.es_embarazada:
            return False, "Solo para enfermedad obstétrica o embarazadas"
        if es_pediatrico:
            return False, "Obstetricia no admite pediátricos"
        if complejidad in [ComplejidadEnum.ALTA, ComplejidadEnum.MEDIA]:
            return False, "Pacientes UTI/UCI van a sus servicios específicos"
        if requiere_aislamiento_individual:
            return False, "Requiere cama de aislamiento individual"
        return True, "Compatible con Obstetricia"
    
    # Medicina
    if tipo_servicio == TipoServicioEnum.MEDICINA:
        if es_pediatrico:
            return False, "Medicina no admite pediátricos"
        if complejidad in [ComplejidadEnum.ALTA, ComplejidadEnum.MEDIA]:
            return False, "Pacientes UTI/UCI van a sus servicios específicos"
        if requiere_aislamiento_individual:
            return False, "Requiere cama de aislamiento individual"
        if paciente.tipo_enfermedad == TipoEnfermedadEnum.OBSTETRICA:
            return False, "Enfermedad obstétrica va a Obstetricia"
        # Verificar compatibilidad de tipo de enfermedad
        if not servicio_compatible_con_enfermedad(tipo_servicio, paciente.tipo_enfermedad):
            return False, f"Tipo de enfermedad {paciente.tipo_enfermedad.value} requiere servicio de Cirugía"
        if not sala.es_individual and sala.sexo_asignado:
            if sala.sexo_asignado != paciente.sexo:
                return False, f"Sala asignada a {sala.sexo_asignado.value}s"
        return True, "Compatible con Medicina"
    
    # Cirugía
    if tipo_servicio == TipoServicioEnum.CIRUGIA:
        if es_pediatrico:
            return False, "Cirugía no admite pediátricos"
        if complejidad in [ComplejidadEnum.ALTA, ComplejidadEnum.MEDIA]:
            return False, "Pacientes UTI/UCI van a sus servicios específicos"
        if requiere_aislamiento_individual:
            return False, "Requiere cama de aislamiento individual"
        if paciente.tipo_enfermedad == TipoEnfermedadEnum.OBSTETRICA:
            return False, "Enfermedad obstétrica va a Obstetricia"
        # Enfermedad médica pura NO va a cirugía
        if paciente.tipo_enfermedad == TipoEnfermedadEnum.MEDICA:
            return False, "Enfermedad médica debe ir a servicio de Medicina"
        if not sala.es_individual and sala.sexo_asignado:
            if sala.sexo_asignado != paciente.sexo:
                return False, f"Sala asignada a {sala.sexo_asignado.value}s"
        return True, "Compatible con Cirugía"
    
    # Médico-Quirúrgico
    if tipo_servicio == TipoServicioEnum.MEDICO_QUIRURGICO:
        if es_pediatrico:
            return False, "Sin disponibilidad de cama pediátrica"
        if complejidad in [ComplejidadEnum.ALTA, ComplejidadEnum.MEDIA]:
            return False, "Sin disponibilidad de cama UTI/UCI"
        if requiere_aislamiento_individual:
            return False, "Sin disponibilidad de aislamiento individual"
        if not sala.es_individual and sala.sexo_asignado:
            if sala.sexo_asignado != paciente.sexo:
                return False, f"Sala asignada a {sala.sexo_asignado.value}s"
        return True, "Compatible con Médico-Quirúrgico"
    
    return False, f"Tipo de servicio {tipo_servicio.value} no soportado"


def verificar_alta_sugerida(paciente: Paciente) -> bool:
    """Verifica si el paciente cumple criterios para alta sugerida."""
    # No tiene requerimientos que requieran hospitalización
    if not paciente_tiene_requerimientos_hospitalizacion(paciente):
        return True
    return False


def determinar_estado_cama_tras_reevaluacion(
    paciente: Paciente, 
    cama_actual: Cama, 
    session: Session,
    reqs_oxigeno_previos: List[str] = None,
    tipo_enfermedad_previo: TipoEnfermedadEnum = None,
    tipo_aislamiento_previo: TipoAislamientoEnum = None
) -> Tuple[EstadoCamaEnum, str, bool]:
    """
    Determina el estado de la cama tras una reevaluación.
    
    LÓGICA CORRECTA:
    1. Detectar si hubo desactivación de oxígeno
    2. Verificar si algún cambio requiere traslado
    3. Si requiere traslado Y hubo desactivación de oxígeno → periodo de espera
    4. Si requiere traslado pero NO hubo desactivación → cambio inmediato
    5. Si NO requiere traslado → mantener estado actual o alta sugerida
    
    Retorna:
    - Estado de cama sugerido
    - Mensaje de estado
    - Si necesita espera por desactivación de oxígeno (bool)
    """
    reqs_oxigeno_actuales = obtener_requerimientos_oxigeno_actuales(paciente)
    
    # Detectar si hubo DESACTIVACIÓN de oxígeno (no activación)
    hubo_desactivacion_oxigeno = verificar_desactivacion_oxigeno(
        reqs_oxigeno_previos or [], 
        reqs_oxigeno_actuales
    )
    
    # ========== PASO 1: Verificar cambio de tipo de enfermedad ==========
    if tipo_enfermedad_previo and tipo_enfermedad_previo != paciente.tipo_enfermedad:
        requiere_traslado, mensaje = verificar_cambio_tipo_enfermedad_requiere_traslado(
            paciente, cama_actual, session, tipo_enfermedad_previo
        )
        if requiere_traslado:
            # Solo aplicar espera si hubo desactivación de oxígeno
            if hubo_desactivacion_oxigeno:
                return EstadoCamaEnum.OCUPADA, "Evaluando desescalaje de oxígeno", True
            return EstadoCamaEnum.CAMA_EN_ESPERA, mensaje, False
    
    # ========== PASO 2: Verificar cambio de aislamiento ==========
    if tipo_aislamiento_previo and tipo_aislamiento_previo != paciente.tipo_aislamiento:
        requiere_traslado, mensaje = verificar_cambio_aislamiento_requiere_traslado(
            paciente, cama_actual, session, tipo_aislamiento_previo
        )
        if requiere_traslado:
            # Solo aplicar espera si hubo desactivación de oxígeno
            if hubo_desactivacion_oxigeno:
                return EstadoCamaEnum.OCUPADA, "Evaluando desescalaje de oxígeno", True
            return EstadoCamaEnum.CAMA_EN_ESPERA, mensaje, False
    
    # ========== PASO 3: Verificar compatibilidad completa ==========
    es_compatible, razon = cama_es_compatible(cama_actual, paciente, session)
    
    if not es_compatible:
        # La cama actual NO es compatible, necesita nueva cama
        # Solo aplicar espera si hubo desactivación de oxígeno
        if hubo_desactivacion_oxigeno:
            return EstadoCamaEnum.OCUPADA, "Evaluando desescalaje de oxígeno", True
        return EstadoCamaEnum.CAMA_EN_ESPERA, f"Paciente requiere nueva cama: {razon}", False
    
    # ========== PASO 4: La cama ES compatible ==========
    # Verificar si debería sugerir alta
    if verificar_alta_sugerida(paciente):
        # Solo aplicar espera si hubo desactivación de oxígeno
        if hubo_desactivacion_oxigeno:
            return EstadoCamaEnum.OCUPADA, "Evaluando desescalaje de oxígeno", True
        return EstadoCamaEnum.ALTA_SUGERIDA, "Alta sugerida", False
    
    # Todo bien, la cama es compatible y tiene requerimientos
    return EstadoCamaEnum.OCUPADA, None, False


def procesar_pacientes_espera_oxigeno(session: Session, tiempo_espera_segundos: int = 120) -> List[Dict]:
    """
    Procesa los pacientes que están en periodo de espera post-desactivación de oxígeno.
    """
    query = select(Paciente).where(
        Paciente.oxigeno_desactivado_at.isnot(None)
    )
    pacientes = session.exec(query).all()
    
    cambios = []
    ahora = datetime.utcnow()
    
    for paciente in pacientes:
        if not paciente.oxigeno_desactivado_at:
            continue
            
        tiempo_transcurrido = (ahora - paciente.oxigeno_desactivado_at).total_seconds()
        
        # Verificar si ya pasó el tiempo de espera
        if tiempo_transcurrido >= tiempo_espera_segundos:
            # Limpiar flags de oxígeno
            paciente.oxigeno_desactivado_at = None
            paciente.requerimientos_oxigeno_previos = None
            
            # Reevaluar paciente con su cama actual
            if paciente.cama_id:
                cama = session.get(Cama, paciente.cama_id)
                if cama:
                    # Verificar compatibilidad y determinar nuevo estado
                    es_compatible, razon = cama_es_compatible(cama, paciente, session)
                    
                    if not es_compatible:
                        cama.estado = EstadoCamaEnum.CAMA_EN_ESPERA
                        cama.mensaje_estado = f"Paciente requiere nueva cama: {razon}"
                        paciente.requiere_nueva_cama = True
                        print(f"[OXÍGENO] Cambiando a CAMA_EN_ESPERA")
                    elif verificar_alta_sugerida(paciente):
                        cama.estado = EstadoCamaEnum.ALTA_SUGERIDA
                        cama.mensaje_estado = "Alta sugerida"
                        print(f"[OXÍGENO] Cambiando a ALTA_SUGERIDA")
                    else:
                        cama.estado = EstadoCamaEnum.OCUPADA
                        cama.mensaje_estado = None
                        print(f"[OXÍGENO] Manteniendo OCUPADA")
                    
                    session.add(cama)
                    cambios.append({
                        "paciente_id": paciente.id,
                        "paciente_nombre": paciente.nombre,
                        "cama_id": cama.id,
                        "cama_identificador": cama.identificador,
                        "nuevo_estado": cama.estado.value,
                        "requiere_nueva_cama": paciente.requiere_nueva_cama
                    })
            
            session.add(paciente)
    
    if cambios:
        session.commit()
        print(f"[OXÍGENO] {len(cambios)} cambios realizados")
    
    return cambios


# ============================================
# CANCELACIÓN DE TRASLADOS/DERIVACIONES
# SECCIÓN CORREGIDA Y UNIFICADA
# ============================================

def cancelar_asignacion(paciente_id: str, session: Session, contexto: str = "auto") -> Dict:
    """
    FUNCIÓN PRINCIPAL DE CANCELACIÓN - UNIFICADA
    
    Cancela la asignación de cama de un paciente.
    Determina automáticamente el flujo correcto según el estado.
    
    Args:
        paciente_id: ID del paciente
        session: Sesión de base de datos
        contexto: Contexto de la cancelación ("auto", "desde_origen", "desde_destino", "desde_lista")
    
    Flujos:
        1. Desde cama origen (TRASLADO_SALIENTE/CONFIRMADO): 
           → Cama a CAMA_EN_ESPERA, paciente sale de lista
        2. Desde cama destino (TRASLADO_ENTRANTE): 
           → Cama libre, paciente vuelve a lista
        3. Derivación desde destino: 
           → Paciente vuelve a lista derivación, cama origen a ESPERA_DERIVACION
        4. Derivación desde origen: 
           → Cama a OCUPADA, derivación cancelada
        5. Paciente nuevo: 
           → Eliminar del sistema
    """
    paciente = session.get(Paciente, paciente_id)
    if not paciente:
        return {"error": "Paciente no encontrado"}
    
    # Obtener información de camas
    cama_destino = session.get(Cama, paciente.cama_destino_id) if paciente.cama_destino_id else None
    cama_origen = session.get(Cama, paciente.cama_id) if paciente.cama_id else None
    cama_origen_derivacion = session.get(Cama, paciente.cama_origen_derivacion_id) if paciente.cama_origen_derivacion_id else None
    
    resultado = {"success": True, "paciente_id": paciente.id, "accion": ""}
    
    # Determinar el tipo de paciente
    es_derivado = paciente.derivacion_estado == "aceptado"
    es_paciente_nuevo = not paciente.cama_id and not cama_origen_derivacion and paciente.tipo_paciente in [TipoPacienteEnum.URGENCIA, TipoPacienteEnum.AMBULATORIO]
    es_hospitalizado = paciente.cama_id is not None and not es_derivado
    
    print(f"[CANCELAR] Paciente: {paciente.nombre}, es_derivado={es_derivado}, es_nuevo={es_paciente_nuevo}, es_hospitalizado={es_hospitalizado}")
    print(f"[CANCELAR] cama_origen={cama_origen}, cama_destino={cama_destino}, cama_origen_derivacion={cama_origen_derivacion}")
    
    # ========== CASO 1: Cancelación desde cama TRASLADO_SALIENTE o TRASLADO_CONFIRMADO ==========
    # Paciente hospitalizado que está buscando nueva cama
    if cama_origen and cama_origen.estado in [EstadoCamaEnum.TRASLADO_SALIENTE, EstadoCamaEnum.TRASLADO_CONFIRMADO]:
        print(f"[CANCELAR] CASO 1: Desde cama origen TRASLADO_SALIENTE/CONFIRMADO")
        
        # Liberar cama destino si existe
        if cama_destino:
            cama_destino.estado = EstadoCamaEnum.LIBRE
            cama_destino.mensaje_estado = None
            session.add(cama_destino)
            print(f"[CANCELAR] Cama destino {cama_destino.identificador} liberada")
        
        # Volver cama origen a CAMA_EN_ESPERA
        cama_origen.estado = EstadoCamaEnum.CAMA_EN_ESPERA
        cama_origen.cama_asignada_destino = None
        cama_origen.mensaje_estado = "Listo para buscar nueva cama"
        session.add(cama_origen)
        print(f"[CANCELAR] Cama origen {cama_origen.identificador} -> CAMA_EN_ESPERA")
        
        # Actualizar paciente: SACAR de lista de espera
        paciente.cama_destino_id = None
        paciente.requiere_nueva_cama = True
        paciente.en_lista_espera = False
        paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
        
        # Remover de cola
        gestor_colas_global.remover_paciente(paciente.id, paciente.hospital_id, session, paciente)
        print(f"[CANCELAR] Paciente removido de cola")
        
        session.add(paciente)
        session.commit()
        
        resultado["accion"] = "paciente_vuelve_a_cama_origen"
        return resultado
    
    # ========== CASO 2: Cancelación desde cama TRASLADO_ENTRANTE (destino) ==========
    if cama_destino and cama_destino.estado == EstadoCamaEnum.TRASLADO_ENTRANTE:
        print(f"[CANCELAR] CASO 2: Desde cama destino TRASLADO_ENTRANTE")
        
        # Liberar la cama destino
        cama_destino.estado = EstadoCamaEnum.LIBRE
        cama_destino.mensaje_estado = None
        session.add(cama_destino)
        print(f"[CANCELAR] Cama destino {cama_destino.identificador} liberada")
        
        # ========== CASO 2a: Si es derivado, volver a lista de derivación ==========
        if es_derivado and cama_origen_derivacion:
            print(f"[CANCELAR] CASO 2a: Derivado vuelve a lista de derivación")
            
            # Actualizar cama de origen de derivación a ESPERA_DERIVACION
            cama_origen_derivacion.estado = EstadoCamaEnum.ESPERA_DERIVACION
            cama_origen_derivacion.cama_asignada_destino = None
            cama_origen_derivacion.mensaje_estado = "Derivación pendiente"
            session.add(cama_origen_derivacion)
            print(f"[CANCELAR] Cama origen derivación {cama_origen_derivacion.identificador} -> ESPERA_DERIVACION")
            
            # Paciente vuelve a estado pendiente de derivación
            paciente.cama_destino_id = None
            paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
            paciente.derivacion_estado = "pendiente"
            paciente.en_lista_espera = False
            
            # Remover de cola del hospital destino
            gestor_colas_global.remover_paciente(paciente.id, paciente.hospital_id, session, paciente)
            
            # Restaurar hospital original
            if cama_origen_derivacion.sala:
                servicio = session.get(Servicio, cama_origen_derivacion.sala.servicio_id)
                if servicio:
                    paciente.hospital_id = servicio.hospital_id
                    print(f"[CANCELAR] Hospital restaurado a {servicio.hospital_id}")
            
            session.add(paciente)
            session.commit()
            
            resultado["accion"] = "derivado_vuelve_a_lista_derivacion"
            return resultado
        
        # ========== CASO 2b: Paciente normal vuelve a lista de espera ==========
        paciente.cama_destino_id = None
        paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
        
        # Si tenía cama origen, actualizar su estado
        if cama_origen and cama_origen.estado == EstadoCamaEnum.TRASLADO_CONFIRMADO:
            cama_origen.estado = EstadoCamaEnum.TRASLADO_SALIENTE
            cama_origen.cama_asignada_destino = None
            cama_origen.mensaje_estado = "Buscando nueva cama"
            session.add(cama_origen)
            print(f"[CANCELAR] Cama origen {cama_origen.identificador} -> TRASLADO_SALIENTE")
        
        session.add(paciente)
        session.commit()
        resultado["accion"] = "paciente_vuelve_a_lista_espera"
        return resultado
    
    # ========== CASO 3: Cancelación de derivación desde cama origen ==========
    if cama_origen and cama_origen.estado in [EstadoCamaEnum.DERIVACION_CONFIRMADA, EstadoCamaEnum.ESPERA_DERIVACION]:
        print(f"[CANCELAR] CASO 3: Derivación desde cama origen")
        
        # Cama origen vuelve a OCUPADA
        cama_origen.estado = EstadoCamaEnum.OCUPADA
        cama_origen.cama_asignada_destino = None
        cama_origen.mensaje_estado = None
        cama_origen.paciente_derivado_id = None
        session.add(cama_origen)
        print(f"[CANCELAR] Cama origen {cama_origen.identificador} -> OCUPADA")
        
        # Liberar cama destino si existe
        if cama_destino:
            cama_destino.estado = EstadoCamaEnum.LIBRE
            cama_destino.mensaje_estado = None
            session.add(cama_destino)
        
        # Cancelar derivación del paciente
        hospital_destino_id = paciente.derivacion_hospital_destino_id
        paciente.derivacion_estado = "cancelado"
        paciente.en_lista_espera = False
        paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
        paciente.cama_destino_id = None
        paciente.cama_origen_derivacion_id = None
        
        # Remover de cola del hospital destino si estaba
        if hospital_destino_id:
            gestor_colas_global.remover_paciente(paciente.id, hospital_destino_id, session, paciente)
        
        session.add(paciente)
        session.commit()
        
        resultado["accion"] = "derivacion_cancelada_desde_origen"
        return resultado
    
    # ========== CASO 4: Paciente nuevo (sin cama) - Eliminar del sistema ==========
    if es_paciente_nuevo:
        print(f"[CANCELAR] CASO 4: Paciente nuevo - eliminar")
        
        # Liberar cama destino si existe
        if cama_destino:
            cama_destino.estado = EstadoCamaEnum.LIBRE
            cama_destino.mensaje_estado = None
            session.add(cama_destino)
        
        # Remover de cola
        gestor_colas_global.remover_paciente(paciente.id, paciente.hospital_id, session, paciente)
        
        # Eliminar paciente del sistema
        session.delete(paciente)
        session.commit()
        
        resultado["accion"] = "paciente_nuevo_eliminado"
        return resultado
    
    # ========== CASO 5: Derivado en lista de espera (sin cama destino asignada aún) ==========
    if es_derivado and paciente.en_lista_espera and cama_origen_derivacion:
        print(f"[CANCELAR] CASO 5: Derivado en lista de espera")
        
        # Actualizar cama de origen de derivación
        cama_origen_derivacion.estado = EstadoCamaEnum.ESPERA_DERIVACION
        cama_origen_derivacion.cama_asignada_destino = None
        cama_origen_derivacion.mensaje_estado = "Derivación pendiente"
        session.add(cama_origen_derivacion)
        
        # Paciente vuelve a estado pendiente de derivación
        paciente.derivacion_estado = "pendiente"
        paciente.en_lista_espera = False
        paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
        
        # Remover de cola del hospital destino
        gestor_colas_global.remover_paciente(paciente.id, paciente.hospital_id, session, paciente)
        
        # Restaurar hospital original
        if cama_origen_derivacion.sala:
            sala = session.get(Sala, cama_origen_derivacion.sala_id)
            if sala:
                servicio = session.get(Servicio, sala.servicio_id)
                if servicio:
                    paciente.hospital_id = servicio.hospital_id
        
        session.add(paciente)
        session.commit()
        
        resultado["accion"] = "derivado_vuelve_a_lista_derivacion"
        return resultado
    
    # ========== CASO por defecto ==========
    print(f"[CANCELAR] CASO default")
    if cama_destino:
        cama_destino.estado = EstadoCamaEnum.LIBRE
        cama_destino.mensaje_estado = None
        session.add(cama_destino)
    
    paciente.cama_destino_id = None
    paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
    session.add(paciente)
    session.commit()
    
    resultado["accion"] = "cancelacion_basica"
    return resultado


def actualizar_sexo_sala_si_vacia(sala_id: str, session: Session):
    """Actualiza el sexo de la sala si queda vacía."""
    sala = session.get(Sala, sala_id)
    if not sala or sala.es_individual:
        return
    
    query = select(Cama).where(
        Cama.sala_id == sala_id,
        Cama.estado.in_([
            EstadoCamaEnum.OCUPADA,
            EstadoCamaEnum.TRASLADO_SALIENTE,
            EstadoCamaEnum.TRASLADO_CONFIRMADO,
            EstadoCamaEnum.CAMA_EN_ESPERA,
            EstadoCamaEnum.ALTA_SUGERIDA,
            EstadoCamaEnum.CAMA_ALTA,
            EstadoCamaEnum.ESPERA_DERIVACION,
            EstadoCamaEnum.DERIVACION_CONFIRMADA
        ])
    )
    camas_ocupadas = session.exec(query).all()
    
    if not camas_ocupadas:
        sala.sexo_asignado = None
        session.add(sala)


# ============================================
# BÚSQUEDA DE CAMAS
# ============================================

def buscar_cama_compatible(paciente: Paciente, session: Session) -> Optional[Cama]:
    """Busca una cama compatible para el paciente."""
    hospital = session.get(Hospital, paciente.hospital_id)
    if not hospital:
        return None
    
    query = select(Servicio).where(Servicio.hospital_id == hospital.id)
    servicios = session.exec(query).all()
    servicios_ordenados = ordenar_servicios_por_prioridad(servicios, paciente)
    
    for servicio in servicios_ordenados:
        query_salas = select(Sala).where(Sala.servicio_id == servicio.id)
        salas = session.exec(query_salas).all()
        
        for sala in salas:
            query_camas = select(Cama).where(
                Cama.sala_id == sala.id,
                Cama.estado == EstadoCamaEnum.LIBRE
            )
            camas = session.exec(query_camas).all()
            
            for cama in camas:
                es_compatible, _ = cama_es_compatible(cama, paciente, session)
                if es_compatible:
                    return cama
    return None


def ordenar_servicios_por_prioridad(servicios: List[Servicio], paciente: Paciente) -> List[Servicio]:
    """Ordena los servicios por prioridad según las características del paciente."""
    complejidad = paciente.complejidad_requerida
    es_pediatrico = paciente.edad_categoria == EdadCategoriaEnum.PEDIATRICO
    tipo_enfermedad = paciente.tipo_enfermedad
    requiere_aislamiento = paciente.tipo_aislamiento in [
        TipoAislamientoEnum.AEREO, TipoAislamientoEnum.AMBIENTE_PROTEGIDO, TipoAislamientoEnum.ESPECIAL
    ]
    
    def prioridad_servicio(servicio: Servicio) -> int:
        tipo = servicio.tipo
        if complejidad == ComplejidadEnum.ALTA:
            return 0 if tipo == TipoServicioEnum.UCI else 100
        if complejidad == ComplejidadEnum.MEDIA:
            return 0 if tipo == TipoServicioEnum.UTI else 100
        if es_pediatrico:
            return 0 if tipo == TipoServicioEnum.PEDIATRIA else 100
        if requiere_aislamiento:
            prioridades = {TipoServicioEnum.AISLAMIENTO: 0, TipoServicioEnum.UCI: 1, TipoServicioEnum.UTI: 2}
            return prioridades.get(tipo, 100)
        if tipo_enfermedad == TipoEnfermedadEnum.OBSTETRICA or paciente.es_embarazada:
            return 0 if tipo == TipoServicioEnum.OBSTETRICIA else 100
        if tipo_enfermedad == TipoEnfermedadEnum.MEDICA:
            prioridades = {TipoServicioEnum.MEDICINA: 0, TipoServicioEnum.MEDICO_QUIRURGICO: 1}
            return prioridades.get(tipo, 100)
        if tipo_enfermedad in [TipoEnfermedadEnum.QUIRURGICA, TipoEnfermedadEnum.TRAUMATOLOGICA,
                               TipoEnfermedadEnum.NEUROLOGICA, TipoEnfermedadEnum.UROLOGICA]:
            prioridades = {TipoServicioEnum.CIRUGIA: 0, TipoServicioEnum.MEDICO_QUIRURGICO: 1}
            return prioridades.get(tipo, 100)
        return 50
    
    return sorted(servicios, key=prioridad_servicio)


# ============================================
# ASIGNACIÓN AUTOMÁTICA
# ============================================

def ejecutar_asignacion_automatica(hospital_id: str, session: Session) -> List[Dict]:
    """Ejecuta el proceso de asignación automática para un hospital."""
    config = session.exec(select(ConfiguracionSistema)).first()
    if config and config.modo_manual:
        return []
    
    asignaciones = []
    cola = gestor_colas_global.obtener_cola(hospital_id)
    lista_pacientes = cola.obtener_lista_ordenada(session)
    
    for info_paciente in lista_pacientes:
        paciente = session.get(Paciente, info_paciente["paciente_id"])
        if not paciente or paciente.estado_lista_espera == EstadoListaEsperaEnum.ASIGNADO:
            continue
        
        # Verificar periodo de espera de oxígeno - NO asignar durante este periodo
        if paciente.oxigeno_desactivado_at:
            tiempo_espera = config.tiempo_espera_oxigeno_segundos if config else 120
            if paciente_en_periodo_espera_oxigeno(paciente, tiempo_espera):
                # Paciente aún en periodo de espera, saltar
                continue
            # Tiempo cumplido, limpiar flags (será procesado por procesar_pacientes_espera_oxigeno)
            continue
        
        paciente.estado_lista_espera = EstadoListaEsperaEnum.BUSCANDO
        session.add(paciente)
        session.commit()
        
        cama = buscar_cama_compatible(paciente, session)
        if cama:
            asignacion = asignar_cama_a_paciente(paciente, cama, session)
            if asignacion:
                asignaciones.append(asignacion)
        else:
            paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
            session.add(paciente)
            session.commit()
    
    return asignaciones


def asignar_cama_a_paciente(paciente: Paciente, cama: Cama, session: Session) -> Optional[Dict]:
    """Asigna una cama a un paciente."""
    paciente.cama_destino_id = cama.id
    paciente.estado_lista_espera = EstadoListaEsperaEnum.ASIGNADO
    session.add(paciente)
    
    cama.estado = EstadoCamaEnum.TRASLADO_ENTRANTE
    cama.estado_updated_at = datetime.utcnow()
    cama.mensaje_estado = f"Asignado a {paciente.nombre}"
    session.add(cama)
    
    if paciente.cama_id:
        cama_origen = session.get(Cama, paciente.cama_id)
        if cama_origen:
            cama_origen.estado = EstadoCamaEnum.TRASLADO_CONFIRMADO
            cama_origen.cama_asignada_destino = cama.identificador
            cama_origen.mensaje_estado = f"Cama asignada: {cama.identificador}"
            session.add(cama_origen)
    
    if paciente.derivacion_estado == "aceptado" and paciente.cama_origen_derivacion_id:
        cama_origen_derivacion = session.get(Cama, paciente.cama_origen_derivacion_id)
        if cama_origen_derivacion:
            cama_origen_derivacion.estado = EstadoCamaEnum.DERIVACION_CONFIRMADA
            cama_origen_derivacion.cama_asignada_destino = cama.identificador
            session.add(cama_origen_derivacion)
    
    sala = cama.sala if cama.sala else session.get(Sala, cama.sala_id)
    if sala and not sala.es_individual and not sala.sexo_asignado:
        sala.sexo_asignado = paciente.sexo
        session.add(sala)
    
    session.commit()
    return {
        "paciente_id": paciente.id,
        "paciente_nombre": paciente.nombre,
        "cama_id": cama.id,
        "cama_identificador": cama.identificador,
        "timestamp": datetime.utcnow().isoformat()
    }


def completar_traslado(paciente_id: str, session: Session) -> Dict:
    """Completa el traslado de un paciente a su cama asignada."""
    paciente = session.get(Paciente, paciente_id)
    if not paciente:
        return {"error": "Paciente no encontrado"}
    if not paciente.cama_destino_id:
        return {"error": "Paciente no tiene cama destino asignada"}
    
    cama_destino = session.get(Cama, paciente.cama_destino_id)
    if not cama_destino:
        return {"error": "Cama destino no encontrada"}
    
    cama_origen_id = paciente.cama_id
    
    if cama_origen_id:
        cama_origen = session.get(Cama, cama_origen_id)
        if cama_origen:
            cama_origen.estado = EstadoCamaEnum.EN_LIMPIEZA
            cama_origen.limpieza_inicio = datetime.utcnow()
            cama_origen.mensaje_estado = "En limpieza"
            cama_origen.cama_asignada_destino = None
            cama_origen.paciente_derivado_id = None
            session.add(cama_origen)
            actualizar_sexo_sala_si_vacia(cama_origen.sala_id, session)
    
    if paciente.cama_origen_derivacion_id:
        cama_derivacion = session.get(Cama, paciente.cama_origen_derivacion_id)
        if cama_derivacion and cama_derivacion.estado == EstadoCamaEnum.DERIVACION_CONFIRMADA:
            cama_derivacion.estado = EstadoCamaEnum.EN_LIMPIEZA
            cama_derivacion.limpieza_inicio = datetime.utcnow()
            cama_derivacion.paciente_derivado_id = None
            session.add(cama_derivacion)
            actualizar_sexo_sala_si_vacia(cama_derivacion.sala_id, session)
        paciente.cama_origen_derivacion_id = None
    
    cama_destino.estado = EstadoCamaEnum.OCUPADA
    cama_destino.mensaje_estado = None
    session.add(cama_destino)
    
    paciente.cama_id = paciente.cama_destino_id
    paciente.cama_destino_id = None
    paciente.en_lista_espera = False
    paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
    paciente.requiere_nueva_cama = False
    session.add(paciente)
    
    gestor_colas_global.remover_paciente(paciente.id, paciente.hospital_id, session, paciente)
    session.commit()
    
    return {"success": True, "paciente_id": paciente.id, "cama_nueva_id": paciente.cama_id}


# ============================================
# FUNCIONES DE ALTA
# ============================================

def iniciar_alta(paciente_id: str, session: Session) -> Dict:
    """Inicia el proceso de alta de un paciente."""
    paciente = session.get(Paciente, paciente_id)
    if not paciente:
        return {"error": "Paciente no encontrado"}
    if not paciente.cama_id:
        return {"error": "Paciente no tiene cama asignada"}
    
    cama = session.get(Cama, paciente.cama_id)
    if cama:
        cama.estado = EstadoCamaEnum.CAMA_ALTA
        cama.mensaje_estado = "Alta pendiente"
        session.add(cama)
    
    paciente.alta_solicitada = True
    session.add(paciente)
    session.commit()
    return {"success": True, "paciente_id": paciente.id}


def ejecutar_alta(paciente_id: str, session: Session) -> Dict:
    """Ejecuta el alta definitiva de un paciente."""
    paciente = session.get(Paciente, paciente_id)
    if not paciente:
        return {"error": "Paciente no encontrado"}
    
    cama_id = paciente.cama_id
    if cama_id:
        cama = session.get(Cama, cama_id)
        if cama:
            cama.estado = EstadoCamaEnum.EN_LIMPIEZA
            cama.limpieza_inicio = datetime.utcnow()
            cama.mensaje_estado = "En limpieza"
            session.add(cama)
            actualizar_sexo_sala_si_vacia(cama.sala_id, session)
    
    if paciente.en_lista_espera:
        gestor_colas_global.remover_paciente(paciente.id, paciente.hospital_id, session, paciente)
    
    session.delete(paciente)
    session.commit()
    return {"success": True, "paciente_id": paciente_id, "cama_liberada": cama_id}


def cancelar_alta(paciente_id: str, session: Session) -> Dict:
    """Cancela el proceso de alta."""
    paciente = session.get(Paciente, paciente_id)
    if not paciente:
        return {"error": "Paciente no encontrado"}
    
    if paciente.cama_id:
        cama = session.get(Cama, paciente.cama_id)
        if cama:
            cama.estado = EstadoCamaEnum.ALTA_SUGERIDA
            cama.mensaje_estado = "Alta sugerida"
            session.add(cama)
    
    paciente.alta_solicitada = False
    session.add(paciente)
    session.commit()
    return {"success": True, "paciente_id": paciente.id}


def procesar_camas_en_limpieza(session: Session, tiempo_limpieza_segundos: int = 60) -> List[str]:
    """Procesa las camas en limpieza y las libera después del tiempo configurado."""
    query = select(Cama).where(Cama.estado == EstadoCamaEnum.EN_LIMPIEZA)
    camas_limpieza = session.exec(query).all()
    
    ahora = datetime.utcnow()
    camas_liberadas = []
    
    for cama in camas_limpieza:
        if cama.limpieza_inicio:
            tiempo = (ahora - cama.limpieza_inicio).total_seconds()
            if tiempo >= tiempo_limpieza_segundos:
                cama.estado = EstadoCamaEnum.LIBRE
                cama.limpieza_inicio = None
                cama.mensaje_estado = None
                session.add(cama)
                camas_liberadas.append(cama.identificador)
    
    if camas_liberadas:
        session.commit()
    return camas_liberadas