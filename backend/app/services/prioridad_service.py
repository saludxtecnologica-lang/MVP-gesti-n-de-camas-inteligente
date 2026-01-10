"""
Servicio de Prioridad v3.1
Gestiona el cálculo de prioridades y las colas de espera.

Sistema de Priorización v3.1:
=============================
Equilibrio entre Eficiencia de Flujo y Gravedad Clínica

COMPONENTES DE PRIORIDAD:
1. Base_Tipo: Hospitalizado(200) > Urgencia(100) > Derivado(80) > Ambulatorio(60)
2. Servicio_Origen: UCI(+60) > UTI(+50) > Aislamiento(+40) > Otros(+0)
3. IVC (Índice de Vulnerabilidad Clínica): Edad granular + monitorización + observación + complejidad + aislamiento
4. FRC (Factor de Requerimientos Críticos): Drogas vasoactivas + sedación + oxígeno + procedimientos + aspiración
5. Tiempo_NoLineal: Curvas escalonadas que aceleran con el tiempo
6. Boost_Rescate: Prioridad máxima (500) si supera umbral de espera

FUNCIONALIDADES PRESERVADAS:
- Tipo efectivo: Ambulatorio con estabilización clínica = prioridad Urgencia
- Paciente con cama_id = Hospitalizado (independiente de tipo_paciente original)
- Lógica especial para destino UTI

CHANGELOG v3.1:
- Agregado IVC (Índice de Vulnerabilidad Clínica)
- Agregado FRC (Factor de Requerimientos Críticos) para desempate
- Tiempo no lineal con fases escalonadas
- Mecanismo de rescate automático
- Edad granular (5 categorías en lugar de 3)
- Uso de datos existentes: monitorización, observación, procedimiento_invasivo
"""
from typing import Optional, List, Dict, Tuple, Union, Set
from sqlmodel import Session, select
from dataclasses import dataclass, field
from datetime import datetime
import logging
import heapq

from app.models.paciente import Paciente
from app.models.hospital import Hospital
from app.models.enums import (
    TipoPacienteEnum,
    ComplejidadEnum,
    EdadCategoriaEnum,
    TipoAislamientoEnum,
)
from app.repositories.paciente_repo import PacienteRepository

logger = logging.getLogger("gestion_camas.prioridad")


# ============================================
# HELPERS PARA NORMALIZACIÓN DE ENUMS/STRINGS
# ============================================

def _normalizar_tipo_paciente(valor: Union[TipoPacienteEnum, str, None]) -> str:
    """Normaliza el tipo de paciente a string lowercase para comparaciones."""
    if valor is None:
        return ""
    if hasattr(valor, 'value'):
        return str(valor.value).lower()
    return str(valor).lower()


def _normalizar_complejidad(valor: Union[ComplejidadEnum, str, None]) -> str:
    """Normaliza la complejidad a string lowercase para comparaciones."""
    if valor is None:
        return "ninguna"
    if hasattr(valor, 'value'):
        return str(valor.value).lower()
    return str(valor).lower()


def _normalizar_edad_categoria(valor: Union[EdadCategoriaEnum, str, None]) -> str:
    """Normaliza la categoría de edad a string lowercase."""
    if valor is None:
        return ""
    if hasattr(valor, 'value'):
        return str(valor.value).lower()
    return str(valor).lower()


def _normalizar_aislamiento(valor: Union[TipoAislamientoEnum, str, None]) -> str:
    """Normaliza el tipo de aislamiento a string lowercase."""
    if valor is None:
        return "ninguno"
    if hasattr(valor, 'value'):
        return str(valor.value).lower()
    return str(valor).lower()


# ============================================
# DATACLASS PARA EXPLICACIÓN DE PRIORIDAD
# ============================================

@dataclass
class ExplicacionPrioridad:
    """
    Desglose del cálculo de prioridad v3.1.
    Incluye todos los componentes del nuevo sistema.
    """
    puntaje_total: float
    puntaje_tipo: float
    puntaje_complejidad: float
    puntaje_edad: float
    puntaje_aislamiento: float
    puntaje_tiempo: float
    puntaje_servicio_origen: float = 0.0
    puntaje_boost_tiempo: float = 0.0
    # Nuevos campos v3.1
    puntaje_ivc: float = 0.0
    puntaje_frc: float = 0.0
    es_rescate: bool = False
    tipo_efectivo: str = ""
    detalles: List[str] = field(default_factory=list)


# ============================================
# COLA DE PRIORIDAD
# ============================================

class ColaPrioridad:
    """
    Cola de prioridad para un hospital.
    Implementa un heap para mantener pacientes ordenados por prioridad.
    """
    
    def __init__(self, hospital_id: str):
        self.hospital_id = hospital_id
        self._heap: List[Tuple[float, str, str]] = []
        self._pacientes: Dict[str, float] = {}
    
    def agregar(self, paciente_id: str, prioridad: float) -> None:
        """Agrega un paciente a la cola."""
        if paciente_id in self._pacientes:
            self.remover(paciente_id)
        
        timestamp = datetime.utcnow().isoformat()
        heapq.heappush(self._heap, (-prioridad, timestamp, paciente_id))
        self._pacientes[paciente_id] = prioridad
    
    def remover(self, paciente_id: str) -> bool:
        """Remueve un paciente de la cola."""
        if paciente_id not in self._pacientes:
            return False
        del self._pacientes[paciente_id]
        return True
    
    def obtener_siguiente(self) -> Optional[str]:
        """Obtiene el siguiente paciente sin removerlo."""
        self._limpiar_heap()
        if self._heap:
            return self._heap[0][2]
        return None
    
    def extraer_siguiente(self) -> Optional[str]:
        """Extrae el siguiente paciente de la cola."""
        self._limpiar_heap()
        if self._heap:
            _, _, paciente_id = heapq.heappop(self._heap)
            if paciente_id in self._pacientes:
                del self._pacientes[paciente_id]
                return paciente_id
        return None
    
    def _limpiar_heap(self) -> None:
        """Limpia entradas obsoletas del heap."""
        while self._heap and self._heap[0][2] not in self._pacientes:
            heapq.heappop(self._heap)
    
    def tamano(self) -> int:
        """Retorna el número de pacientes en la cola."""
        return len(self._pacientes)
    
    def contiene(self, paciente_id: str) -> bool:
        """Verifica si un paciente está en la cola."""
        return paciente_id in self._pacientes
    
    def obtener_prioridad(self, paciente_id: str) -> Optional[float]:
        """Obtiene la prioridad de un paciente."""
        return self._pacientes.get(paciente_id)
    
    def obtener_todos_ordenados(self) -> List[Tuple[str, float]]:
        """Obtiene todos los pacientes ordenados por prioridad."""
        items = [(pid, prio) for pid, prio in self._pacientes.items()]
        return sorted(items, key=lambda x: x[1], reverse=True)


