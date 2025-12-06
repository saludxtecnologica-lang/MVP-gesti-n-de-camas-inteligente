"""
Sistema de Cola de Prioridad para Gestión de Camas Hospitalarias.
Implementa una cola de prioridad global por hospital usando max-heap.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Set, TYPE_CHECKING
import heapq

if TYPE_CHECKING:
    from models import Paciente

from models import TipoPacienteEnum, ComplejidadEnum, EdadCategoriaEnum, TipoAislamientoEnum


# ============================================
# CONSTANTES DE PRIORIDAD
# ============================================

SCORES_TIPO_PACIENTE = {
    TipoPacienteEnum.HOSPITALIZADO: 10,
    TipoPacienteEnum.URGENCIA: 8,
    TipoPacienteEnum.DERIVADO: 6,
    TipoPacienteEnum.AMBULATORIO: 4,
}

SCORES_COMPLEJIDAD = {
    ComplejidadEnum.ALTA: 3,
    ComplejidadEnum.MEDIA: 2,
    ComplejidadEnum.BAJA: 1,
    ComplejidadEnum.NINGUNA: 0,
}

UMBRALES_ESPERA = {
    TipoPacienteEnum.HOSPITALIZADO: 2,
    TipoPacienteEnum.URGENCIA: 4,
    TipoPacienteEnum.DERIVADO: 12,
    TipoPacienteEnum.AMBULATORIO: 48,
}

BOOST_EMBARAZADA = 10
BOOST_EDAD_VULNERABLE = 5
BOOST_AISLAMIENTO_INDIVIDUAL = 3
BOOST_DERIVADO_CON_OCUPACION = 4
BOOST_ADULTO_ESPERA_LARGA = 5


# ============================================
# DATACLASS PARA ENTRADA EN COLA
# ============================================

@dataclass(order=True)
class EntradaCola:
    """Entrada en la cola de prioridad con max-heap"""
    prioridad_negativa: float = field(compare=True)
    timestamp: datetime = field(compare=True)
    contador: int = field(compare=True)
    paciente_id: str = field(compare=False)
    hospital_id: str = field(compare=False)


# ============================================
# FUNCIONES DE CÁLCULO DE PRIORIDAD
# ============================================

def calcular_prioridad_paciente(paciente: "Paciente") -> float:
    """
    Calcula la prioridad de un paciente.
    Mayor valor = Mayor prioridad.
    """
    tipo_paciente = paciente.tipo_paciente
    if tipo_paciente is None:
        if paciente.cama_id:
            tipo_paciente = TipoPacienteEnum.HOSPITALIZADO
        elif paciente.derivacion_estado == "pendiente":
            tipo_paciente = TipoPacienteEnum.DERIVADO
        else:
            tipo_paciente = TipoPacienteEnum.URGENCIA
    
    score_tipo = SCORES_TIPO_PACIENTE.get(tipo_paciente, 5)
    
    complejidad = paciente.complejidad_requerida
    score_complejidad = SCORES_COMPLEJIDAD.get(complejidad, 1)
    
    tiempo_espera_min = paciente.tiempo_espera_min or 0
    tiempo_espera_horas = tiempo_espera_min / 60
    
    umbral = UMBRALES_ESPERA.get(tipo_paciente, 12)
    if tiempo_espera_horas > umbral:
        factor_exceso = (tiempo_espera_horas - umbral) / umbral
        score_tiempo = tiempo_espera_horas * (1 + factor_exceso * 0.5)
    else:
        score_tiempo = tiempo_espera_horas
    
    boosts = 0
    
    if paciente.es_embarazada:
        boosts += BOOST_EMBARAZADA
    
    if paciente.edad_categoria in [EdadCategoriaEnum.PEDIATRICO, EdadCategoriaEnum.ADULTO_MAYOR]:
        boosts += BOOST_EDAD_VULNERABLE
    
    if paciente.tipo_aislamiento in [
        TipoAislamientoEnum.AEREO,
        TipoAislamientoEnum.AMBIENTE_PROTEGIDO,
        TipoAislamientoEnum.ESPECIAL
    ]:
        boosts += BOOST_AISLAMIENTO_INDIVIDUAL
    
    if tipo_paciente == TipoPacienteEnum.DERIVADO:
        boosts += BOOST_DERIVADO_CON_OCUPACION
    
    if tiempo_espera_horas > 8 and paciente.edad_categoria == EdadCategoriaEnum.ADULTO:
        boosts += BOOST_ADULTO_ESPERA_LARGA
    
    prioridad = (score_tipo * 10) + (score_complejidad * 3) + (score_tiempo * 2) + boosts
    
    return round(prioridad, 2)


def explicar_prioridad(paciente: "Paciente") -> Dict:
    """Retorna un desglose detallado del cálculo de prioridad."""
    tipo_paciente = paciente.tipo_paciente or TipoPacienteEnum.URGENCIA
    score_tipo = SCORES_TIPO_PACIENTE.get(tipo_paciente, 5)
    
    complejidad = paciente.complejidad_requerida
    score_complejidad = SCORES_COMPLEJIDAD.get(complejidad, 1)
    
    tiempo_espera_min = paciente.tiempo_espera_min or 0
    tiempo_espera_horas = tiempo_espera_min / 60
    
    umbral = UMBRALES_ESPERA.get(tipo_paciente, 12)
    if tiempo_espera_horas > umbral:
        factor_exceso = (tiempo_espera_horas - umbral) / umbral
        score_tiempo = tiempo_espera_horas * (1 + factor_exceso * 0.5)
    else:
        score_tiempo = tiempo_espera_horas
    
    boosts_detalle = []
    boosts_total = 0
    
    if paciente.es_embarazada:
        boosts_detalle.append({"razon": "Embarazada", "valor": BOOST_EMBARAZADA})
        boosts_total += BOOST_EMBARAZADA
    
    if paciente.edad_categoria in [EdadCategoriaEnum.PEDIATRICO, EdadCategoriaEnum.ADULTO_MAYOR]:
        boosts_detalle.append({"razon": f"Edad vulnerable ({paciente.edad_categoria.value})", "valor": BOOST_EDAD_VULNERABLE})
        boosts_total += BOOST_EDAD_VULNERABLE
    
    if paciente.tipo_aislamiento in [TipoAislamientoEnum.AEREO, TipoAislamientoEnum.AMBIENTE_PROTEGIDO, TipoAislamientoEnum.ESPECIAL]:
        boosts_detalle.append({"razon": f"Aislamiento individual ({paciente.tipo_aislamiento.value})", "valor": BOOST_AISLAMIENTO_INDIVIDUAL})
        boosts_total += BOOST_AISLAMIENTO_INDIVIDUAL
    
    if tipo_paciente == TipoPacienteEnum.DERIVADO:
        boosts_detalle.append({"razon": "Paciente derivado", "valor": BOOST_DERIVADO_CON_OCUPACION})
        boosts_total += BOOST_DERIVADO_CON_OCUPACION
    
    if tiempo_espera_horas > 8 and paciente.edad_categoria == EdadCategoriaEnum.ADULTO:
        boosts_detalle.append({"razon": "Adulto con espera larga (>8h)", "valor": BOOST_ADULTO_ESPERA_LARGA})
        boosts_total += BOOST_ADULTO_ESPERA_LARGA
    
    prioridad_final = (score_tipo * 10) + (score_complejidad * 3) + (score_tiempo * 2) + boosts_total
    
    return {
        "paciente_id": paciente.id,
        "nombre": paciente.nombre,
        "tipo_paciente": tipo_paciente.value,
        "componentes": {
            "score_tipo": {"valor": score_tipo, "multiplicador": 10, "contribucion": score_tipo * 10},
            "score_complejidad": {"valor": score_complejidad, "multiplicador": 3, "contribucion": score_complejidad * 3},
            "score_tiempo": {"horas_espera": round(tiempo_espera_horas, 2), "multiplicador": 2, "contribucion": round(score_tiempo * 2, 2)},
            "boosts": {"detalle": boosts_detalle, "total": boosts_total}
        },
        "prioridad_final": round(prioridad_final, 2),
        "umbral_espera_horas": umbral,
        "excede_umbral": tiempo_espera_horas > umbral
    }


# ============================================
# GESTOR DE COLA DE PRIORIDAD POR HOSPITAL
# ============================================

class GestorColaPrioridad:
    """Cola de prioridad para un hospital específico."""
    
    def __init__(self, hospital_id: str):
        self.hospital_id = hospital_id
        self._heap: List[EntradaCola] = []
        self._pacientes_en_cola: Set[str] = set()
        self._contador = 0
    
    def agregar_paciente(self, paciente: "Paciente", session=None) -> float:
        """Agrega un paciente a la cola de prioridad."""
        if paciente.id in self._pacientes_en_cola:
            self.actualizar_prioridad(paciente, session)
            return paciente.prioridad_calculada
        
        prioridad = calcular_prioridad_paciente(paciente)
        
        entrada = EntradaCola(
            prioridad_negativa=-prioridad,
            timestamp=datetime.utcnow(),
            contador=self._contador,
            paciente_id=paciente.id,
            hospital_id=self.hospital_id
        )
        
        heapq.heappush(self._heap, entrada)
        self._pacientes_en_cola.add(paciente.id)
        self._contador += 1
        
        if session:
            paciente.en_lista_espera = True
            paciente.prioridad_calculada = prioridad
            if not paciente.timestamp_lista_espera:
                paciente.timestamp_lista_espera = datetime.utcnow()
            session.add(paciente)
        
        return prioridad
    
    def actualizar_prioridad(self, paciente: "Paciente", session=None) -> float:
        """Actualiza la prioridad de un paciente en la cola."""
        prioridad = calcular_prioridad_paciente(paciente)
        
        entrada = EntradaCola(
            prioridad_negativa=-prioridad,
            timestamp=datetime.utcnow(),
            contador=self._contador,
            paciente_id=paciente.id,
            hospital_id=self.hospital_id
        )
        
        heapq.heappush(self._heap, entrada)
        self._contador += 1
        
        if session:
            paciente.prioridad_calculada = prioridad
            session.add(paciente)
        
        return prioridad
    
    def obtener_siguiente(self) -> Optional[str]:
        """Obtiene el siguiente paciente más prioritario sin removerlo."""
        while self._heap:
            entrada = self._heap[0]
            if entrada.paciente_id in self._pacientes_en_cola:
                return entrada.paciente_id
            else:
                heapq.heappop(self._heap)
        return None
    
    def remover_paciente(self, paciente_id: str, session=None, paciente: "Paciente" = None) -> bool:
        """Remueve un paciente de la cola."""
        if paciente_id not in self._pacientes_en_cola:
            return False
        
        self._pacientes_en_cola.discard(paciente_id)
        
        if session and paciente:
            paciente.en_lista_espera = False
            paciente.prioridad_calculada = 0
            session.add(paciente)
        
        return True
    
    def eliminar_paciente(self, paciente_id: str, session=None, paciente: "Paciente" = None) -> bool:
        """Alias de remover_paciente."""
        return self.remover_paciente(paciente_id, session, paciente)
    
    def pop_siguiente(self) -> Optional[str]:
        """Obtiene Y REMUEVE el siguiente paciente más prioritario."""
        while self._heap:
            entrada = heapq.heappop(self._heap)
            if entrada.paciente_id in self._pacientes_en_cola:
                self._pacientes_en_cola.discard(entrada.paciente_id)
                return entrada.paciente_id
        return None
    
    def esta_en_cola(self, paciente_id: str) -> bool:
        return paciente_id in self._pacientes_en_cola
    
    def esta_vacio(self) -> bool:
        return len(self._pacientes_en_cola) == 0
    
    def obtener_lista_ordenada(self, session=None) -> List[Dict]:
        """Retorna la lista de pacientes ordenados por prioridad."""
        entradas_validas = [e for e in self._heap if e.paciente_id in self._pacientes_en_cola]
        entradas_ordenadas = sorted(entradas_validas, key=lambda x: x.prioridad_negativa)
        
        resultado = []
        for entrada in entradas_ordenadas:
            info = {
                "paciente_id": entrada.paciente_id,
                "prioridad": -entrada.prioridad_negativa,
                "timestamp": entrada.timestamp.isoformat(),
                "posicion": len(resultado) + 1
            }
            
            if session:
                from sqlmodel import select
                from models import Paciente
                paciente = session.get(Paciente, entrada.paciente_id)
                if paciente:
                    info.update({
                        "nombre": paciente.nombre,
                        "run": paciente.run,
                        "tipo_paciente": paciente.tipo_paciente.value if paciente.tipo_paciente else "desconocido",
                        "complejidad": paciente.complejidad_requerida.value,
                        "tiempo_espera_min": paciente.tiempo_espera_min,
                        "tiene_cama_actual": paciente.cama_id is not None,
                        "cama_actual_id": paciente.cama_id,
                        "estado_lista": paciente.estado_lista_espera.value if paciente.estado_lista_espera else "esperando",
                        "sexo": paciente.sexo.value,
                        "edad": paciente.edad,
                        "tipo_enfermedad": paciente.tipo_enfermedad.value,
                        "tipo_aislamiento": paciente.tipo_aislamiento.value
                    })
            
            resultado.append(info)
        
        return resultado
    
    def limpiar_cola(self):
        """Limpia completamente la cola."""
        self._heap = []
        self._pacientes_en_cola = set()
        self._contador = 0
    
    def tamano(self) -> int:
        return len(self._pacientes_en_cola)
    
    def __len__(self) -> int:
        return len(self._pacientes_en_cola)


# ============================================
# GESTOR GLOBAL DE COLAS
# ============================================

class GestorColasGlobal:
    """Singleton que mantiene las colas de prioridad de todos los hospitales."""
    _instance = None
    _colas: Dict[str, GestorColaPrioridad] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._colas = {}
        return cls._instance
    
    def obtener_cola(self, hospital_id: str) -> GestorColaPrioridad:
        """Obtiene o crea la cola de prioridad para un hospital."""
        if hospital_id not in self._colas:
            self._colas[hospital_id] = GestorColaPrioridad(hospital_id)
        return self._colas[hospital_id]
    
    def agregar_paciente(self, paciente: "Paciente", hospital_id: str, session=None) -> float:
        cola = self.obtener_cola(hospital_id)
        return cola.agregar_paciente(paciente, session)
    
    def remover_paciente(self, paciente_id: str, hospital_id: str, session=None, paciente=None) -> bool:
        cola = self.obtener_cola(hospital_id)
        return cola.remover_paciente(paciente_id, session, paciente)
    
    def eliminar_paciente(self, paciente_id: str, hospital_id: str, session=None, paciente=None) -> bool:
        return self.remover_paciente(paciente_id, hospital_id, session, paciente)
    
    def sincronizar_cola_con_db(self, hospital_id: str, session) -> int:
        """Sincroniza la cola con el estado actual de la base de datos."""
        from sqlmodel import select
        from models import Paciente
        
        cola = self.obtener_cola(hospital_id)
        cola.limpiar_cola()
        
        query = select(Paciente).where(Paciente.hospital_id == hospital_id)
        todos_pacientes = session.exec(query).all()
        
        for paciente in todos_pacientes:
            necesita_cola = (
                paciente.en_lista_espera or
                (paciente.en_espera and not paciente.cama_destino_id) or
                (paciente.requiere_nueva_cama and not paciente.cama_destino_id)
            )
            
            if necesita_cola:
                cola.agregar_paciente(paciente, session)
        
        session.commit()
        return len(cola)
    
    def limpiar_todas(self):
        """Limpia todas las colas."""
        for hospital_id, cola in self._colas.items():
            cola.limpiar_cola()


# Instancia global
gestor_colas_global = GestorColasGlobal()