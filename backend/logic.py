"""
Lógica de Asignación de Camas para el Sistema de Gestión Hospitalaria.
Contiene las reglas de negocio para asignar camas según características.
"""

from typing import Optional, List, Dict, Tuple
from sqlmodel import Session, select
from datetime import datetime
import json

from models import (
    Paciente, Cama, Sala, Servicio, Hospital,
    TipoServicioEnum, TipoEnfermedadEnum, TipoAislamientoEnum,
    ComplejidadEnum, SexoEnum, EdadCategoriaEnum, EstadoCamaEnum,
    EstadoListaEsperaEnum, ConfiguracionSistema
)
from cola_prioridad import gestor_colas_global, calcular_prioridad_paciente


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


# ============================================
# VALIDACIÓN DE COMPATIBILIDAD
# ============================================

def cama_es_compatible(cama: Cama, paciente: Paciente, session: Session) -> Tuple[bool, str]:
    """
    Verifica si una cama es compatible con un paciente.
    Retorna (es_compatible, mensaje_razon)
    """
    sala = cama.sala
    servicio = sala.servicio
    tipo_servicio = servicio.tipo
    
    # Verificar estado de la cama
    if cama.estado != EstadoCamaEnum.LIBRE:
        return False, "Cama no disponible"
    
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
            return False, "Sin disponibilidad de cama UTI/UCI pediátrica en este hospital"
        if requiere_aislamiento_individual:
            return False, "Sin disponibilidad de aislamiento individual pediátrico"
        # Verificar sexo de sala compartida
        if not sala.es_individual and sala.sexo_asignado:
            if sala.sexo_asignado != paciente.sexo:
                return False, f"Sala asignada a {sala.sexo_asignado.value}s"
        return True, "Compatible con Pediatría"
    
    # Aislamiento: Prioridad a aislamientos individuales
    if tipo_servicio == TipoServicioEnum.AISLAMIENTO:
        if es_pediatrico:
            return False, "Aislamiento no admite pediátricos"
        if complejidad in [ComplejidadEnum.ALTA, ComplejidadEnum.MEDIA]:
            return False, "Pacientes UTI/UCI van a sus servicios específicos"
        # Verificar si hay pacientes con aislamiento individual en espera
        if not requiere_aislamiento_individual:
            pacientes_aislamiento_esperando = verificar_pacientes_aislamiento_en_espera(
                paciente.hospital_id, session
            )
            if pacientes_aislamiento_esperando:
                return False, "Cama reservada para pacientes con aislamiento individual"
        return True, "Compatible con Aislamiento"
    
    # Obstetricia: Solo mujeres con enfermedad obstétrica o embarazadas
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
    
    # Medicina: Prioridad a enfermedad médica
    if tipo_servicio == TipoServicioEnum.MEDICINA:
        if es_pediatrico:
            return False, "Medicina no admite pediátricos"
        if complejidad in [ComplejidadEnum.ALTA, ComplejidadEnum.MEDIA]:
            return False, "Pacientes UTI/UCI van a sus servicios específicos"
        if requiere_aislamiento_individual:
            return False, "Requiere cama de aislamiento individual"
        if paciente.tipo_enfermedad == TipoEnfermedadEnum.OBSTETRICA:
            return False, "Enfermedad obstétrica va a Obstetricia"
        # Verificar prioridad de enfermedad médica
        if paciente.tipo_enfermedad != TipoEnfermedadEnum.MEDICA:
            pacientes_medicos_esperando = verificar_pacientes_tipo_enfermedad_en_espera(
                paciente.hospital_id, TipoEnfermedadEnum.MEDICA, session
            )
            if pacientes_medicos_esperando:
                return False, "Cama reservada para pacientes con enfermedad médica"
        # Verificar sexo de sala compartida
        if not sala.es_individual and sala.sexo_asignado:
            if sala.sexo_asignado != paciente.sexo:
                return False, f"Sala asignada a {sala.sexo_asignado.value}s"
        return True, "Compatible con Medicina"
    
    # Cirugía: Prioridad a no-médicas
    if tipo_servicio == TipoServicioEnum.CIRUGIA:
        if es_pediatrico:
            return False, "Cirugía no admite pediátricos"
        if complejidad in [ComplejidadEnum.ALTA, ComplejidadEnum.MEDIA]:
            return False, "Pacientes UTI/UCI van a sus servicios específicos"
        if requiere_aislamiento_individual:
            return False, "Requiere cama de aislamiento individual"
        if paciente.tipo_enfermedad == TipoEnfermedadEnum.OBSTETRICA:
            return False, "Enfermedad obstétrica va a Obstetricia"
        # Verificar si hay pacientes quirúrgicos esperando
        if paciente.tipo_enfermedad == TipoEnfermedadEnum.MEDICA:
            pacientes_quirurgicos_esperando = verificar_pacientes_quirurgicos_en_espera(
                paciente.hospital_id, session
            )
            if pacientes_quirurgicos_esperando:
                return False, "Cama reservada para pacientes quirúrgicos"
        # Verificar sexo de sala compartida
        if not sala.es_individual and sala.sexo_asignado:
            if sala.sexo_asignado != paciente.sexo:
                return False, f"Sala asignada a {sala.sexo_asignado.value}s"
        return True, "Compatible con Cirugía"
    
    # Médico-Quirúrgico: Acepta todo excepto obstétricas y pediátricos
    if tipo_servicio == TipoServicioEnum.MEDICO_QUIRURGICO:
        if es_pediatrico:
            return False, "Sin disponibilidad de cama pediátrica en este hospital"
        if complejidad in [ComplejidadEnum.ALTA, ComplejidadEnum.MEDIA]:
            return False, "Sin disponibilidad de cama UTI/UCI en este hospital"
        if requiere_aislamiento_individual:
            return False, "Sin disponibilidad de aislamiento individual en este hospital"
        # Verificar sexo de sala compartida
        if not sala.es_individual and sala.sexo_asignado:
            if sala.sexo_asignado != paciente.sexo:
                return False, f"Sala asignada a {sala.sexo_asignado.value}s"
        return True, "Compatible con Médico-Quirúrgico"
    
    return False, "Servicio no reconocido"


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
    hospital_id: str, 
    tipo_enfermedad: TipoEnfermedadEnum, 
    session: Session
) -> bool:
    """Verifica si hay pacientes con un tipo específico de enfermedad esperando."""
    query = select(Paciente).where(
        Paciente.hospital_id == hospital_id,
        Paciente.en_lista_espera == True,
        Paciente.tipo_enfermedad == tipo_enfermedad
    )
    return session.exec(query).first() is not None


