"""
Servicio de Prioridad.
Gestiona el cálculo de prioridades y las colas de espera.

Sistema de Priorización v2.2:
- Hospitalizados tienen máxima prioridad (deben ser movidos primero)
- Dentro de hospitalizados: UCI > UTI > Aislamientos > otros servicios
- Para destino UTI: todos los servicios > UCI > otros orígenes
- Boost por tiempo de espera diferenciado según tipo de paciente

CORREGIDO v2.2:
- Detección de paciente hospitalizado por cama_id (no solo por tipo_paciente)
- Un paciente con cama asignada ES hospitalizado, sin importar su tipo_paciente original
- Manejo robusto de enums vs strings
"""
from typing import Optional, List, Dict, Tuple, Union
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
    """
    Normaliza el tipo de paciente a string lowercase para comparaciones.
    """
    if valor is None:
        return ""
    if hasattr(valor, 'value'):
        return str(valor.value).lower()
    return str(valor).lower()


def _normalizar_complejidad(valor: Union[ComplejidadEnum, str, None]) -> str:
    """
    Normaliza la complejidad a string lowercase para comparaciones.
    """
    if valor is None:
        return "ninguna"
    if hasattr(valor, 'value'):
        return str(valor.value).lower()
    return str(valor).lower()


def _normalizar_edad_categoria(valor: Union[EdadCategoriaEnum, str, None]) -> str:
    """
    Normaliza la categoría de edad a string lowercase.
    """
    if valor is None:
        return ""
    if hasattr(valor, 'value'):
        return str(valor.value).lower()
    return str(valor).lower()


def _normalizar_aislamiento(valor: Union[TipoAislamientoEnum, str, None]) -> str:
    """
    Normaliza el tipo de aislamiento a string lowercase.
    """
    if valor is None:
        return "ninguno"
    if hasattr(valor, 'value'):
        return str(valor.value).lower()
    return str(valor).lower()


@dataclass
class ExplicacionPrioridad:
    """Desglose del cálculo de prioridad."""
    puntaje_total: float
    puntaje_tipo: float
    puntaje_complejidad: float
    puntaje_edad: float
    puntaje_aislamiento: float
    puntaje_tiempo: float
    puntaje_servicio_origen: float = 0.0
    puntaje_boost_tiempo: float = 0.0
    detalles: List[str] = field(default_factory=list)


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