# ============================================
# GESTOR GLOBAL DE COLAS
# ============================================

class GestorColas:
    """Gestor global de colas de prioridad. Mantiene una cola por hospital."""
    
    def __init__(self):
        self._colas: Dict[str, ColaPrioridad] = {}
    
    def obtener_cola(self, hospital_id: str) -> ColaPrioridad:
        """Obtiene la cola de un hospital, creándola si no existe."""
        if hospital_id not in self._colas:
            self._colas[hospital_id] = ColaPrioridad(hospital_id)
        return self._colas[hospital_id]
    
    def sincronizar_cola_con_db(self, hospital_id: str, session: Session) -> None:
        """Sincroniza la cola con la base de datos."""
        cola = self.obtener_cola(hospital_id)
        
        pacientes = session.exec(
            select(Paciente).where(
                Paciente.hospital_id == hospital_id,
                Paciente.en_lista_espera == True
            )
        ).all()
        
        for paciente in pacientes:
            prioridad = PrioridadService(session).calcular_prioridad(paciente)
            cola.agregar(paciente.id, prioridad)
            paciente.prioridad_calculada = prioridad
            session.add(paciente)
        
        session.commit()


# Instancia global
gestor_colas_global = GestorColas()


# ============================================
# SERVICIO DE PRIORIDAD v3.1
# ============================================