def verificar_pacientes_quirurgicos_en_espera(hospital_id: str, session: Session) -> bool:
    """Verifica si hay pacientes quirúrgicos (no médicos) esperando."""
    tipos_quirurgicos = [
        TipoEnfermedadEnum.QUIRURGICA,
        TipoEnfermedadEnum.TRAUMATOLOGICA,
        TipoEnfermedadEnum.NEUROLOGICA,
        TipoEnfermedadEnum.UROLOGICA,
        TipoEnfermedadEnum.GERIATRICA,
        TipoEnfermedadEnum.GINECOLOGICA
    ]
    query = select(Paciente).where(
        Paciente.hospital_id == hospital_id,
        Paciente.en_lista_espera == True,
        Paciente.tipo_enfermedad.in_(tipos_quirurgicos)
    )
    return session.exec(query).first() is not None


# ============================================
# BÚSQUEDA DE CAMAS
# ============================================

def buscar_cama_compatible(paciente: Paciente, session: Session) -> Optional[Cama]:
    """
    Busca una cama compatible para el paciente.
    Retorna la mejor cama disponible o None.
    """
    hospital = session.get(Hospital, paciente.hospital_id)
    if not hospital:
        return None
    
    # Obtener todos los servicios del hospital
    query = select(Servicio).where(Servicio.hospital_id == hospital.id)
    servicios = session.exec(query).all()
    
    # Ordenar servicios por prioridad según complejidad
    complejidad = paciente.complejidad_requerida
    servicios_ordenados = ordenar_servicios_por_prioridad(servicios, paciente)
    
    for servicio in servicios_ordenados:
        # Obtener salas del servicio
        query_salas = select(Sala).where(Sala.servicio_id == servicio.id)
        salas = session.exec(query_salas).all()
        
        for sala in salas:
            # Obtener camas de la sala
            query_camas = select(Cama).where(
                Cama.sala_id == sala.id,
                Cama.estado == EstadoCamaEnum.LIBRE
            )
            camas = session.exec(query_camas).all()
            
            for cama in camas:
                es_compatible, razon = cama_es_compatible(cama, paciente, session)
                if es_compatible:
                    return cama
    
    return None