class PrioridadService:
    """
    Servicio para cálculo de prioridades v2.2.
    
    IMPORTANTE: Un paciente se considera HOSPITALIZADO si:
    - tiene cama_id asignada (ya está en una cama del hospital)
    - O su tipo_paciente es "hospitalizado"
    
    Esto es crucial porque un paciente que entró por urgencias pero ya tiene
    cama asignada, ES un paciente hospitalizado para efectos de priorización.
    
    Sistema de Priorización (orden de importancia):
    
    1. TIPO DE PACIENTE (Hospitalizados primero):
       - Hospitalizado (con cama): 200 (máxima prioridad - deben moverse primero)
       - Urgencia (sin cama): 100
       - Derivado: 80
       - Ambulatorio: 60
    
    2. SERVICIO DE ORIGEN (solo para hospitalizados con cama):
       - UCI: +60
       - UTI: +50
       - Aislamientos: +40
       - Otros servicios: +0
    
    3. COMPLEJIDAD REQUERIDA:
       - Alta: +50
       - Media: +30
       - Baja: +15
       - Ninguna: +0
    
    4. CATEGORÍA DE EDAD:
       - Adulto mayor: +20
       - Pediátrico: +15
       - Adulto: +0
    
    5. TIPO DE AISLAMIENTO:
       - Aéreo: +25
       - Ambiente protegido: +20
       - Especial: +15
       - Gotitas: +10
       - Contacto: +5
       - Ninguno: +0
    
    6. TIEMPO EN ESPERA (base + boost):
       - Base: 2 puntos por hora de espera
       - Boost Urgencias: +30 si >8 horas
       - Boost Ambulatorios: +40 si >4 días (5760 min)
       - Boost Derivados: +35 si >1 día (1440 min)
    
    7. CONDICIONES ESPECIALES:
       - Embarazada: +15
       - Casos especiales: +10
    """
    
    # ========================================
    # PESOS POR TIPO DE PACIENTE (usando strings normalizados)
    # Hospitalizados tienen máxima prioridad
    # ========================================
    PESO_TIPO = {
        'hospitalizado': 200,  # Máxima prioridad - mover primero
        'urgencia': 100,
        'derivado': 80,
        'ambulatorio': 60,
    }
    
    # ========================================
    # BONUS POR SERVICIO DE ORIGEN
    # Solo aplica a pacientes hospitalizados (con cama)
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
    # Cambia la priorización cuando el destino es UTI
    # ========================================
    BONUS_DESTINO_UTI = {
        'todos_servicios': 70,  # Pacientes de todos los servicios (no UCI)
        'uci': 60,              # Pacientes de UCI
        'otros_origenes': 0,    # Urgencias, derivados, ambulatorios sin cama
    }
    
    # ========================================
    # PESOS POR COMPLEJIDAD REQUERIDA (usando strings normalizados)
    # ========================================
    PESO_COMPLEJIDAD = {
        'alta': 50,
        'media': 30,
        'baja': 15,
        'ninguna': 0,
    }
    
    # ========================================
    # BONUS POR CATEGORÍA DE EDAD (usando strings normalizados)
    # ========================================
    BONUS_EDAD = {
        'adulto_mayor': 20,
        'adulto mayor': 20,
        'pediatrico': 15,
        'pediátrico': 15,
        'adulto': 0,
    }
    
    # ========================================
    # BONUS POR TIPO DE AISLAMIENTO (usando strings normalizados)
    # ========================================
    BONUS_AISLAMIENTO = {
        'aereo': 25,
        'aéreo': 25,
        'ambiente_protegido': 20,
        'ambiente protegido': 20,
        'especial': 15,
        'gotitas': 10,
        'contacto': 5,
        'ninguno': 0,
    }
    
    # ========================================
    # CONFIGURACIÓN DE TIEMPO
    # ========================================
    FACTOR_TIEMPO_POR_HORA = 2.0
    
    # Boost por tiempo de espera según tipo de paciente
    BOOST_TIEMPO_URGENCIA_HORAS = 8       # 8 horas
    BOOST_TIEMPO_URGENCIA_PUNTOS = 30
    
    BOOST_TIEMPO_AMBULATORIO_DIAS = 4     # 4 días
    BOOST_TIEMPO_AMBULATORIO_PUNTOS = 40
    
    BOOST_TIEMPO_DERIVADO_DIAS = 1        # 1 día
    BOOST_TIEMPO_DERIVADO_PUNTOS = 35
    
    def __init__(self, session: Session):
        self.session = session
        self.paciente_repo = PacienteRepository(session)
    
    def _es_paciente_hospitalizado(self, paciente: Paciente) -> bool:
        """
        Determina si un paciente debe ser tratado como HOSPITALIZADO.
        
        Un paciente ES hospitalizado si:
        1. Tiene cama_id asignada (ya está ocupando una cama)
        2. O su tipo_paciente es explícitamente "hospitalizado"
        
        Esto es CRÍTICO porque un paciente de urgencias que ya tiene cama
        asignada, ya está hospitalizado y debe tener prioridad máxima
        para ser movido.
        """
        # Si tiene cama asignada, ES hospitalizado
        if paciente.cama_id:
            return True
        
        # Si su tipo es hospitalizado
        tipo = _normalizar_tipo_paciente(paciente.tipo_paciente)
        if tipo == 'hospitalizado':
            return True
        
        return False
    
    def _obtener_tipo_efectivo(self, paciente: Paciente) -> str:
        """
        Obtiene el tipo de paciente EFECTIVO para priorización.
        
        Si el paciente tiene cama asignada, su tipo efectivo es "hospitalizado"
        sin importar su tipo_paciente original (urgencia, ambulatorio, etc.)
        """
        if self._es_paciente_hospitalizado(paciente):
            return 'hospitalizado'
        
        return _normalizar_tipo_paciente(paciente.tipo_paciente)
    
    def _clasificar_servicio_origen(self, servicio_nombre: Optional[str]) -> str:
        """
        Clasifica el servicio de origen del paciente.
        
        Returns:
            'uci', 'uti', 'aislamiento' o 'otros'
        """
        if not servicio_nombre:
            return 'otros'
        
        servicio_lower = servicio_nombre.lower().strip()
        
        # Verificar si es UCI
        if any(s in servicio_lower for s in self.SERVICIOS_UCI):
            return 'uci'
        
        # Verificar si es UTI
        if any(s in servicio_lower for s in self.SERVICIOS_UTI):
            return 'uti'
        
        # Verificar si es Aislamiento
        if any(s in servicio_lower for s in self.SERVICIOS_AISLAMIENTO):
            return 'aislamiento'
        
        return 'otros'
    
    def _obtener_servicio_origen(self, paciente: Paciente) -> Optional[str]:
        """
        Obtiene el nombre del servicio de origen del paciente.
        Busca en diferentes atributos según la estructura del modelo.
        """
        # Primero: campo explícito de origen
        if hasattr(paciente, 'origen_servicio_nombre') and paciente.origen_servicio_nombre:
            return paciente.origen_servicio_nombre
        
        if hasattr(paciente, 'servicio_origen') and paciente.servicio_origen:
            return paciente.servicio_origen
        
        # Segundo: obtener de la cama actual (relación cargada)
        if hasattr(paciente, 'cama') and paciente.cama:
            if hasattr(paciente.cama, 'sala') and paciente.cama.sala:
                if hasattr(paciente.cama.sala, 'servicio') and paciente.cama.sala.servicio:
                    return paciente.cama.sala.servicio.nombre
        
        # Tercero: cargar la cama desde la BD si tiene cama_id
        if paciente.cama_id:
            try:
                from app.models.cama import Cama
                cama = self.session.get(Cama, paciente.cama_id)
                if cama:
                    # Intentar cargar sala y servicio
                    if cama.sala_id:
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
        """
        Obtiene el nombre del servicio de destino del paciente.
        """
        if hasattr(paciente, 'servicio_destino') and paciente.servicio_destino:
            return paciente.servicio_destino
        
        if hasattr(paciente, 'servicio_destino_nombre') and paciente.servicio_destino_nombre:
            return paciente.servicio_destino_nombre
        
        return None
    
    def _es_destino_uti(self, paciente: Paciente) -> bool:
        """
        Verifica si el destino del paciente es UTI.
        """
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
        """
        Calcula el bonus por servicio de origen.
        
        Solo aplica a pacientes HOSPITALIZADOS (con cama asignada).
        
        Para destino UTI tiene lógica especial:
        - Pacientes de todos los servicios (no UCI) tienen mayor prioridad
        - Luego pacientes de UCI
        - Luego otros orígenes (urgencias, derivados, ambulatorios sin cama)
        
        Returns:
            Tuple de (puntaje, descripción)
        """
        # Solo los hospitalizados reciben bonus de servicio
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
        
        # Caso normal: solo hospitalizados reciben bonus
        if not es_hospitalizado:
            return (0, "")
        
        bonus = self.BONUS_SERVICIO_ORIGEN.get(tipo_servicio, 0)
        
        if bonus > 0:
            descripcion = f"Servicio origen {tipo_servicio.upper()}: +{bonus}"
        else:
            descripcion = f"Servicio origen ({servicio_origen or 'general'}): +0"
        
        return (bonus, descripcion)
    
    def _calcular_boost_tiempo(self, paciente: Paciente) -> Tuple[float, str]:
        """
        Calcula el boost adicional por tiempo de espera según el tipo de paciente ORIGINAL.
        
        Nota: Usa el tipo_paciente original (no el efectivo) porque el boost
        es para compensar a pacientes que llevan mucho tiempo esperando
        según su canal de entrada original.
        
        - Urgencias: +30 puntos si >8 horas de espera
        - Ambulatorios: +40 puntos si >4 días de espera
        - Derivados: +35 puntos si >1 día de espera
        
        Returns:
            Tuple de (puntaje, descripción)
        """
        if not paciente.timestamp_lista_espera:
            return (0, "")
        
        tiempo_espera_min = getattr(paciente, 'tiempo_espera_min', 0) or 0
        tipo_original = _normalizar_tipo_paciente(paciente.tipo_paciente)
        
        # Urgencias: boost si >8 horas (480 minutos)
        if tipo_original == 'urgencia':
            if tiempo_espera_min > (self.BOOST_TIEMPO_URGENCIA_HORAS * 60):
                return (self.BOOST_TIEMPO_URGENCIA_PUNTOS,
                        f"Boost urgencia >8h: +{self.BOOST_TIEMPO_URGENCIA_PUNTOS}")
        
        # Ambulatorios: boost si >4 días (5760 minutos)
        elif tipo_original == 'ambulatorio':
            if tiempo_espera_min > (self.BOOST_TIEMPO_AMBULATORIO_DIAS * 24 * 60):
                return (self.BOOST_TIEMPO_AMBULATORIO_PUNTOS,
                        f"Boost ambulatorio >4 días: +{self.BOOST_TIEMPO_AMBULATORIO_PUNTOS}")
        
        # Derivados: boost si >1 día (1440 minutos)
        elif tipo_original == 'derivado':
            if tiempo_espera_min > (self.BOOST_TIEMPO_DERIVADO_DIAS * 24 * 60):
                return (self.BOOST_TIEMPO_DERIVADO_PUNTOS,
                        f"Boost derivado >1 día: +{self.BOOST_TIEMPO_DERIVADO_PUNTOS}")
        
        return (0, "")
    
    def calcular_prioridad(
        self, 
        paciente: Paciente,
        servicio_destino: Optional[str] = None
    ) -> float:
        """
        Calcula la prioridad de un paciente.
        
        IMPORTANTE: Si el paciente tiene cama_id, se considera HOSPITALIZADO
        y recibe la prioridad máxima (200) + bonus por servicio de origen.
        
        Args:
            paciente: El paciente a evaluar
            servicio_destino: Servicio de destino (opcional, para lógica especial UTI)
        
        Returns:
            Puntaje de prioridad calculado
        """
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
        
        bonus_servicio, desc_servicio = self._calcular_bonus_servicio_origen(
            paciente, servicio_origen, es_destino_uti
        )
        puntaje += bonus_servicio
        
        logger.debug(f"  Servicio origen: {servicio_origen}, bonus: {bonus_servicio}")
        
        # 3. Puntaje por complejidad requerida
        complejidad = _normalizar_complejidad(paciente.complejidad_requerida)
        puntaje_complejidad = self.PESO_COMPLEJIDAD.get(complejidad, 0)
        puntaje += puntaje_complejidad
        
        # 4. Puntaje por categoría de edad
        edad_cat = _normalizar_edad_categoria(paciente.edad_categoria)
        puntaje_edad = self.BONUS_EDAD.get(edad_cat, 0)
        puntaje += puntaje_edad
        
        # 5. Puntaje por tipo de aislamiento
        aislamiento = _normalizar_aislamiento(paciente.tipo_aislamiento)
        puntaje_aislamiento = self.BONUS_AISLAMIENTO.get(aislamiento, 0)
        puntaje += puntaje_aislamiento
        
        # 6. Puntaje por tiempo en espera (base)
        puntaje_tiempo = 0.0
        if paciente.timestamp_lista_espera:
            tiempo_espera_min = getattr(paciente, 'tiempo_espera_min', 0) or 0
            horas_espera = tiempo_espera_min / 60.0
            puntaje_tiempo = horas_espera * self.FACTOR_TIEMPO_POR_HORA
            puntaje += puntaje_tiempo
        
        # 6b. Boost adicional por tiempo según tipo original
        boost_tiempo, _ = self._calcular_boost_tiempo(paciente)
        puntaje += boost_tiempo
        
        # 7. Condiciones especiales
        if paciente.es_embarazada:
            puntaje += 15
        
        if paciente.tiene_casos_especiales():
            puntaje += 10
        
        logger.info(
            f"Prioridad {paciente.nombre}: tipo_efectivo={tipo_efectivo}({puntaje_tipo}), "
            f"servicio={servicio_origen}({bonus_servicio}), complejidad={complejidad}({puntaje_complejidad}), "
            f"edad={edad_cat}({puntaje_edad}), aislamiento={aislamiento}({puntaje_aislamiento}), "
            f"tiempo={puntaje_tiempo:.1f}, boost={boost_tiempo}, "
            f"TOTAL={puntaje:.2f}"
        )
        
        return round(puntaje, 2)
    
    def explicar_prioridad(
        self, 
        paciente: Paciente,
        servicio_destino: Optional[str] = None
    ) -> ExplicacionPrioridad:
        """
        Calcula y explica la prioridad de un paciente con desglose detallado.
        
        Args:
            paciente: El paciente a evaluar
            servicio_destino: Servicio de destino (opcional)
        
        Returns:
            ExplicacionPrioridad con desglose completo
        """
        detalles = []
        
        # 1. Puntaje por tipo de paciente EFECTIVO
        tipo_efectivo = self._obtener_tipo_efectivo(paciente)
        tipo_original = _normalizar_tipo_paciente(paciente.tipo_paciente)
        puntaje_tipo = self.PESO_TIPO.get(tipo_efectivo, 0)
        
        if tipo_efectivo != tipo_original:
            detalles.append(f"Tipo efectivo: {tipo_efectivo} (original: {tipo_original}, tiene cama): +{puntaje_tipo}")
        else:
            detalles.append(f"Tipo {tipo_efectivo}: +{puntaje_tipo}")
        
        # 2. Puntaje por servicio de origen
        servicio_origen = self._obtener_servicio_origen(paciente)
        es_destino_uti = self._es_destino_uti(paciente) if not servicio_destino else \
                         any(s in servicio_destino.lower() for s in self.SERVICIOS_UTI)
        
        puntaje_servicio_origen, desc_servicio = self._calcular_bonus_servicio_origen(
            paciente, servicio_origen, es_destino_uti
        )
        if desc_servicio:
            detalles.append(desc_servicio)
        
        # 3. Puntaje por complejidad
        complejidad = _normalizar_complejidad(paciente.complejidad_requerida)
        puntaje_complejidad = self.PESO_COMPLEJIDAD.get(complejidad, 0)
        detalles.append(f"Complejidad {complejidad}: +{puntaje_complejidad}")
        
        # 4. Puntaje por edad
        edad_cat = _normalizar_edad_categoria(paciente.edad_categoria)
        puntaje_edad = self.BONUS_EDAD.get(edad_cat, 0)
        if puntaje_edad > 0:
            detalles.append(f"Categoría edad {edad_cat}: +{puntaje_edad}")
        
        # 5. Puntaje por aislamiento
        aislamiento = _normalizar_aislamiento(paciente.tipo_aislamiento)
        puntaje_aislamiento = self.BONUS_AISLAMIENTO.get(aislamiento, 0)
        if puntaje_aislamiento > 0:
            detalles.append(f"Aislamiento {aislamiento}: +{puntaje_aislamiento}")
        
        # 6. Puntaje por tiempo de espera
        puntaje_tiempo = 0.0
        if paciente.timestamp_lista_espera:
            tiempo_espera_min = getattr(paciente, 'tiempo_espera_min', 0) or 0
            horas = tiempo_espera_min / 60.0
            puntaje_tiempo = horas * self.FACTOR_TIEMPO_POR_HORA
            detalles.append(f"Tiempo espera ({tiempo_espera_min} min): +{puntaje_tiempo:.1f}")
        
        # 6b. Boost por tiempo según tipo original
        puntaje_boost_tiempo, desc_boost = self._calcular_boost_tiempo(paciente)
        if desc_boost:
            detalles.append(desc_boost)
        
        # 7. Extras (embarazo, casos especiales)
        extras = 0
        if paciente.es_embarazada:
            extras += 15
            detalles.append("Embarazada: +15")
        if paciente.tiene_casos_especiales():
            extras += 10
            detalles.append("Casos especiales: +10")
        
        # Calcular total
        puntaje_total = (
            puntaje_tipo + 
            puntaje_servicio_origen +
            puntaje_complejidad + 
            puntaje_edad + 
            puntaje_aislamiento + 
            puntaje_tiempo +
            puntaje_boost_tiempo +
            extras
        )
        
        return ExplicacionPrioridad(
            puntaje_total=round(puntaje_total, 2),
            puntaje_tipo=puntaje_tipo,
            puntaje_complejidad=puntaje_complejidad,
            puntaje_edad=puntaje_edad,
            puntaje_aislamiento=puntaje_aislamiento,
            puntaje_tiempo=round(puntaje_tiempo, 2),
            puntaje_servicio_origen=puntaje_servicio_origen,
            puntaje_boost_tiempo=puntaje_boost_tiempo,
            detalles=detalles
        )
    
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
        Útil cuando se libera una cama y se quiere ordenar por la lógica especial
        (ej: destino UTI tiene priorización diferente).
        
        Args:
            hospital_id: ID del hospital
            servicio_destino: Nombre del servicio de destino
        
        Returns:
            Lista ordenada de (paciente, prioridad, posición)
        """
        cola = gestor_colas_global.obtener_cola(hospital_id)
        pacientes_ids = [pid for pid, _ in cola.obtener_todos_ordenados()]
        
        # Recalcular prioridades con el servicio de destino
        prioridades_recalculadas = []
        for paciente_id in pacientes_ids:
            paciente = self.paciente_repo.obtener_por_id(paciente_id)
            if paciente:
                prioridad = self.calcular_prioridad(paciente, servicio_destino)
                prioridades_recalculadas.append((paciente, prioridad))
        
        # Ordenar por prioridad descendente
        prioridades_recalculadas.sort(key=lambda x: x[1], reverse=True)
        
        # Agregar posición
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
        
        Si se especifica servicio_destino, aplica la lógica especial
        (ej: para UTI, prioriza de forma diferente).
        
        Args:
            hospital_id: ID del hospital
            servicio_destino: Servicio de destino de la cama
        
        Returns:
            Tuple de (paciente, prioridad) o None
        """
        if servicio_destino:
            # Recalcular con lógica especial
            lista = self.recalcular_prioridades_para_destino(hospital_id, servicio_destino)
            if lista:
                paciente, prioridad, _ = lista[0]
                return (paciente, prioridad)
            return None
        
        # Obtener de la cola normal
        cola = gestor_colas_global.obtener_cola(hospital_id)
        paciente_id = cola.obtener_siguiente()
        
        if paciente_id:
            paciente = self.paciente_repo.obtener_por_id(paciente_id)
            if paciente:
                prioridad = cola.obtener_prioridad(paciente_id)
                return (paciente, prioridad or 0)
        
        return None


def sincronizar_colas_iniciales(session: Session) -> None:
    """Sincroniza todas las colas con la base de datos al inicio."""
    hospitales = session.exec(select(Hospital)).all()
    for hospital in hospitales:
        gestor_colas_global.sincronizar_cola_con_db(hospital.id, session)
        logger.info(f"Cola sincronizada para hospital {hospital.nombre}")