class PrioridadService:
    """
    Servicio para cálculo de prioridades v3.1.
    
    IMPORTANTE: Un paciente se considera HOSPITALIZADO si:
    - tiene cama_id asignada (ya está en una cama del hospital)
    - O su tipo_paciente es explícitamente "hospitalizado"
    
    IMPORTANTE: Un paciente AMBULATORIO con motivo "estabilizacion_clinica"
    se trata como URGENCIA para efectos de priorización.
    
    Sistema de Priorización v3.1:
    =============================
    
    1. BASE POR TIPO DE PACIENTE (tipo efectivo):
       - Hospitalizado (con cama): 200 (máxima prioridad)
       - Derivado: 150 (alta prioridad - transferencia inter-hospitalaria)
       - Urgencia (incluye ambulatorio por estabilización): 100
       - Ambulatorio (tratamiento): 60
    
    2. SERVICIO DE ORIGEN (solo hospitalizados):
       - UCI: +60
       - UTI: +50
       - Aislamientos: +40
       - Otros: +0
    
    3. IVC - ÍNDICE DE VULNERABILIDAD CLÍNICA (NUEVO):
       - Edad granular: ≥80(+25), 70-79(+20), 60-69(+15), <5(+20), 5-14(+15)
       - Monitorización activa: +20
       - Observación activa: +15
       - Complejidad: UCI(+30), UTI(+20), Baja(+5)
       - Aislamiento crítico: Aéreo(+20), Amb.protegido(+15), Especial(+10)
       - Embarazada: +20
       - Casos especiales: +15
    
    4. FRC - FACTOR DE REQUERIMIENTOS CRÍTICOS (NUEVO):
       - Drogas vasoactivas: +15
       - Sedación: +12
       - Oxígeno (cualquier tipo): +10
       - Procedimiento invasivo/quirúrgico: +10
       - Aspiración invasiva de secreciones: +10
    
    5. TIEMPO NO LINEAL (NUEVO):
       Urgencias:    0-4h(3pts/h), 4-8h(5pts/h), >8h(8pts/h + boost 40)
       Derivados:    0-12h(2pts/h), 12-24h(4pts/h), >24h(6pts/h + boost 45)
       Ambulatorios: 0-48h(1pts/h), 48-96h(2pts/h), >96h(4pts/h + boost 50)
    
    6. MECANISMO DE RESCATE (NUEVO):
       - Urgencia > 24h: Prioridad fija 500
       - Derivado > 48h: Prioridad fija 500
       - Ambulatorio > 7 días: Prioridad fija 500
    """
    
    # ========================================
    # PESOS BASE POR TIPO DE PACIENTE
    # ========================================
    PESO_TIPO = {
        'hospitalizado': 200,
        'derivado': 150,      # Alta prioridad - transferencia inter-hospitalaria
        'urgencia': 100,
        'ambulatorio': 60,
    }
    
    # ========================================
    # BONUS POR SERVICIO DE ORIGEN (solo hospitalizados)
    # ========================================
    SERVICIOS_UCI = {'uci', 'unidad de cuidados intensivos', 'cuidados intensivos', 'upc'}
    SERVICIOS_UTI = {'uti', 'unidad de tratamiento intensivo', 'intermedio', 'uci intermedia'}
    SERVICIOS_AISLAMIENTO = {
        'aislamiento', 'aislado', 'aislamiento respiratorio',
        'aislamiento contacto', 'aislamiento gotitas', 'aislamiento aereo'
    }
    
    BONUS_SERVICIO_ORIGEN = {
        'uci': 60,
        'uti': 50,
        'aislamiento': 40,
        'otros': 0,
    }
    
    # ========================================
    # BONUS ESPECIAL PARA DESTINO UTI
    # ========================================
    BONUS_DESTINO_UTI = {
        'todos_servicios': 70,
        'uci': 60,
        'otros_origenes': 0,
    }
    
    # ========================================
    # IVC - ÍNDICE DE VULNERABILIDAD CLÍNICA
    # ========================================
    
    # Edad granular (5 categorías)
    BONUS_EDAD_GRANULAR = {
        'muy_mayor': 25,      # ≥80 años
        'mayor': 20,          # 70-79 años
        'adulto_mayor': 15,   # 60-69 años
        'infante': 20,        # <5 años
        'nino': 15,           # 5-14 años
        'adulto': 0,          # 15-59 años
    }
    
    # Timers activos
    BONUS_MONITORIZACION_ACTIVA = 20
    BONUS_OBSERVACION_ACTIVA = 15
    
    # Complejidad (para IVC, separado del peso base)
    BONUS_COMPLEJIDAD_IVC = {
        'alta': 30,
        'media': 20,
        'baja': 5,
        'ninguna': 0,
    }
    
    # Aislamiento crítico
    BONUS_AISLAMIENTO_IVC = {
        'aereo': 20,
        'aéreo': 20,
        'ambiente_protegido': 15,
        'ambiente protegido': 15,
        'especial': 10,
        'gotitas': 5,
        'contacto': 3,
        'ninguno': 0,
    }
    
    # Condiciones especiales
    BONUS_EMBARAZADA = 20
    BONUS_CASOS_ESPECIALES = 15
    
    # ========================================
    # FRC - FACTOR DE REQUERIMIENTOS CRÍTICOS
    # ========================================
    BONUS_REQUERIMIENTOS_CRITICOS = {
        'drogas_vasoactivas': 15,
        'sedacion': 12,
        'oxigeno': 10,
        'procedimiento_invasivo': 10,
        'aspiracion_secreciones': 10,
    }
    
    # Keywords para detección de requerimientos críticos
    KEYWORDS_DROGAS_VASOACTIVAS: Set[str] = {
        'drogas_vasoactivas', 'vasoactivos', 'noradrenalina', 'norepinefrina',
        'dopamina', 'dobutamina', 'vasopresina', 'adrenalina', 'epinefrina',
        'dva', 'drogas vasoactivas', 'aminas', 'inotropicos', 'vasopresores'
    }
    
    KEYWORDS_SEDACION: Set[str] = {
        'sedacion', 'sedación', 'midazolam', 'propofol', 'fentanilo', 'fentanil',
        'dexmedetomidina', 'ketamina', 'bic_sedacion', 'infusion_sedacion',
        'sedoanalgesia', 'analgosedacion'
    }
    
    KEYWORDS_OXIGENO: Set[str] = {
        'oxigeno', 'oxígeno', 'o2', 'naricera', 'canula_nasal', 'cánula nasal',
        'mascarilla', 'venturi', 'multiventuri', 'reservorio', 'mascara_reservorio',
        'cnaf', 'alto_flujo', 'alto flujo', 'vmni', 'ventilacion_no_invasiva',
        'vmi', 'ventilacion_mecanica', 'ventilacion_invasiva', 'tubo_endotraqueal',
        'intubacion', 'soporte_ventilatorio', 'oxigenoterapia'
    }
    
    KEYWORDS_ASPIRACION: Set[str] = {
        'aspiracion_secreciones', 'aspiración', 'aspiracion', 'aspiracion_invasiva',
        'traqueostomia', 'traqueostomía', 'tqt', 'tubo_endotraqueal', 'tet',
        'secreciones_invasivo', 'manejo_via_aerea', 'toilet_bronquial'
    }
    
    KEYWORDS_PROCEDIMIENTO: Set[str] = {
        'procedimiento_invasivo', 'cirugia', 'cirugía', 'quirurgico', 'quirúrgico',
        'intervencion', 'intervención', 'operacion', 'operación', 'biopsia',
        'drenaje', 'puncion', 'punción', 'cateterismo', 'endoscopia'
    }
    
    # ========================================
    # CONFIGURACIÓN DE TIEMPO NO LINEAL
    # ========================================
    
    # Urgencias: 3 fases
    TIEMPO_URGENCIA_FASE1_HORAS = 4
    TIEMPO_URGENCIA_FASE1_PTS = 3
    TIEMPO_URGENCIA_FASE2_HORAS = 8
    TIEMPO_URGENCIA_FASE2_PTS = 5
    TIEMPO_URGENCIA_FASE3_PTS = 8
    TIEMPO_URGENCIA_BOOST = 40
    
    # Derivados: 3 fases
    TIEMPO_DERIVADO_FASE1_HORAS = 12
    TIEMPO_DERIVADO_FASE1_PTS = 2
    TIEMPO_DERIVADO_FASE2_HORAS = 24
    TIEMPO_DERIVADO_FASE2_PTS = 4
    TIEMPO_DERIVADO_FASE3_PTS = 6
    TIEMPO_DERIVADO_BOOST = 45
    
    # Ambulatorios: 3 fases
    TIEMPO_AMBULATORIO_FASE1_HORAS = 48
    TIEMPO_AMBULATORIO_FASE1_PTS = 1
    TIEMPO_AMBULATORIO_FASE2_HORAS = 96
    TIEMPO_AMBULATORIO_FASE2_PTS = 2
    TIEMPO_AMBULATORIO_FASE3_PTS = 4
    TIEMPO_AMBULATORIO_BOOST = 50
    
    # ========================================
    # MECANISMO DE RESCATE
    # ========================================
    UMBRAL_RESCATE_HORAS = {
        'urgencia': 24,
        'derivado': 48,
        'ambulatorio': 168,  # 7 días
    }
    PRIORIDAD_RESCATE = 500
    
    # ========================================
    # CONSTRUCTOR
    # ========================================
    
    def __init__(self, session: Session):
        self.session = session
        self.paciente_repo = PacienteRepository(session)
    
    # ========================================
    # MÉTODOS DE TIPO EFECTIVO (PRESERVADOS)
    # ========================================
    
    def _es_paciente_hospitalizado(self, paciente: Paciente) -> bool:
        """
        Determina si un paciente debe ser tratado como HOSPITALIZADO.
        
        Un paciente ES hospitalizado si:
        1. Tiene cama_id asignada (ya está ocupando una cama)
        2. O su tipo_paciente es explícitamente "hospitalizado"
        """
        if paciente.cama_id:
            return True
        
        tipo = _normalizar_tipo_paciente(paciente.tipo_paciente)
        if tipo == 'hospitalizado':
            return True
        
        return False
    
    def _obtener_tipo_efectivo(self, paciente: Paciente) -> str:
        """
        Determina el tipo efectivo del paciente para priorización.

        REGLAS:
        1. Si es derivado aceptado → derivado (PRIORIDAD SOBRE cama_id)
        2. Si tiene cama asignada → hospitalizado
        3. Si es ambulatorio con estabilización clínica → urgencia
        4. En otro caso → tipo original
        """
        # CRÍTICO: Verificar primero si es derivado aceptado
        # Un paciente derivado puede tener cama_id (su cama de origen)
        # pero debe ser tratado como DERIVADO para priorización correcta
        if paciente.derivacion_estado == "aceptada":
            return 'derivado'

        # Si tiene cama asignada, ES hospitalizado
        if self._es_paciente_hospitalizado(paciente):
            return 'hospitalizado'

        tipo = _normalizar_tipo_paciente(paciente.tipo_paciente)

        # CRÍTICO: Ambulatorio con estabilización = prioridad urgencia
        if tipo == 'ambulatorio':
            motivo = getattr(paciente, 'motivo_ingreso_ambulatorio', None)
            if motivo == 'estabilizacion_clinica':
                return 'urgencia'

        return tipo
    
    # ========================================
    # MÉTODOS DE SERVICIO DE ORIGEN (PRESERVADOS)
    # ========================================
    
    def _clasificar_servicio_origen(self, servicio_nombre: Optional[str]) -> str:
        """Clasifica el servicio de origen del paciente."""
        if not servicio_nombre:
            return 'otros'
        
        servicio_lower = servicio_nombre.lower().strip()
        
        if any(s in servicio_lower for s in self.SERVICIOS_UCI):
            return 'uci'
        if any(s in servicio_lower for s in self.SERVICIOS_UTI):
            return 'uti'
        if any(s in servicio_lower for s in self.SERVICIOS_AISLAMIENTO):
            return 'aislamiento'
        
        return 'otros'
    
    def _obtener_servicio_origen(self, paciente: Paciente) -> Optional[str]:
        """Obtiene el nombre del servicio de origen del paciente."""
        if hasattr(paciente, 'origen_servicio_nombre') and paciente.origen_servicio_nombre:
            return paciente.origen_servicio_nombre
        
        if hasattr(paciente, 'servicio_origen') and paciente.servicio_origen:
            return paciente.servicio_origen
        
        if hasattr(paciente, 'cama') and paciente.cama:
            if hasattr(paciente.cama, 'sala') and paciente.cama.sala:
                if hasattr(paciente.cama.sala, 'servicio') and paciente.cama.sala.servicio:
                    return paciente.cama.sala.servicio.nombre
        
        if paciente.cama_id:
            try:
                from app.models.cama import Cama
                cama = self.session.get(Cama, paciente.cama_id)
                if cama and cama.sala_id:
                    from app.models.sala import Sala
                    sala = self.session.get(Sala, cama.sala_id)
                    if sala and sala.servicio_id:
                        from app.models.servicio import Servicio
                        servicio = self.session.get(Servicio, sala.servicio_id)
                        if servicio:
                            return servicio.nombre
            except Exception as e:
                logger.debug(f"No se pudo obtener servicio de cama: {e}")
        
        return None
    
    def _obtener_servicio_destino(self, paciente: Paciente) -> Optional[str]:
        """Obtiene el nombre del servicio de destino del paciente."""
        if hasattr(paciente, 'servicio_destino') and paciente.servicio_destino:
            return paciente.servicio_destino
        if hasattr(paciente, 'servicio_destino_nombre') and paciente.servicio_destino_nombre:
            return paciente.servicio_destino_nombre
        return None
    
    def _es_destino_uti(self, paciente: Paciente) -> bool:
        """Verifica si el destino del paciente es UTI."""
        servicio_destino = self._obtener_servicio_destino(paciente)
        if not servicio_destino:
            return False
        servicio_lower = servicio_destino.lower().strip()
        return any(s in servicio_lower for s in self.SERVICIOS_UTI)
    
    def _calcular_bonus_servicio_origen(
        self, 
        paciente: Paciente, 
        servicio_origen: Optional[str],
        es_destino_uti: bool
    ) -> Tuple[float, str]:
        """Calcula el bonus por servicio de origen."""
        es_hospitalizado = self._es_paciente_hospitalizado(paciente)
        tipo_servicio = self._clasificar_servicio_origen(servicio_origen)
        
        # Caso especial: destino es UTI
        if es_destino_uti:
            if es_hospitalizado:
                if tipo_servicio == 'uci':
                    return (self.BONUS_DESTINO_UTI['uci'], 
                            f"Origen UCI (destino UTI): +{self.BONUS_DESTINO_UTI['uci']}")
                else:
                    return (self.BONUS_DESTINO_UTI['todos_servicios'],
                            f"Origen servicio {tipo_servicio} (destino UTI): +{self.BONUS_DESTINO_UTI['todos_servicios']}")
            else:
                return (self.BONUS_DESTINO_UTI['otros_origenes'],
                        "Origen externo sin cama (destino UTI): +0")
        
        # Caso normal
        if not es_hospitalizado:
            return (0, "")
        
        bonus = self.BONUS_SERVICIO_ORIGEN.get(tipo_servicio, 0)
        
        if bonus > 0:
            descripcion = f"Servicio origen {tipo_servicio.upper()}: +{bonus}"
        else:
            descripcion = f"Servicio origen ({servicio_origen or 'general'}): +0"
        
        return (bonus, descripcion)
    
    # ========================================
    # NUEVOS MÉTODOS v3.1: IVC
    # ========================================
    
    def _calcular_ivc(self, paciente: Paciente) -> Tuple[float, List[str]]:
        """
        Calcula el Índice de Vulnerabilidad Clínica (IVC).
        
        Componentes:
        - Edad granular
        - Monitorización activa
        - Observación activa
        - Complejidad
        - Aislamiento crítico
        - Embarazada
        - Casos especiales
        
        Returns:
            Tuple de (puntaje_ivc, lista_detalles)
        """
        ivc = 0.0
        detalles = []
        
        # 1. Edad granular
        edad = paciente.edad or 0
        if edad >= 80:
            ivc += self.BONUS_EDAD_GRANULAR['muy_mayor']
            detalles.append(f'IVC Edad ≥80: +{self.BONUS_EDAD_GRANULAR["muy_mayor"]}')
        elif edad >= 70:
            ivc += self.BONUS_EDAD_GRANULAR['mayor']
            detalles.append(f'IVC Edad 70-79: +{self.BONUS_EDAD_GRANULAR["mayor"]}')
        elif edad >= 60:
            ivc += self.BONUS_EDAD_GRANULAR['adulto_mayor']
            detalles.append(f'IVC Edad 60-69: +{self.BONUS_EDAD_GRANULAR["adulto_mayor"]}')
        elif edad < 5:
            ivc += self.BONUS_EDAD_GRANULAR['infante']
            detalles.append(f'IVC Infante <5: +{self.BONUS_EDAD_GRANULAR["infante"]}')
        elif edad < 15:
            ivc += self.BONUS_EDAD_GRANULAR['nino']
            detalles.append(f'IVC Niño 5-14: +{self.BONUS_EDAD_GRANULAR["nino"]}')
        
        # 2. Monitorización activa
        if (hasattr(paciente, 'monitorizacion_inicio') and paciente.monitorizacion_inicio and 
            hasattr(paciente, 'monitorizacion_tiempo_horas') and paciente.monitorizacion_tiempo_horas):
            ivc += self.BONUS_MONITORIZACION_ACTIVA
            detalles.append(f'IVC Monitorización activa: +{self.BONUS_MONITORIZACION_ACTIVA}')
        
        # 3. Observación activa
        if (hasattr(paciente, 'observacion_inicio') and paciente.observacion_inicio and 
            hasattr(paciente, 'observacion_tiempo_horas') and paciente.observacion_tiempo_horas):
            ivc += self.BONUS_OBSERVACION_ACTIVA
            detalles.append(f'IVC Observación activa: +{self.BONUS_OBSERVACION_ACTIVA}')
        
        # 4. Complejidad
        complejidad = _normalizar_complejidad(paciente.complejidad_requerida)
        bonus_complejidad = self.BONUS_COMPLEJIDAD_IVC.get(complejidad, 0)
        if bonus_complejidad > 0:
            ivc += bonus_complejidad
            nombre_complejidad = {'alta': 'UCI', 'media': 'UTI', 'baja': 'Baja'}.get(complejidad, complejidad)
            detalles.append(f'IVC Complejidad {nombre_complejidad}: +{bonus_complejidad}')
        
        # 5. Aislamiento crítico
        aislamiento = _normalizar_aislamiento(paciente.tipo_aislamiento)
        bonus_aislamiento = self.BONUS_AISLAMIENTO_IVC.get(aislamiento, 0)
        if bonus_aislamiento > 0:
            ivc += bonus_aislamiento
            detalles.append(f'IVC Aislamiento {aislamiento}: +{bonus_aislamiento}')
        
        # 6. Embarazada
        if paciente.es_embarazada:
            ivc += self.BONUS_EMBARAZADA
            detalles.append(f'IVC Embarazada: +{self.BONUS_EMBARAZADA}')
        
        # 7. Casos especiales
        if paciente.tiene_casos_especiales():
            ivc += self.BONUS_CASOS_ESPECIALES
            detalles.append(f'IVC Casos especiales: +{self.BONUS_CASOS_ESPECIALES}')
        
        return ivc, detalles
    
    # ========================================
    # NUEVOS MÉTODOS v3.1: FRC
    # ========================================
    
    def _obtener_todos_requerimientos(self, paciente: Paciente) -> Set[str]:
        """
        Obtiene todos los requerimientos del paciente como un set de strings normalizados.
        """
        todos_reqs = set()
        
        for campo in ['requerimientos_baja', 'requerimientos_uti', 'requerimientos_uci', 'requerimientos_no_definen']:
            try:
                reqs = paciente.get_requerimientos_lista(campo)
                for req in reqs:
                    todos_reqs.add(req.lower().strip())
            except Exception:
                pass
        
        return todos_reqs
    
    def _calcular_frc(self, paciente: Paciente) -> Tuple[float, List[str]]:
        """
        Calcula el Factor de Requerimientos Críticos (FRC).
        
        Detecta requerimientos críticos que indican mayor gravedad:
        - Drogas vasoactivas
        - Sedación
        - Oxígeno (cualquier tipo)
        - Procedimiento invasivo/quirúrgico
        - Aspiración invasiva de secreciones
        
        Returns:
            Tuple de (puntaje_frc, lista_detalles)
        """
        frc = 0.0
        detalles = []
        
        # Obtener todos los requerimientos como set normalizado
        reqs_set = self._obtener_todos_requerimientos(paciente)
        
        # 1. Detectar drogas vasoactivas
        if reqs_set & self.KEYWORDS_DROGAS_VASOACTIVAS:
            bonus = self.BONUS_REQUERIMIENTOS_CRITICOS['drogas_vasoactivas']
            frc += bonus
            detalles.append(f'FRC Drogas vasoactivas: +{bonus}')
        
        # 2. Detectar sedación
        if reqs_set & self.KEYWORDS_SEDACION:
            bonus = self.BONUS_REQUERIMIENTOS_CRITICOS['sedacion']
            frc += bonus
            detalles.append(f'FRC Sedación: +{bonus}')
        
        # 3. Detectar oxígeno (cualquier tipo)
        if reqs_set & self.KEYWORDS_OXIGENO:
            bonus = self.BONUS_REQUERIMIENTOS_CRITICOS['oxigeno']
            frc += bonus
            detalles.append(f'FRC Oxígeno: +{bonus}')
        
        # 4. Detectar procedimiento invasivo/quirúrgico
        tiene_procedimiento = False
        
        # Verificar campo booleano
        if hasattr(paciente, 'procedimiento_invasivo') and paciente.procedimiento_invasivo:
            tiene_procedimiento = True
        
        # Verificar preparación quirúrgica
        if hasattr(paciente, 'preparacion_quirurgica_detalle') and paciente.preparacion_quirurgica_detalle:
            tiene_procedimiento = True
        
        # Verificar keywords en requerimientos
        if reqs_set & self.KEYWORDS_PROCEDIMIENTO:
            tiene_procedimiento = True
        
        if tiene_procedimiento:
            bonus = self.BONUS_REQUERIMIENTOS_CRITICOS['procedimiento_invasivo']
            frc += bonus
            detalles.append(f'FRC Procedimiento invasivo: +{bonus}')
        
        # 5. Detectar aspiración invasiva de secreciones
        if reqs_set & self.KEYWORDS_ASPIRACION:
            bonus = self.BONUS_REQUERIMIENTOS_CRITICOS['aspiracion_secreciones']
            frc += bonus
            detalles.append(f'FRC Aspiración secreciones: +{bonus}')
        
        return frc, detalles
    
    # ========================================
    # NUEVOS MÉTODOS v3.1: TIEMPO NO LINEAL
    # ========================================
    
    def _calcular_tiempo_no_lineal(self, paciente: Paciente) -> Tuple[float, str]:
        """
        Calcula el puntaje de tiempo con curva no lineal escalonada.
        
        Las curvas varían según el tipo efectivo:
        - Urgencias: Aceleran más rápido
        - Derivados: Aceleración media
        - Ambulatorios: Aceleración lenta
        
        Returns:
            Tuple de (puntaje_tiempo, descripción)
        """
        tiempo_min = getattr(paciente, 'tiempo_espera_min', 0) or 0
        horas = tiempo_min / 60.0
        tipo_efectivo = self._obtener_tipo_efectivo(paciente)
        
        pts = 0.0
        desc = ""
        
        if tipo_efectivo == 'urgencia':
            # Urgencias: 0-4h(3pts/h), 4-8h(5pts/h), >8h(8pts/h + boost)
            if horas <= self.TIEMPO_URGENCIA_FASE1_HORAS:
                pts = horas * self.TIEMPO_URGENCIA_FASE1_PTS
            elif horas <= self.TIEMPO_URGENCIA_FASE2_HORAS:
                pts = (self.TIEMPO_URGENCIA_FASE1_HORAS * self.TIEMPO_URGENCIA_FASE1_PTS +
                       (horas - self.TIEMPO_URGENCIA_FASE1_HORAS) * self.TIEMPO_URGENCIA_FASE2_PTS)
            else:
                pts = (self.TIEMPO_URGENCIA_FASE1_HORAS * self.TIEMPO_URGENCIA_FASE1_PTS +
                       (self.TIEMPO_URGENCIA_FASE2_HORAS - self.TIEMPO_URGENCIA_FASE1_HORAS) * self.TIEMPO_URGENCIA_FASE2_PTS +
                       (horas - self.TIEMPO_URGENCIA_FASE2_HORAS) * self.TIEMPO_URGENCIA_FASE3_PTS +
                       self.TIEMPO_URGENCIA_BOOST)
            desc = f'Tiempo urgencia {horas:.1f}h: +{pts:.0f}'
        
        elif tipo_efectivo == 'derivado':
            # Derivados: 0-12h(2pts/h), 12-24h(4pts/h), >24h(6pts/h + boost)
            if horas <= self.TIEMPO_DERIVADO_FASE1_HORAS:
                pts = horas * self.TIEMPO_DERIVADO_FASE1_PTS
            elif horas <= self.TIEMPO_DERIVADO_FASE2_HORAS:
                pts = (self.TIEMPO_DERIVADO_FASE1_HORAS * self.TIEMPO_DERIVADO_FASE1_PTS +
                       (horas - self.TIEMPO_DERIVADO_FASE1_HORAS) * self.TIEMPO_DERIVADO_FASE2_PTS)
            else:
                pts = (self.TIEMPO_DERIVADO_FASE1_HORAS * self.TIEMPO_DERIVADO_FASE1_PTS +
                       (self.TIEMPO_DERIVADO_FASE2_HORAS - self.TIEMPO_DERIVADO_FASE1_HORAS) * self.TIEMPO_DERIVADO_FASE2_PTS +
                       (horas - self.TIEMPO_DERIVADO_FASE2_HORAS) * self.TIEMPO_DERIVADO_FASE3_PTS +
                       self.TIEMPO_DERIVADO_BOOST)
            desc = f'Tiempo derivado {horas:.1f}h: +{pts:.0f}'
        
        elif tipo_efectivo == 'hospitalizado':
            # Hospitalizados: Usar curva de urgencia (ya tienen prioridad alta)
            if horas <= self.TIEMPO_URGENCIA_FASE1_HORAS:
                pts = horas * self.TIEMPO_URGENCIA_FASE1_PTS
            elif horas <= self.TIEMPO_URGENCIA_FASE2_HORAS:
                pts = (self.TIEMPO_URGENCIA_FASE1_HORAS * self.TIEMPO_URGENCIA_FASE1_PTS +
                       (horas - self.TIEMPO_URGENCIA_FASE1_HORAS) * self.TIEMPO_URGENCIA_FASE2_PTS)
            else:
                pts = (self.TIEMPO_URGENCIA_FASE1_HORAS * self.TIEMPO_URGENCIA_FASE1_PTS +
                       (self.TIEMPO_URGENCIA_FASE2_HORAS - self.TIEMPO_URGENCIA_FASE1_HORAS) * self.TIEMPO_URGENCIA_FASE2_PTS +
                       (horas - self.TIEMPO_URGENCIA_FASE2_HORAS) * self.TIEMPO_URGENCIA_FASE3_PTS)
            # Sin boost para hospitalizados (ya tienen prioridad máxima)
            desc = f'Tiempo hospitalizado {horas:.1f}h: +{pts:.0f}'
        
        else:  # ambulatorio (tratamiento)
            # Ambulatorios: 0-48h(1pts/h), 48-96h(2pts/h), >96h(4pts/h + boost)
            if horas <= self.TIEMPO_AMBULATORIO_FASE1_HORAS:
                pts = horas * self.TIEMPO_AMBULATORIO_FASE1_PTS
            elif horas <= self.TIEMPO_AMBULATORIO_FASE2_HORAS:
                pts = (self.TIEMPO_AMBULATORIO_FASE1_HORAS * self.TIEMPO_AMBULATORIO_FASE1_PTS +
                       (horas - self.TIEMPO_AMBULATORIO_FASE1_HORAS) * self.TIEMPO_AMBULATORIO_FASE2_PTS)
            else:
                pts = (self.TIEMPO_AMBULATORIO_FASE1_HORAS * self.TIEMPO_AMBULATORIO_FASE1_PTS +
                       (self.TIEMPO_AMBULATORIO_FASE2_HORAS - self.TIEMPO_AMBULATORIO_FASE1_HORAS) * self.TIEMPO_AMBULATORIO_FASE2_PTS +
                       (horas - self.TIEMPO_AMBULATORIO_FASE2_HORAS) * self.TIEMPO_AMBULATORIO_FASE3_PTS +
                       self.TIEMPO_AMBULATORIO_BOOST)
            desc = f'Tiempo ambulatorio {horas:.1f}h: +{pts:.0f}'
        
        return pts, desc
    
    # ========================================
    # NUEVOS MÉTODOS v3.1: MECANISMO DE RESCATE
    # ========================================
    
    def _debe_activar_rescate(self, paciente: Paciente) -> bool:
        """
        Determina si se debe activar el mecanismo de rescate para un paciente.
        
        El rescate se activa cuando el paciente supera el umbral máximo de espera
        según su tipo.
        
        Returns:
            True si debe activar rescate
        """
        tiempo_min = getattr(paciente, 'tiempo_espera_min', 0) or 0
        horas = tiempo_min / 60.0
        
        tipo_efectivo = self._obtener_tipo_efectivo(paciente)
        
        # Hospitalizados no tienen rescate (ya tienen prioridad máxima)
        if tipo_efectivo == 'hospitalizado':
            return False
        
        umbral = self.UMBRAL_RESCATE_HORAS.get(tipo_efectivo, 168)  # Default 7 días
        
        return horas >= umbral
    
    # ========================================
    # MÉTODO PRINCIPAL: CALCULAR PRIORIDAD
    # ========================================
    
    def calcular_prioridad(
        self, 
        paciente: Paciente,
        servicio_destino: Optional[str] = None
    ) -> float:
        """
        Calcula la prioridad de un paciente v3.1.
        
        Fórmula:
        P = Base_Tipo + Servicio_Origen + IVC + FRC + Tiempo_NoLineal
        
        Si activa rescate: P = PRIORIDAD_RESCATE (500)
        
        Args:
            paciente: El paciente a evaluar
            servicio_destino: Servicio de destino (opcional, para lógica especial UTI)
        
        Returns:
            Puntaje de prioridad calculado
        """
        # Verificar mecanismo de rescate primero
        if self._debe_activar_rescate(paciente):
            logger.warning(
                f"🚨 RESCATE ACTIVADO para {paciente.nombre} - "
                f"Tiempo espera: {getattr(paciente, 'tiempo_espera_min', 0)/60:.1f}h"
            )
            return self.PRIORIDAD_RESCATE
        
        puntaje = 0.0
        
        # 1. Puntaje por tipo de paciente EFECTIVO
        tipo_efectivo = self._obtener_tipo_efectivo(paciente)
        puntaje_tipo = self.PESO_TIPO.get(tipo_efectivo, 0)
        puntaje += puntaje_tipo
        
        logger.debug(
            f"Paciente {paciente.nombre}: tipo_original={_normalizar_tipo_paciente(paciente.tipo_paciente)}, "
            f"tiene_cama={bool(paciente.cama_id)}, tipo_efectivo={tipo_efectivo}, puntaje_tipo={puntaje_tipo}"
        )
        
        # 2. Puntaje por servicio de origen (solo hospitalizados)
        servicio_origen = self._obtener_servicio_origen(paciente)
        es_destino_uti = self._es_destino_uti(paciente) if not servicio_destino else \
                         any(s in servicio_destino.lower() for s in self.SERVICIOS_UTI)
        
        bonus_servicio, _ = self._calcular_bonus_servicio_origen(
            paciente, servicio_origen, es_destino_uti
        )
        puntaje += bonus_servicio
        
        # 3. IVC - Índice de Vulnerabilidad Clínica
        puntaje_ivc, _ = self._calcular_ivc(paciente)
        puntaje += puntaje_ivc
        
        # 4. FRC - Factor de Requerimientos Críticos
        puntaje_frc, _ = self._calcular_frc(paciente)
        puntaje += puntaje_frc
        
        # 5. Tiempo no lineal
        puntaje_tiempo, _ = self._calcular_tiempo_no_lineal(paciente)
        puntaje += puntaje_tiempo
        
        logger.info(
            f"Prioridad v3.1 {paciente.nombre}: tipo={tipo_efectivo}({puntaje_tipo}), "
            f"servicio={bonus_servicio}, IVC={puntaje_ivc}, FRC={puntaje_frc}, "
            f"tiempo={puntaje_tiempo:.1f}, TOTAL={puntaje:.2f}"
        )
        
        return round(puntaje, 2)
    
    # ========================================
    # MÉTODO EXPLICAR PRIORIDAD
    # ========================================
    
    def explicar_prioridad(
        self, 
        paciente: Paciente,
        servicio_destino: Optional[str] = None
    ) -> ExplicacionPrioridad:
        """
        Calcula y explica la prioridad de un paciente con desglose detallado v3.1.
        
        Args:
            paciente: El paciente a evaluar
            servicio_destino: Servicio de destino (opcional)
        
        Returns:
            ExplicacionPrioridad con desglose completo
        """
        detalles = []
        
        # Verificar rescate
        es_rescate = self._debe_activar_rescate(paciente)
        if es_rescate:
            tiempo_horas = getattr(paciente, 'tiempo_espera_min', 0) / 60.0
            detalles.append(f"🚨 RESCATE ACTIVADO ({tiempo_horas:.1f}h espera): +{self.PRIORIDAD_RESCATE}")
            
            return ExplicacionPrioridad(
                puntaje_total=self.PRIORIDAD_RESCATE,
                puntaje_tipo=0,
                puntaje_complejidad=0,
                puntaje_edad=0,
                puntaje_aislamiento=0,
                puntaje_tiempo=0,
                puntaje_servicio_origen=0,
                puntaje_boost_tiempo=0,
                puntaje_ivc=0,
                puntaje_frc=0,
                es_rescate=True,
                tipo_efectivo=self._obtener_tipo_efectivo(paciente),
                detalles=detalles
            )
        
        # 1. Tipo efectivo
        tipo_efectivo = self._obtener_tipo_efectivo(paciente)
        tipo_original = _normalizar_tipo_paciente(paciente.tipo_paciente)
        puntaje_tipo = self.PESO_TIPO.get(tipo_efectivo, 0)
        
        if tipo_efectivo != tipo_original:
            detalles.append(f"Tipo efectivo: {tipo_efectivo} (original: {tipo_original}): +{puntaje_tipo}")
        else:
            detalles.append(f"Tipo {tipo_efectivo}: +{puntaje_tipo}")
        
        # 2. Servicio de origen
        servicio_origen = self._obtener_servicio_origen(paciente)
        es_destino_uti = self._es_destino_uti(paciente) if not servicio_destino else \
                         any(s in servicio_destino.lower() for s in self.SERVICIOS_UTI)
        
        puntaje_servicio_origen, desc_servicio = self._calcular_bonus_servicio_origen(
            paciente, servicio_origen, es_destino_uti
        )
        if desc_servicio:
            detalles.append(desc_servicio)
        
        # 3. IVC
        puntaje_ivc, detalles_ivc = self._calcular_ivc(paciente)
        detalles.extend(detalles_ivc)
        
        # 4. FRC
        puntaje_frc, detalles_frc = self._calcular_frc(paciente)
        detalles.extend(detalles_frc)
        
        # 5. Tiempo no lineal
        puntaje_tiempo, desc_tiempo = self._calcular_tiempo_no_lineal(paciente)
        if desc_tiempo:
            detalles.append(desc_tiempo)
        
        # Calcular total
        puntaje_total = (
            puntaje_tipo + 
            puntaje_servicio_origen +
            puntaje_ivc +
            puntaje_frc +
            puntaje_tiempo
        )
        
        # Extraer componentes individuales del IVC para el desglose
        complejidad = _normalizar_complejidad(paciente.complejidad_requerida)
        puntaje_complejidad = self.BONUS_COMPLEJIDAD_IVC.get(complejidad, 0)
        
        edad = paciente.edad or 0
        puntaje_edad = 0
        if edad >= 80:
            puntaje_edad = self.BONUS_EDAD_GRANULAR['muy_mayor']
        elif edad >= 70:
            puntaje_edad = self.BONUS_EDAD_GRANULAR['mayor']
        elif edad >= 60:
            puntaje_edad = self.BONUS_EDAD_GRANULAR['adulto_mayor']
        elif edad < 5:
            puntaje_edad = self.BONUS_EDAD_GRANULAR['infante']
        elif edad < 15:
            puntaje_edad = self.BONUS_EDAD_GRANULAR['nino']
        
        aislamiento = _normalizar_aislamiento(paciente.tipo_aislamiento)
        puntaje_aislamiento = self.BONUS_AISLAMIENTO_IVC.get(aislamiento, 0)
        
        return ExplicacionPrioridad(
            puntaje_total=round(puntaje_total, 2),
            puntaje_tipo=puntaje_tipo,
            puntaje_complejidad=puntaje_complejidad,
            puntaje_edad=puntaje_edad,
            puntaje_aislamiento=puntaje_aislamiento,
            puntaje_tiempo=round(puntaje_tiempo, 2),
            puntaje_servicio_origen=puntaje_servicio_origen,
            puntaje_boost_tiempo=0,  # Integrado en tiempo no lineal
            puntaje_ivc=round(puntaje_ivc, 2),
            puntaje_frc=round(puntaje_frc, 2),
            es_rescate=False,
            tipo_efectivo=tipo_efectivo,
            detalles=detalles
        )
    
    # ========================================
    # MÉTODOS DE GESTIÓN DE COLA (PRESERVADOS)
    # ========================================
    
    def agregar_a_cola(self, paciente: Paciente) -> float:
        """Agrega un paciente a la cola de espera."""
        prioridad = self.calcular_prioridad(paciente)
        cola = gestor_colas_global.obtener_cola(paciente.hospital_id)
        cola.agregar(paciente.id, prioridad)
        
        paciente.prioridad_calculada = prioridad
        self.session.add(paciente)
        self.session.commit()
        
        logger.info(f"Paciente {paciente.nombre} agregado a cola con prioridad {prioridad}")
        return prioridad
    
    def remover_de_cola(self, paciente: Paciente) -> bool:
        """Remueve un paciente de la cola de espera."""
        cola = gestor_colas_global.obtener_cola(paciente.hospital_id)
        return cola.remover(paciente.id)
    
    def actualizar_prioridad(self, paciente: Paciente) -> float:
        """Actualiza la prioridad de un paciente en la cola."""
        prioridad = self.calcular_prioridad(paciente)
        cola = gestor_colas_global.obtener_cola(paciente.hospital_id)
        cola.agregar(paciente.id, prioridad)
        
        paciente.prioridad_calculada = prioridad
        self.session.add(paciente)
        self.session.commit()
        
        return prioridad
    
    def recalcular_prioridades_para_destino(
        self, 
        hospital_id: str, 
        servicio_destino: str
    ) -> List[Tuple[Paciente, float, int]]:
        """
        Recalcula las prioridades considerando un servicio de destino específico.
        """
        cola = gestor_colas_global.obtener_cola(hospital_id)
        pacientes_ids = [pid for pid, _ in cola.obtener_todos_ordenados()]
        
        prioridades_recalculadas = []
        for paciente_id in pacientes_ids:
            paciente = self.paciente_repo.obtener_por_id(paciente_id)
            if paciente:
                prioridad = self.calcular_prioridad(paciente, servicio_destino)
                prioridades_recalculadas.append((paciente, prioridad))
        
        prioridades_recalculadas.sort(key=lambda x: x[1], reverse=True)
        
        resultado = []
        for posicion, (paciente, prioridad) in enumerate(prioridades_recalculadas, 1):
            resultado.append((paciente, prioridad, posicion))
        
        return resultado
    
    def obtener_lista_ordenada(self, hospital_id: str) -> List[Tuple[Paciente, float, int]]:
        """Obtiene la lista de espera ordenada por prioridad."""
        cola = gestor_colas_global.obtener_cola(hospital_id)
        ordenados = cola.obtener_todos_ordenados()
        
        resultado = []
        for posicion, (paciente_id, prioridad) in enumerate(ordenados, 1):
            paciente = self.paciente_repo.obtener_por_id(paciente_id)
            if paciente:
                resultado.append((paciente, prioridad, posicion))
        
        return resultado
    
    def obtener_siguiente_para_cama(
        self, 
        hospital_id: str, 
        servicio_destino: Optional[str] = None
    ) -> Optional[Tuple[Paciente, float]]:
        """
        Obtiene el siguiente paciente más prioritario para una cama.
        """
        if servicio_destino:
            lista = self.recalcular_prioridades_para_destino(hospital_id, servicio_destino)
            if lista:
                paciente, prioridad, _ = lista[0]
                return (paciente, prioridad)
            return None
        
        cola = gestor_colas_global.obtener_cola(hospital_id)
        paciente_id = cola.obtener_siguiente()
        
        if paciente_id:
            paciente = self.paciente_repo.obtener_por_id(paciente_id)
            if paciente:
                prioridad = cola.obtener_prioridad(paciente_id)
                return (paciente, prioridad or 0)
        
        return None
    
    def obtener_estadisticas_cola(self, hospital_id: str) -> dict:
        """
        Obtiene estadísticas de la cola de espera.
        
        Útil para dashboards y monitoreo.
        """
        cola = gestor_colas_global.obtener_cola(hospital_id)
        ordenados = cola.obtener_todos_ordenados()
        
        if not ordenados:
            return {
                'total_pacientes': 0,
                'por_tipo': {},
                'en_rescate': 0,
                'prioridad_promedio': 0,
                'prioridad_maxima': 0,
                'prioridad_minima': 0,
            }
        
        # Contar por tipo y rescates
        por_tipo = {'hospitalizado': 0, 'urgencia': 0, 'derivado': 0, 'ambulatorio': 0}
        en_rescate = 0
        prioridades = []
        
        for paciente_id, prioridad in ordenados:
            paciente = self.paciente_repo.obtener_por_id(paciente_id)
            if paciente:
                tipo_efectivo = self._obtener_tipo_efectivo(paciente)
                por_tipo[tipo_efectivo] = por_tipo.get(tipo_efectivo, 0) + 1
                prioridades.append(prioridad)
                
                if self._debe_activar_rescate(paciente):
                    en_rescate += 1
        
        return {
            'total_pacientes': len(ordenados),
            'por_tipo': por_tipo,
            'en_rescate': en_rescate,
            'prioridad_promedio': round(sum(prioridades) / len(prioridades), 2) if prioridades else 0,
            'prioridad_maxima': max(prioridades) if prioridades else 0,
            'prioridad_minima': min(prioridades) if prioridades else 0,
        }


# ============================================
# FUNCIONES DE INICIALIZACIÓN
# ============================================

def sincronizar_colas_iniciales(session: Session) -> None:
    """Sincroniza todas las colas con la base de datos al inicio."""
    hospitales = session.exec(select(Hospital)).all()
    for hospital in hospitales:
        gestor_colas_global.sincronizar_cola_con_db(hospital.id, session)
        logger.info(f"Cola sincronizada para hospital {hospital.nombre}")