def ordenar_servicios_por_prioridad(servicios: List[Servicio], paciente: Paciente) -> List[Servicio]:
    """Ordena los servicios por prioridad según las características del paciente."""
    complejidad = paciente.complejidad_requerida
    es_pediatrico = paciente.edad_categoria == EdadCategoriaEnum.PEDIATRICO
    tipo_enfermedad = paciente.tipo_enfermedad
    requiere_aislamiento_individual = paciente.tipo_aislamiento in [
        TipoAislamientoEnum.AEREO,
        TipoAislamientoEnum.AMBIENTE_PROTEGIDO,
        TipoAislamientoEnum.ESPECIAL
    ]
    
    def prioridad_servicio(servicio: Servicio) -> int:
        tipo = servicio.tipo
        
        # UCI para complejidad alta
        if complejidad == ComplejidadEnum.ALTA:
            if tipo == TipoServicioEnum.UCI:
                return 0
            return 100
        
        # UTI para complejidad media
        if complejidad == ComplejidadEnum.MEDIA:
            if tipo == TipoServicioEnum.UTI:
                return 0
            return 100
        
        # Pediátricos
        if es_pediatrico:
            if tipo == TipoServicioEnum.PEDIATRIA:
                return 0
            return 100
        
        # Aislamiento individual
        if requiere_aislamiento_individual:
            if tipo == TipoServicioEnum.AISLAMIENTO:
                return 0
            if tipo == TipoServicioEnum.UCI:
                return 1
            if tipo == TipoServicioEnum.UTI:
                return 2
            return 100
        
        # Obstetricia
        if tipo_enfermedad == TipoEnfermedadEnum.OBSTETRICA or (
            paciente.es_embarazada and paciente.sexo == SexoEnum.MUJER
        ):
            if tipo == TipoServicioEnum.OBSTETRICIA:
                return 0
            return 100
        
        # Enfermedad médica
        if tipo_enfermedad == TipoEnfermedadEnum.MEDICA:
            prioridades = {
                TipoServicioEnum.MEDICINA: 0,
                TipoServicioEnum.MEDICO_QUIRURGICO: 1,
                TipoServicioEnum.CIRUGIA: 2,
                TipoServicioEnum.AISLAMIENTO: 3
            }
            return prioridades.get(tipo, 100)
        
        # Otras enfermedades (quirúrgicas, etc.)
        prioridades = {
            TipoServicioEnum.CIRUGIA: 0,
            TipoServicioEnum.MEDICO_QUIRURGICO: 1,
            TipoServicioEnum.MEDICINA: 2,
            TipoServicioEnum.AISLAMIENTO: 3
        }
        return prioridades.get(tipo, 100)
    
    return sorted(servicios, key=prioridad_servicio)


# ============================================
# ASIGNACIÓN AUTOMÁTICA
# ============================================

def ejecutar_asignacion_automatica(hospital_id: str, session: Session) -> List[Dict]:
    """
    Ejecuta el proceso de asignación automática para un hospital.
    Retorna lista de asignaciones realizadas.
    """
    # Verificar modo manual
    config = session.exec(select(ConfiguracionSistema)).first()
    if config and config.modo_manual:
        return []
    
    asignaciones = []
    cola = gestor_colas_global.obtener_cola(hospital_id)
    
    # Procesar pacientes en orden de prioridad
    lista_pacientes = cola.obtener_lista_ordenada(session)
    
    for info_paciente in lista_pacientes:
        paciente = session.get(Paciente, info_paciente["paciente_id"])
        if not paciente:
            continue
        
        # Saltar si ya está asignado
        if paciente.estado_lista_espera == EstadoListaEsperaEnum.ASIGNADO:
            continue
        
        # Actualizar estado a "buscando"
        paciente.estado_lista_espera = EstadoListaEsperaEnum.BUSCANDO
        session.add(paciente)
        session.commit()
        
        # Buscar cama compatible
        cama = buscar_cama_compatible(paciente, session)
        
        if cama:
            # Realizar asignación
            asignacion = asignar_cama_a_paciente(paciente, cama, session)
            if asignacion:
                asignaciones.append(asignacion)
        else:
            # Volver a estado esperando
            paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
            session.add(paciente)
            session.commit()
    
    return asignaciones


def asignar_cama_a_paciente(paciente: Paciente, cama: Cama, session: Session) -> Optional[Dict]:
    """Asigna una cama a un paciente."""
    
    # Actualizar paciente
    paciente.cama_destino_id = cama.id
    paciente.estado_lista_espera = EstadoListaEsperaEnum.ASIGNADO
    session.add(paciente)
    
    # Actualizar cama
    cama.estado = EstadoCamaEnum.TRASLADO_ENTRANTE
    cama.estado_updated_at = datetime.utcnow()
    cama.mensaje_estado = f"Asignado a {paciente.nombre}"
    session.add(cama)
    
    # Si el paciente tiene cama origen, actualizar estado
    if paciente.cama_id:
        cama_origen = session.get(Cama, paciente.cama_id)
        if cama_origen:
            cama_origen.estado = EstadoCamaEnum.TRASLADO_CONFIRMADO
            cama_origen.cama_asignada_destino = cama.identificador
            cama_origen.mensaje_estado = f"Cama asignada: {cama.identificador}"
            session.add(cama_origen)
    
    # Actualizar sexo de sala si es compartida
    sala = cama.sala
    if not sala.es_individual and not sala.sexo_asignado:
        sala.sexo_asignado = paciente.sexo
        session.add(sala)
    
    session.commit()
    
    return {
        "paciente_id": paciente.id,
        "paciente_nombre": paciente.nombre,
        "cama_id": cama.id,
        "cama_identificador": cama.identificador,
        "cama_origen_id": paciente.cama_id,
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
    
    # Si tiene cama origen, liberarla
    if cama_origen_id:
        cama_origen = session.get(Cama, cama_origen_id)
        if cama_origen:
            cama_origen.estado = EstadoCamaEnum.EN_LIMPIEZA
            cama_origen.limpieza_inicio = datetime.utcnow()
            cama_origen.mensaje_estado = "En limpieza"
            cama_origen.cama_asignada_destino = None
            session.add(cama_origen)
            
            # Verificar si la sala queda vacía
            actualizar_sexo_sala_si_vacia(cama_origen.sala_id, session)
    
    # Actualizar cama destino
    cama_destino.estado = EstadoCamaEnum.OCUPADA
    cama_destino.estado_updated_at = datetime.utcnow()
    cama_destino.mensaje_estado = None
    session.add(cama_destino)
    
    # Actualizar paciente
    paciente.cama_id = paciente.cama_destino_id
    paciente.cama_destino_id = None
    paciente.en_lista_espera = False
    paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
    paciente.requiere_nueva_cama = False
    paciente.en_espera = False
    paciente.timestamp_lista_espera = None
    session.add(paciente)
    
    # Remover de cola
    gestor_colas_global.remover_paciente(
        paciente.id, 
        paciente.hospital_id, 
        session, 
        paciente
    )
    
    session.commit()
    
    return {
        "success": True,
        "paciente_id": paciente.id,
        "cama_nueva_id": paciente.cama_id,
        "cama_nueva_identificador": cama_destino.identificador,
        "cama_anterior_id": cama_origen_id
    }


def cancelar_asignacion(paciente_id: str, session: Session) -> Dict:
    """Cancela la asignación de cama de un paciente."""
    paciente = session.get(Paciente, paciente_id)
    if not paciente:
        return {"error": "Paciente no encontrado"}
    
    if paciente.cama_destino_id:
        cama_destino = session.get(Cama, paciente.cama_destino_id)
        if cama_destino:
            cama_destino.estado = EstadoCamaEnum.LIBRE
            cama_destino.mensaje_estado = None
            session.add(cama_destino)
    
    # Si tiene cama origen, volver a estado apropiado
    if paciente.cama_id:
        cama_origen = session.get(Cama, paciente.cama_id)
        if cama_origen:
            cama_origen.estado = EstadoCamaEnum.TRASLADO_SALIENTE
            cama_origen.cama_asignada_destino = None
            cama_origen.mensaje_estado = "En espera de confirmación"
            session.add(cama_origen)
    
    paciente.cama_destino_id = None
    paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
    session.add(paciente)
    session.commit()
    
    return {"success": True, "paciente_id": paciente.id}


def actualizar_sexo_sala_si_vacia(sala_id: str, session: Session):
    """Actualiza el sexo de la sala si queda vacía."""
    sala = session.get(Sala, sala_id)
    if not sala or sala.es_individual:
        return
    
    # Verificar si hay camas ocupadas en la sala
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
# FUNCIONES DE ALTA
# ============================================

def verificar_alta_sugerida(paciente: Paciente) -> bool:
    """Verifica si el paciente debería tener alta sugerida."""
    if paciente.alta_solicitada:
        return False
    
    casos_especiales = json.loads(paciente.casos_especiales or "[]")
    if casos_especiales:
        return False
    
    tiene_aislamiento_aereo = paciente.tipo_aislamiento == TipoAislamientoEnum.AEREO
    
    return not paciente_tiene_requerimientos_hospitalizacion(paciente) or (
        not json.loads(paciente.requerimientos_baja or "[]") and
        not json.loads(paciente.requerimientos_uti or "[]") and
        not json.loads(paciente.requerimientos_uci or "[]") and
        not tiene_aislamiento_aereo
    )


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
    
    # Remover de cola si está
    if paciente.en_lista_espera:
        gestor_colas_global.remover_paciente(
            paciente.id,
            paciente.hospital_id,
            session,
            paciente
        )
    
    # Eliminar paciente
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


# ============================================
# FUNCIONES DE LIMPIEZA
# ============================================

def procesar_camas_en_limpieza(session: Session, tiempo_limpieza_segundos: int = 60):
    """Procesa las camas en limpieza y las libera después del tiempo configurado."""
    from datetime import timedelta
    
    query = select(Cama).where(Cama.estado == EstadoCamaEnum.EN_LIMPIEZA)
    camas_limpieza = session.exec(query).all()
    
    ahora = datetime.utcnow()
    camas_liberadas = []
    
    for cama in camas_limpieza:
        if cama.limpieza_inicio:
            tiempo_transcurrido = (ahora - cama.limpieza_inicio).total_seconds()
            if tiempo_transcurrido >= tiempo_limpieza_segundos:
                cama.estado = EstadoCamaEnum.LIBRE
                cama.limpieza_inicio = None
                cama.mensaje_estado = None
                session.add(cama)
                camas_liberadas.append(cama.identificador)
    
    if camas_liberadas:
        session.commit()
    
    return camas_liberadas