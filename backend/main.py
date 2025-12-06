"""
API Principal del Sistema de Gestión de Camas Hospitalarias.
FastAPI con WebSocket para actualizaciones en tiempo real.
"""

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime
import asyncio
import json
import os

from database import create_db_and_tables, get_session, get_session_direct
from models import (
    Hospital, Servicio, Sala, Cama, Paciente, ConfiguracionSistema, LogActividad,
    TipoPacienteEnum, EstadoCamaEnum, ComplejidadEnum, EdadCategoriaEnum,
    EstadoListaEsperaEnum, SexoEnum, TipoAislamientoEnum
)
from schemas import (
    PacienteCreate, PacienteUpdate, PacienteResponse,
    CamaResponse, CamaBloquearRequest,
    HospitalResponse, ServicioResponse, SalaResponse,
    ListaEsperaResponse, PacienteListaEsperaResponse,
    DerivacionRequest, DerivacionAccionRequest, PacienteDerivadoResponse,
    TrasladoManualRequest, IntercambioRequest,
    ConfiguracionResponse, ConfiguracionUpdate,
    EstadisticasHospitalResponse, EstadisticasGlobalesResponse,
    MessageResponse, ErrorResponse
)
from cola_prioridad import gestor_colas_global, calcular_prioridad_paciente, explicar_prioridad
from logic import (
    calcular_complejidad, buscar_cama_compatible, ejecutar_asignacion_automatica,
    completar_traslado, cancelar_asignacion, verificar_alta_sugerida,
    iniciar_alta, ejecutar_alta, cancelar_alta, procesar_camas_en_limpieza,
    actualizar_sexo_sala_si_vacia, asignar_cama_a_paciente
)
from init_data import inicializar_datos

# Crear aplicación
app = FastAPI(
    title="Sistema de Gestión de Camas Hospitalarias",
    description="MVP de gestión automatizada de camas hospitalarias",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directorio para archivos subidos
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ============================================
# WEBSOCKET MANAGER
# ============================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()


# ============================================
# EVENTOS DE INICIO
# ============================================

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    session = get_session_direct()
    inicializar_datos(session)
    
    # Sincronizar colas con DB
    hospitales = session.exec(select(Hospital)).all()
    for hospital in hospitales:
        gestor_colas_global.sincronizar_cola_con_db(hospital.id, session)
    
    session.close()
    
    # Iniciar tarea de procesamiento de camas
    asyncio.create_task(proceso_automatico())


async def proceso_automatico():
    """Proceso en segundo plano para asignación automática y limpieza."""
    while True:
        try:
            session = get_session_direct()
            
            # Verificar modo
            config = session.exec(select(ConfiguracionSistema)).first()
            
            if not config or not config.modo_manual:
                # Procesar camas en limpieza
                camas_liberadas = procesar_camas_en_limpieza(
                    session, 
                    config.tiempo_limpieza_segundos if config else 60
                )
                
                # Ejecutar asignación automática
                hospitales = session.exec(select(Hospital)).all()
                for hospital in hospitales:
                    asignaciones = ejecutar_asignacion_automatica(hospital.id, session)
                    
                    if asignaciones:
                        await manager.broadcast({
                            "tipo": "asignaciones",
                            "hospital_id": hospital.id,
                            "asignaciones": asignaciones
                        })
                
                if camas_liberadas:
                    await manager.broadcast({
                        "tipo": "camas_liberadas",
                        "camas": camas_liberadas
                    })
            
            session.close()
        except Exception as e:
            print(f"Error en proceso automático: {e}")
        
        await asyncio.sleep(5)  # Ejecutar cada 5 segundos


# ============================================
# WEBSOCKET ENDPOINT
# ============================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Procesar mensajes del cliente si es necesario
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ============================================
# ENDPOINTS DE HOSPITALES
# ============================================

@app.get("/api/hospitales", response_model=List[HospitalResponse])
def obtener_hospitales(session: Session = Depends(get_session)):
    """Obtiene todos los hospitales con estadísticas."""
    hospitales = session.exec(select(Hospital)).all()
    resultado = []
    
    for hospital in hospitales:
        # Contar camas
        query_camas = select(Cama).join(Sala).join(Servicio).where(
            Servicio.hospital_id == hospital.id
        )
        camas = session.exec(query_camas).all()
        
        total_camas = len(camas)
        camas_libres = len([c for c in camas if c.estado == EstadoCamaEnum.LIBRE])
        camas_ocupadas = len([c for c in camas if c.estado in [
            EstadoCamaEnum.OCUPADA, EstadoCamaEnum.CAMA_EN_ESPERA,
            EstadoCamaEnum.TRASLADO_SALIENTE, EstadoCamaEnum.TRASLADO_CONFIRMADO,
            EstadoCamaEnum.ALTA_SUGERIDA, EstadoCamaEnum.CAMA_ALTA,
            EstadoCamaEnum.ESPERA_DERIVACION, EstadoCamaEnum.DERIVACION_CONFIRMADA
        ]])
        
        # Contar pacientes en espera
        cola = gestor_colas_global.obtener_cola(hospital.id)
        pacientes_espera = cola.tamano()
        
        # Contar derivados pendientes
        query_derivados = select(Paciente).where(
            Paciente.derivacion_hospital_destino_id == hospital.id,
            Paciente.derivacion_estado == "pendiente"
        )
        derivados = len(session.exec(query_derivados).all())
        
        resultado.append(HospitalResponse(
            id=hospital.id,
            nombre=hospital.nombre,
            codigo=hospital.codigo,
            es_central=hospital.es_central,
            total_camas=total_camas,
            camas_libres=camas_libres,
            camas_ocupadas=camas_ocupadas,
            pacientes_en_espera=pacientes_espera,
            pacientes_derivados=derivados
        ))
    
    return resultado


@app.get("/api/hospitales/{hospital_id}", response_model=HospitalResponse)
def obtener_hospital(hospital_id: str, session: Session = Depends(get_session)):
    """Obtiene un hospital específico."""
    hospital = session.get(Hospital, hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital no encontrado")
    
    # Similar al anterior pero para un solo hospital
    query_camas = select(Cama).join(Sala).join(Servicio).where(
        Servicio.hospital_id == hospital.id
    )
    camas = session.exec(query_camas).all()
    
    return HospitalResponse(
        id=hospital.id,
        nombre=hospital.nombre,
        codigo=hospital.codigo,
        es_central=hospital.es_central,
        total_camas=len(camas),
        camas_libres=len([c for c in camas if c.estado == EstadoCamaEnum.LIBRE]),
        camas_ocupadas=len([c for c in camas if c.estado != EstadoCamaEnum.LIBRE]),
        pacientes_en_espera=gestor_colas_global.obtener_cola(hospital.id).tamano(),
        pacientes_derivados=0
    )


# ============================================
# ENDPOINTS DE SERVICIOS Y CAMAS
# ============================================

@app.get("/api/hospitales/{hospital_id}/servicios", response_model=List[ServicioResponse])
def obtener_servicios(hospital_id: str, session: Session = Depends(get_session)):
    """Obtiene los servicios de un hospital."""
    query = select(Servicio).where(Servicio.hospital_id == hospital_id)
    servicios = session.exec(query).all()
    
    resultado = []
    for servicio in servicios:
        query_camas = select(Cama).join(Sala).where(Sala.servicio_id == servicio.id)
        camas = session.exec(query_camas).all()
        
        resultado.append(ServicioResponse(
            id=servicio.id,
            nombre=servicio.nombre,
            codigo=servicio.codigo,
            tipo=servicio.tipo,
            hospital_id=servicio.hospital_id,
            total_camas=len(camas),
            camas_libres=len([c for c in camas if c.estado == EstadoCamaEnum.LIBRE])
        ))
    
    return resultado


@app.get("/api/hospitales/{hospital_id}/camas", response_model=List[CamaResponse])
def obtener_camas_hospital(hospital_id: str, session: Session = Depends(get_session)):
    """Obtiene todas las camas de un hospital con información completa."""
    query = select(Cama).join(Sala).join(Servicio).where(
        Servicio.hospital_id == hospital_id
    ).order_by(Cama.identificador)
    camas = session.exec(query).all()
    
    resultado = []
    for cama in camas:
        sala = cama.sala
        servicio = sala.servicio
        
        # Obtener paciente actual
        paciente = None
        if cama.estado not in [EstadoCamaEnum.LIBRE, EstadoCamaEnum.BLOQUEADA, EstadoCamaEnum.EN_LIMPIEZA, EstadoCamaEnum.TRASLADO_ENTRANTE]:
            query_paciente = select(Paciente).where(Paciente.cama_id == cama.id)
            paciente_db = session.exec(query_paciente).first()
            if paciente_db:
                paciente = crear_paciente_response(paciente_db)
        
        # Obtener paciente entrante
        paciente_entrante = None
        if cama.estado == EstadoCamaEnum.TRASLADO_ENTRANTE:
            query_entrante = select(Paciente).where(Paciente.cama_destino_id == cama.id)
            paciente_entrante_db = session.exec(query_entrante).first()
            if paciente_entrante_db:
                paciente_entrante = crear_paciente_response(paciente_entrante_db)
        
        resultado.append(CamaResponse(
            id=cama.id,
            numero=cama.numero,
            letra=cama.letra,
            identificador=cama.identificador,
            estado=cama.estado,
            mensaje_estado=cama.mensaje_estado,
            cama_asignada_destino=cama.cama_asignada_destino,
            sala_id=cama.sala_id,
            servicio_nombre=servicio.nombre,
            servicio_tipo=servicio.tipo,
            sala_es_individual=sala.es_individual,
            sala_sexo_asignado=sala.sexo_asignado,
            paciente=paciente,
            paciente_entrante=paciente_entrante
        ))
    
    return resultado


@app.post("/api/camas/{cama_id}/bloquear", response_model=MessageResponse)
async def bloquear_cama(
    cama_id: str, 
    request: CamaBloquearRequest,
    session: Session = Depends(get_session)
):
    """Bloquea o desbloquea una cama."""
    cama = session.get(Cama, cama_id)
    if not cama:
        raise HTTPException(status_code=404, detail="Cama no encontrada")
    
    if request.bloquear:
        if cama.estado != EstadoCamaEnum.LIBRE:
            raise HTTPException(status_code=400, detail="Solo se pueden bloquear camas libres")
        cama.estado = EstadoCamaEnum.BLOQUEADA
        cama.mensaje_estado = "Bloqueada"
    else:
        if cama.estado != EstadoCamaEnum.BLOQUEADA:
            raise HTTPException(status_code=400, detail="La cama no está bloqueada")
        cama.estado = EstadoCamaEnum.LIBRE
        cama.mensaje_estado = None
    
    session.add(cama)
    session.commit()
    
    await manager.broadcast({"tipo": "cama_actualizada", "cama_id": cama_id})
    
    return MessageResponse(
        success=True,
        message=f"Cama {'bloqueada' if request.bloquear else 'desbloqueada'} correctamente"
    )


# ============================================
# ENDPOINTS DE PACIENTES
# ============================================

def determinar_edad_categoria(edad: int) -> EdadCategoriaEnum:
    """Determina la categoría de edad."""
    if edad < 15:
        return EdadCategoriaEnum.PEDIATRICO
    elif edad < 60:
        return EdadCategoriaEnum.ADULTO
    else:
        return EdadCategoriaEnum.ADULTO_MAYOR


def crear_paciente_response(paciente: Paciente) -> PacienteResponse:
    """Crea un PacienteResponse a partir de un modelo Paciente."""
    return PacienteResponse(
        id=paciente.id,
        nombre=paciente.nombre,
        run=paciente.run,
        sexo=paciente.sexo,
        edad=paciente.edad,
        edad_categoria=paciente.edad_categoria,
        es_embarazada=paciente.es_embarazada,
        diagnostico=paciente.diagnostico,
        tipo_enfermedad=paciente.tipo_enfermedad,
        tipo_aislamiento=paciente.tipo_aislamiento,
        notas_adicionales=paciente.notas_adicionales,
        complejidad_requerida=paciente.complejidad_requerida,
        tipo_paciente=paciente.tipo_paciente,
        hospital_id=paciente.hospital_id,
        cama_id=paciente.cama_id,
        cama_destino_id=paciente.cama_destino_id,
        en_lista_espera=paciente.en_lista_espera,
        estado_lista_espera=paciente.estado_lista_espera,
        prioridad_calculada=paciente.prioridad_calculada,
        tiempo_espera_min=paciente.tiempo_espera_min,
        requiere_nueva_cama=paciente.requiere_nueva_cama,
        derivacion_hospital_destino_id=paciente.derivacion_hospital_destino_id,
        derivacion_motivo=paciente.derivacion_motivo,
        derivacion_estado=paciente.derivacion_estado,
        alta_solicitada=paciente.alta_solicitada,
        created_at=paciente.created_at,
        updated_at=paciente.updated_at,
        requerimientos_no_definen=json.loads(paciente.requerimientos_no_definen or "[]"),
        requerimientos_baja=json.loads(paciente.requerimientos_baja or "[]"),
        requerimientos_uti=json.loads(paciente.requerimientos_uti or "[]"),
        requerimientos_uci=json.loads(paciente.requerimientos_uci or "[]"),
        casos_especiales=json.loads(paciente.casos_especiales or "[]"),
        motivo_observacion=paciente.motivo_observacion,
        justificacion_observacion=paciente.justificacion_observacion,
        procedimiento_invasivo=paciente.procedimiento_invasivo
    )


@app.post("/api/pacientes", response_model=PacienteResponse)
async def registrar_paciente(
    data: PacienteCreate,
    session: Session = Depends(get_session)
):
    """Registra un nuevo paciente."""
    
    # Determinar categoría de edad
    edad_categoria = determinar_edad_categoria(data.edad)
    
    # Crear paciente
    paciente = Paciente(
        nombre=data.nombre,
        run=data.run,
        sexo=data.sexo,
        edad=data.edad,
        edad_categoria=edad_categoria,
        es_embarazada=data.es_embarazada if data.sexo == SexoEnum.MUJER else False,
        diagnostico=data.diagnostico,
        tipo_enfermedad=data.tipo_enfermedad,
        tipo_aislamiento=data.tipo_aislamiento,
        notas_adicionales=data.notas_adicionales,
        tipo_paciente=data.tipo_paciente,
        hospital_id=data.hospital_id,
        requerimientos_no_definen=json.dumps(data.requerimientos_no_definen),
        requerimientos_baja=json.dumps(data.requerimientos_baja),
        requerimientos_uti=json.dumps(data.requerimientos_uti),
        requerimientos_uci=json.dumps(data.requerimientos_uci),
        casos_especiales=json.dumps(data.casos_especiales),
        motivo_observacion=data.motivo_observacion,
        justificacion_observacion=data.justificacion_observacion,
        procedimiento_invasivo=data.procedimiento_invasivo,
        alta_motivo=data.alta_motivo
    )
    
    # Calcular complejidad
    paciente.complejidad_requerida = calcular_complejidad(paciente)
    
    # Verificar caso especial pediátrico
    if edad_categoria == EdadCategoriaEnum.PEDIATRICO:
        if paciente.complejidad_requerida in [ComplejidadEnum.ALTA, ComplejidadEnum.MEDIA]:
            raise HTTPException(
                status_code=400,
                detail=f"Sin disponibilidad de cama {'UCI' if paciente.complejidad_requerida == ComplejidadEnum.ALTA else 'UTI'} pediátrica en este hospital"
            )
        if paciente.tipo_aislamiento in [TipoAislamientoEnum.AEREO, TipoAislamientoEnum.AMBIENTE_PROTEGIDO, TipoAislamientoEnum.ESPECIAL]:
            raise HTTPException(
                status_code=400,
                detail="Sin disponibilidad de aislamiento individual pediátrico en este hospital"
            )
    
    session.add(paciente)
    session.commit()
    session.refresh(paciente)
    
    # Manejar derivación
    if data.derivacion_hospital_destino_id:
        paciente.derivacion_hospital_destino_id = data.derivacion_hospital_destino_id
        paciente.derivacion_motivo = data.derivacion_motivo
        paciente.derivacion_estado = "pendiente"
        session.add(paciente)
        session.commit()
        
        await manager.broadcast({
            "tipo": "nueva_derivacion",
            "hospital_destino_id": data.derivacion_hospital_destino_id,
            "paciente_id": paciente.id
        })
    elif not data.alta_solicitada:
        # Agregar a lista de espera
        paciente.en_lista_espera = True
        paciente.timestamp_lista_espera = datetime.utcnow()
        paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
        session.add(paciente)
        session.commit()
        
        gestor_colas_global.agregar_paciente(paciente, paciente.hospital_id, session)
        
        await manager.broadcast({
            "tipo": "paciente_en_espera",
            "hospital_id": paciente.hospital_id,
            "paciente_id": paciente.id
        })
    
    return crear_paciente_response(paciente)


@app.get("/api/pacientes/{paciente_id}", response_model=PacienteResponse)
def obtener_paciente(paciente_id: str, session: Session = Depends(get_session)):
    """Obtiene un paciente específico."""
    paciente = session.get(Paciente, paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    return crear_paciente_response(paciente)


@app.put("/api/pacientes/{paciente_id}", response_model=PacienteResponse)
async def actualizar_paciente(
    paciente_id: str,
    data: PacienteUpdate,
    session: Session = Depends(get_session)
):
    """Actualiza (reevalúa) un paciente."""
    paciente = session.get(Paciente, paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    cama_actual = session.get(Cama, paciente.cama_id) if paciente.cama_id else None
    complejidad_anterior = paciente.complejidad_requerida
    
    # Actualizar campos
    if data.diagnostico is not None:
        paciente.diagnostico = data.diagnostico
    if data.tipo_enfermedad is not None:
        paciente.tipo_enfermedad = data.tipo_enfermedad
    if data.tipo_aislamiento is not None:
        paciente.tipo_aislamiento = data.tipo_aislamiento
    if data.notas_adicionales is not None:
        paciente.notas_adicionales = data.notas_adicionales
    if data.es_embarazada is not None and paciente.sexo == SexoEnum.MUJER:
        paciente.es_embarazada = data.es_embarazada
    if data.requerimientos_no_definen is not None:
        paciente.requerimientos_no_definen = json.dumps(data.requerimientos_no_definen)
    if data.requerimientos_baja is not None:
        paciente.requerimientos_baja = json.dumps(data.requerimientos_baja)
    if data.requerimientos_uti is not None:
        paciente.requerimientos_uti = json.dumps(data.requerimientos_uti)
    if data.requerimientos_uci is not None:
        paciente.requerimientos_uci = json.dumps(data.requerimientos_uci)
    if data.casos_especiales is not None:
        paciente.casos_especiales = json.dumps(data.casos_especiales)
    if data.motivo_observacion is not None:
        paciente.motivo_observacion = data.motivo_observacion
    if data.justificacion_observacion is not None:
        paciente.justificacion_observacion = data.justificacion_observacion
    if data.procedimiento_invasivo is not None:
        paciente.procedimiento_invasivo = data.procedimiento_invasivo
    
    paciente.updated_at = datetime.utcnow()
    
    # Recalcular complejidad
    paciente.complejidad_requerida = calcular_complejidad(paciente)
    
    # Manejar derivación (prioridad sobre otros cambios)
    if data.derivacion_hospital_destino_id:
        paciente.derivacion_hospital_destino_id = data.derivacion_hospital_destino_id
        paciente.derivacion_motivo = data.derivacion_motivo
        paciente.derivacion_estado = "pendiente"
        
        if cama_actual:
            cama_actual.estado = EstadoCamaEnum.ESPERA_DERIVACION
            cama_actual.mensaje_estado = "Esperando confirmación de derivación"
            session.add(cama_actual)
        
        session.add(paciente)
        session.commit()
        
        await manager.broadcast({
            "tipo": "derivacion_solicitada",
            "hospital_destino_id": data.derivacion_hospital_destino_id,
            "paciente_id": paciente.id
        })
        
        return crear_paciente_response(paciente)
    
    # Manejar alta
    if data.alta_solicitada:
        paciente.alta_solicitada = True
        paciente.alta_motivo = data.alta_motivo
        
        if cama_actual:
            cama_actual.estado = EstadoCamaEnum.CAMA_ALTA
            cama_actual.mensaje_estado = "Alta pendiente"
            session.add(cama_actual)
        
        session.add(paciente)
        session.commit()
        
        await manager.broadcast({
            "tipo": "alta_solicitada",
            "paciente_id": paciente.id,
            "cama_id": paciente.cama_id
        })
        
        return crear_paciente_response(paciente)
    
    # Verificar si necesita nueva cama
    complejidad_nueva = paciente.complejidad_requerida
    
    if cama_actual:
        # Verificar si la cama actual sigue siendo compatible
        from logic import cama_es_compatible
        es_compatible, razon = cama_es_compatible(cama_actual, paciente, session)
        
        if not es_compatible or complejidad_anterior != complejidad_nueva:
            # Necesita nueva cama
            paciente.requiere_nueva_cama = True
            cama_actual.estado = EstadoCamaEnum.CAMA_EN_ESPERA
            cama_actual.mensaje_estado = "Paciente requiere nueva cama"
            session.add(cama_actual)
        else:
            # Verificar si debería sugerir alta
            if verificar_alta_sugerida(paciente):
                cama_actual.estado = EstadoCamaEnum.ALTA_SUGERIDA
                cama_actual.mensaje_estado = "Alta sugerida"
                session.add(cama_actual)
            else:
                cama_actual.estado = EstadoCamaEnum.OCUPADA
                cama_actual.mensaje_estado = None
                session.add(cama_actual)
    
    session.add(paciente)
    session.commit()
    
    await manager.broadcast({
        "tipo": "paciente_actualizado",
        "paciente_id": paciente.id,
        "hospital_id": paciente.hospital_id
    })
    
    return crear_paciente_response(paciente)


@app.get("/api/pacientes/{paciente_id}/prioridad")
def obtener_prioridad_paciente(paciente_id: str, session: Session = Depends(get_session)):
    """Obtiene el desglose de prioridad de un paciente."""
    paciente = session.get(Paciente, paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    return explicar_prioridad(paciente)


# ============================================
# ENDPOINTS DE LISTA DE ESPERA
# ============================================

@app.get("/api/hospitales/{hospital_id}/lista-espera", response_model=ListaEsperaResponse)
def obtener_lista_espera(hospital_id: str, session: Session = Depends(get_session)):
    """Obtiene la lista de espera de un hospital."""
    cola = gestor_colas_global.obtener_cola(hospital_id)
    lista = cola.obtener_lista_ordenada(session)
    
    pacientes = []
    for item in lista:
        pacientes.append(PacienteListaEsperaResponse(
            paciente_id=item["paciente_id"],
            nombre=item.get("nombre", ""),
            run=item.get("run", ""),
            prioridad=item["prioridad"],
            posicion=item["posicion"],
            tiempo_espera_min=item.get("tiempo_espera_min", 0),
            estado_lista=item.get("estado_lista", "esperando"),
            tipo_paciente=item.get("tipo_paciente", "urgencia"),
            complejidad=item.get("complejidad", "baja"),
            sexo=item.get("sexo", "hombre"),
            edad=item.get("edad", 0),
            tipo_enfermedad=item.get("tipo_enfermedad", "medica"),
            tipo_aislamiento=item.get("tipo_aislamiento", "ninguno"),
            tiene_cama_actual=item.get("tiene_cama_actual", False),
            cama_actual_id=item.get("cama_actual_id"),
            timestamp=item["timestamp"]
        ))
    
    return ListaEsperaResponse(
        hospital_id=hospital_id,
        total_pacientes=len(pacientes),
        pacientes=pacientes
    )


@app.post("/api/pacientes/{paciente_id}/buscar-cama", response_model=MessageResponse)
async def buscar_nueva_cama(paciente_id: str, session: Session = Depends(get_session)):
    """Inicia la búsqueda de nueva cama para un paciente hospitalizado."""
    paciente = session.get(Paciente, paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    if not paciente.cama_id:
        raise HTTPException(status_code=400, detail="El paciente no tiene cama asignada")
    
    # Actualizar cama actual
    cama_actual = session.get(Cama, paciente.cama_id)
    if cama_actual:
        cama_actual.estado = EstadoCamaEnum.TRASLADO_SALIENTE
        cama_actual.mensaje_estado = "En espera de confirmación"
        session.add(cama_actual)
    
    # Agregar a lista de espera
    paciente.en_lista_espera = True
    paciente.timestamp_lista_espera = datetime.utcnow()
    paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
    paciente.tipo_paciente = TipoPacienteEnum.HOSPITALIZADO
    session.add(paciente)
    session.commit()
    
    gestor_colas_global.agregar_paciente(paciente, paciente.hospital_id, session)
    
    await manager.broadcast({
        "tipo": "paciente_busca_cama",
        "hospital_id": paciente.hospital_id,
        "paciente_id": paciente.id
    })
    
    return MessageResponse(
        success=True,
        message="Paciente agregado a lista de búsqueda de cama"
    )


@app.post("/api/pacientes/{paciente_id}/cancelar-busqueda", response_model=MessageResponse)
async def cancelar_busqueda_cama(paciente_id: str, session: Session = Depends(get_session)):
    """Cancela la búsqueda de cama y saca al paciente de la lista."""
    paciente = session.get(Paciente, paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    if not paciente.en_lista_espera:
        raise HTTPException(status_code=400, detail="El paciente no está en lista de espera")
    
    # Si tiene cama destino asignada, liberarla
    if paciente.cama_destino_id:
        cama_destino = session.get(Cama, paciente.cama_destino_id)
        if cama_destino:
            cama_destino.estado = EstadoCamaEnum.LIBRE
            cama_destino.mensaje_estado = None
            session.add(cama_destino)
    
    # Si tenía cama original
    if paciente.cama_id:
        cama_actual = session.get(Cama, paciente.cama_id)
        if cama_actual:
            cama_actual.estado = EstadoCamaEnum.CAMA_EN_ESPERA
            cama_actual.cama_asignada_destino = None
            session.add(cama_actual)
        
        # Remover de cola pero mantener en cama
        gestor_colas_global.remover_paciente(paciente.id, paciente.hospital_id, session, paciente)
        paciente.cama_destino_id = None
        paciente.en_lista_espera = False
        paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
        session.add(paciente)
    else:
        # No tiene cama, eliminar del sistema
        gestor_colas_global.remover_paciente(paciente.id, paciente.hospital_id, session, paciente)
        session.delete(paciente)
    
    session.commit()
    
    await manager.broadcast({
        "tipo": "busqueda_cancelada",
        "paciente_id": paciente_id
    })
    
    return MessageResponse(
        success=True,
        message="Búsqueda cancelada correctamente"
    )


# ============================================
# ENDPOINTS DE TRASLADOS
# ============================================

@app.post("/api/traslados/completar/{paciente_id}", response_model=MessageResponse)
async def completar_traslado_endpoint(paciente_id: str, session: Session = Depends(get_session)):
    """Completa el traslado de un paciente a su cama asignada."""
    resultado = completar_traslado(paciente_id, session)
    
    if "error" in resultado:
        raise HTTPException(status_code=400, detail=resultado["error"])
    
    await manager.broadcast({
        "tipo": "traslado_completado",
        "paciente_id": paciente_id,
        "cama_id": resultado.get("cama_nueva_id")
    })
    
    return MessageResponse(
        success=True,
        message="Traslado completado correctamente",
        data=resultado
    )


@app.post("/api/traslados/cancelar/{paciente_id}", response_model=MessageResponse)
async def cancelar_traslado_endpoint(paciente_id: str, session: Session = Depends(get_session)):
    """Cancela la asignación de cama de un paciente."""
    resultado = cancelar_asignacion(paciente_id, session)
    
    if "error" in resultado:
        raise HTTPException(status_code=400, detail=resultado["error"])
    
    await manager.broadcast({
        "tipo": "traslado_cancelado",
        "paciente_id": paciente_id
    })
    
    return MessageResponse(
        success=True,
        message="Asignación cancelada correctamente"
    )


# ============================================
# ENDPOINTS DE DERIVACIONES
# ============================================

@app.get("/api/hospitales/{hospital_id}/derivados", response_model=List[PacienteDerivadoResponse])
def obtener_derivados(hospital_id: str, session: Session = Depends(get_session)):
    """Obtiene la lista de pacientes derivados pendientes de un hospital."""
    query = select(Paciente).where(
        Paciente.derivacion_hospital_destino_id == hospital_id,
        Paciente.derivacion_estado == "pendiente"
    )
    pacientes = session.exec(query).all()
    
    resultado = []
    for paciente in pacientes:
        hospital_origen = session.get(Hospital, paciente.hospital_id)
        
        # Calcular tiempo en lista
        tiempo_min = 0
        if paciente.updated_at:
            delta = datetime.utcnow() - paciente.updated_at
            tiempo_min = int(delta.total_seconds() / 60)
        
        resultado.append(PacienteDerivadoResponse(
            paciente_id=paciente.id,
            nombre=paciente.nombre,
            run=paciente.run,
            prioridad=calcular_prioridad_paciente(paciente),
            tiempo_en_lista_min=tiempo_min,
            hospital_origen_id=paciente.hospital_id,
            hospital_origen_nombre=hospital_origen.nombre if hospital_origen else "",
            motivo_derivacion=paciente.derivacion_motivo or "",
            tipo_paciente=paciente.tipo_paciente.value,
            complejidad=paciente.complejidad_requerida.value,
            diagnostico=paciente.diagnostico
        ))
    
    # Ordenar por prioridad
    resultado.sort(key=lambda x: x.prioridad, reverse=True)
    
    return resultado


@app.post("/api/derivaciones/{paciente_id}/accion", response_model=MessageResponse)
async def accion_derivacion(
    paciente_id: str,
    data: DerivacionAccionRequest,
    session: Session = Depends(get_session)
):
    """Acepta o rechaza una derivación."""
    paciente = session.get(Paciente, paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    if paciente.derivacion_estado != "pendiente":
        raise HTTPException(status_code=400, detail="La derivación no está pendiente")
    
    hospital_destino_id = paciente.derivacion_hospital_destino_id
    hospital_origen_id = paciente.hospital_id
    
    if data.accion == "aceptar":
        # Cambiar hospital del paciente
        paciente.hospital_id = hospital_destino_id
        paciente.derivacion_estado = "aceptado"
        paciente.tipo_paciente = TipoPacienteEnum.DERIVADO
        paciente.en_lista_espera = True
        paciente.timestamp_lista_espera = datetime.utcnow()
        paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
        session.add(paciente)
        
        # Actualizar cama origen
        if paciente.cama_id:
            query_cama = select(Cama).where(Cama.id == paciente.cama_id)
            cama_origen = session.exec(query_cama).first()
            if cama_origen:
                cama_origen.estado = EstadoCamaEnum.DERIVACION_CONFIRMADA
                cama_origen.mensaje_estado = "Derivación confirmada"
                session.add(cama_origen)
        
        session.commit()
        
        # Agregar a cola del hospital destino
        gestor_colas_global.agregar_paciente(paciente, hospital_destino_id, session)
        
        await manager.broadcast({
            "tipo": "derivacion_aceptada",
            "paciente_id": paciente.id,
            "hospital_origen_id": hospital_origen_id,
            "hospital_destino_id": hospital_destino_id
        })
        
        return MessageResponse(
            success=True,
            message="Derivación aceptada. Paciente agregado a lista de espera."
        )
    
    else:  # rechazar
        if not data.motivo_rechazo:
            raise HTTPException(status_code=400, detail="Se requiere motivo de rechazo")
        
        paciente.derivacion_estado = "rechazado"
        paciente.derivacion_motivo_rechazo = data.motivo_rechazo
        
        # Actualizar cama origen
        if paciente.cama_id:
            query_cama = select(Cama).where(Cama.id == paciente.cama_id)
            cama_origen = session.exec(query_cama).first()
            if cama_origen:
                # Verificar si necesita otra cama
                if paciente.requiere_nueva_cama:
                    cama_origen.estado = EstadoCamaEnum.CAMA_EN_ESPERA
                    cama_origen.mensaje_estado = "Paciente requiere nueva cama"
                else:
                    cama_origen.estado = EstadoCamaEnum.OCUPADA
                    cama_origen.mensaje_estado = None
                session.add(cama_origen)
        
        session.add(paciente)
        session.commit()
        
        await manager.broadcast({
            "tipo": "derivacion_rechazada",
            "paciente_id": paciente.id,
            "hospital_origen_id": hospital_origen_id
        })
        
        return MessageResponse(
            success=True,
            message="Derivación rechazada."
        )


@app.post("/api/derivaciones/{paciente_id}/confirmar-egreso", response_model=MessageResponse)
async def confirmar_egreso_derivacion(paciente_id: str, session: Session = Depends(get_session)):
    """Confirma el egreso de un paciente derivado de su hospital de origen."""
    paciente = session.get(Paciente, paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    if paciente.derivacion_estado != "aceptado":
        raise HTTPException(status_code=400, detail="La derivación no está confirmada")
    
    # Liberar cama origen (que ahora pertenece al hospital origen)
    query_cama = select(Cama).join(Sala).join(Servicio).where(
        Cama.id == paciente.cama_id
    )
    cama_origen = session.exec(query_cama).first()
    
    if cama_origen:
        cama_origen.estado = EstadoCamaEnum.EN_LIMPIEZA
        cama_origen.limpieza_inicio = datetime.utcnow()
        cama_origen.mensaje_estado = "En limpieza"
        session.add(cama_origen)
        
        actualizar_sexo_sala_si_vacia(cama_origen.sala_id, session)
    
    # El paciente ya no tiene cama origen
    paciente.cama_id = None
    session.add(paciente)
    session.commit()
    
    await manager.broadcast({
        "tipo": "egreso_confirmado",
        "paciente_id": paciente.id
    })
    
    return MessageResponse(
        success=True,
        message="Egreso confirmado. Cama liberada."
    )


# ============================================
# ENDPOINTS DE ALTA
# ============================================

@app.post("/api/pacientes/{paciente_id}/iniciar-alta", response_model=MessageResponse)
async def iniciar_alta_endpoint(paciente_id: str, session: Session = Depends(get_session)):
    """Inicia el proceso de alta de un paciente."""
    resultado = iniciar_alta(paciente_id, session)
    
    if "error" in resultado:
        raise HTTPException(status_code=400, detail=resultado["error"])
    
    await manager.broadcast({
        "tipo": "alta_iniciada",
        "paciente_id": paciente_id
    })
    
    return MessageResponse(success=True, message="Alta iniciada correctamente")


@app.post("/api/pacientes/{paciente_id}/ejecutar-alta", response_model=MessageResponse)
async def ejecutar_alta_endpoint(paciente_id: str, session: Session = Depends(get_session)):
    """Ejecuta el alta definitiva de un paciente."""
    resultado = ejecutar_alta(paciente_id, session)
    
    if "error" in resultado:
        raise HTTPException(status_code=400, detail=resultado["error"])
    
    await manager.broadcast({
        "tipo": "alta_ejecutada",
        "paciente_id": paciente_id,
        "cama_liberada": resultado.get("cama_liberada")
    })
    
    return MessageResponse(
        success=True,
        message="Alta ejecutada. Paciente dado de alta.",
        data=resultado
    )


@app.post("/api/pacientes/{paciente_id}/cancelar-alta", response_model=MessageResponse)
async def cancelar_alta_endpoint(paciente_id: str, session: Session = Depends(get_session)):
    """Cancela el proceso de alta."""
    resultado = cancelar_alta(paciente_id, session)
    
    if "error" in resultado:
        raise HTTPException(status_code=400, detail=resultado["error"])
    
    await manager.broadcast({
        "tipo": "alta_cancelada",
        "paciente_id": paciente_id
    })
    
    return MessageResponse(success=True, message="Alta cancelada")


# ============================================
# ENDPOINTS DE MODO MANUAL
# ============================================

@app.get("/api/configuracion", response_model=ConfiguracionResponse)
def obtener_configuracion(session: Session = Depends(get_session)):
    """Obtiene la configuración del sistema."""
    config = session.exec(select(ConfiguracionSistema)).first()
    if not config:
        config = ConfiguracionSistema()
        session.add(config)
        session.commit()
    
    return ConfiguracionResponse(
        modo_manual=config.modo_manual,
        tiempo_limpieza_segundos=config.tiempo_limpieza_segundos
    )


@app.put("/api/configuracion", response_model=ConfiguracionResponse)
async def actualizar_configuracion(
    data: ConfiguracionUpdate,
    session: Session = Depends(get_session)
):
    """Actualiza la configuración del sistema."""
    config = session.exec(select(ConfiguracionSistema)).first()
    if not config:
        config = ConfiguracionSistema()
    
    if data.modo_manual is not None:
        modo_anterior = config.modo_manual
        config.modo_manual = data.modo_manual
        
        # Si se activa el modo manual, cancelar asignaciones pendientes
        if data.modo_manual and not modo_anterior:
            await activar_modo_manual(session)
        # Si se desactiva, priorizar pacientes que perdieron asignación
        elif not data.modo_manual and modo_anterior:
            await desactivar_modo_manual(session)
    
    if data.tiempo_limpieza_segundos is not None:
        config.tiempo_limpieza_segundos = data.tiempo_limpieza_segundos
    
    config.updated_at = datetime.utcnow()
    session.add(config)
    session.commit()
    
    await manager.broadcast({
        "tipo": "configuracion_actualizada",
        "modo_manual": config.modo_manual
    })
    
    return ConfiguracionResponse(
        modo_manual=config.modo_manual,
        tiempo_limpieza_segundos=config.tiempo_limpieza_segundos
    )


async def activar_modo_manual(session: Session):
    """Activa el modo manual y cancela asignaciones pendientes."""
    # Cancelar camas en traslado entrante
    query = select(Cama).where(Cama.estado == EstadoCamaEnum.TRASLADO_ENTRANTE)
    camas = session.exec(query).all()
    
    for cama in camas:
        # Buscar paciente asignado
        query_paciente = select(Paciente).where(Paciente.cama_destino_id == cama.id)
        paciente = session.exec(query_paciente).first()
        
        if paciente:
            paciente.cama_destino_id = None
            paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
            session.add(paciente)
        
        cama.estado = EstadoCamaEnum.LIBRE
        cama.mensaje_estado = None
        session.add(cama)
    
    # Convertir traslados confirmados a salientes
    query2 = select(Cama).where(Cama.estado == EstadoCamaEnum.TRASLADO_CONFIRMADO)
    camas2 = session.exec(query2).all()
    
    for cama in camas2:
        cama.estado = EstadoCamaEnum.TRASLADO_SALIENTE
        cama.cama_asignada_destino = None
        cama.mensaje_estado = "En espera de confirmación"
        session.add(cama)
    
    session.commit()


async def desactivar_modo_manual(session: Session):
    """Desactiva el modo manual y prepara para reasignación."""
    # Los pacientes que perdieron asignación ya están en la cola
    # Solo necesitamos actualizar prioridades
    hospitales = session.exec(select(Hospital)).all()
    
    for hospital in hospitales:
        gestor_colas_global.sincronizar_cola_con_db(hospital.id, session)


@app.post("/api/manual/trasladar", response_model=MessageResponse)
async def traslado_manual(data: TrasladoManualRequest, session: Session = Depends(get_session)):
    """Realiza un traslado manual de paciente (solo en modo manual)."""
    config = session.exec(select(ConfiguracionSistema)).first()
    if not config or not config.modo_manual:
        raise HTTPException(status_code=400, detail="El modo manual no está activado")
    
    paciente = session.get(Paciente, data.paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    cama_destino = session.get(Cama, data.cama_destino_id)
    if not cama_destino:
        raise HTTPException(status_code=404, detail="Cama destino no encontrada")
    
    if cama_destino.estado != EstadoCamaEnum.LIBRE:
        raise HTTPException(status_code=400, detail="La cama destino no está libre")
    
    # Liberar cama origen si existe
    if paciente.cama_id:
        cama_origen = session.get(Cama, paciente.cama_id)
        if cama_origen:
            cama_origen.estado = EstadoCamaEnum.EN_LIMPIEZA
            cama_origen.limpieza_inicio = datetime.utcnow()
            cama_origen.mensaje_estado = "En limpieza"
            session.add(cama_origen)
            
            actualizar_sexo_sala_si_vacia(cama_origen.sala_id, session)
    
    # Asignar nueva cama
    paciente.cama_id = cama_destino.id
    paciente.cama_destino_id = None
    paciente.en_lista_espera = False
    paciente.requiere_nueva_cama = False
    session.add(paciente)
    
    cama_destino.estado = EstadoCamaEnum.OCUPADA
    session.add(cama_destino)
    
    # Actualizar sexo de sala
    sala = cama_destino.sala
    if not sala.es_individual and not sala.sexo_asignado:
        sala.sexo_asignado = paciente.sexo
        session.add(sala)
    
    session.commit()
    
    await manager.broadcast({
        "tipo": "traslado_manual_completado",
        "paciente_id": paciente.id,
        "cama_id": cama_destino.id
    })
    
    return MessageResponse(
        success=True,
        message="Traslado manual completado"
    )


@app.post("/api/manual/intercambiar", response_model=MessageResponse)
async def intercambio_manual(data: IntercambioRequest, session: Session = Depends(get_session)):
    """Intercambia dos pacientes de cama (solo en modo manual)."""
    config = session.exec(select(ConfiguracionSistema)).first()
    if not config or not config.modo_manual:
        raise HTTPException(status_code=400, detail="El modo manual no está activado")
    
    paciente_a = session.get(Paciente, data.paciente_a_id)
    paciente_b = session.get(Paciente, data.paciente_b_id)
    
    if not paciente_a or not paciente_b:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    if not paciente_a.cama_id or not paciente_b.cama_id:
        raise HTTPException(status_code=400, detail="Ambos pacientes deben tener cama asignada")
    
    # Intercambiar camas
    cama_a_id = paciente_a.cama_id
    cama_b_id = paciente_b.cama_id
    
    paciente_a.cama_id = cama_b_id
    paciente_b.cama_id = cama_a_id
    
    session.add(paciente_a)
    session.add(paciente_b)
    session.commit()
    
    await manager.broadcast({
        "tipo": "intercambio_completado",
        "paciente_a_id": paciente_a.id,
        "paciente_b_id": paciente_b.id
    })
    
    return MessageResponse(
        success=True,
        message="Intercambio completado"
    )


# ============================================
# ENDPOINTS DE ESTADÍSTICAS
# ============================================

@app.get("/api/estadisticas", response_model=EstadisticasGlobalesResponse)
def obtener_estadisticas(session: Session = Depends(get_session)):
    """Obtiene estadísticas globales del sistema."""
    hospitales = session.exec(select(Hospital)).all()
    
    stats_hospitales = []
    total_camas = 0
    total_pacientes = 0
    
    for hospital in hospitales:
        query_camas = select(Cama).join(Sala).join(Servicio).where(
            Servicio.hospital_id == hospital.id
        )
        camas = session.exec(query_camas).all()
        
        camas_libres = len([c for c in camas if c.estado == EstadoCamaEnum.LIBRE])
        camas_ocupadas = len([c for c in camas if c.estado in [
            EstadoCamaEnum.OCUPADA, EstadoCamaEnum.CAMA_EN_ESPERA,
            EstadoCamaEnum.TRASLADO_SALIENTE, EstadoCamaEnum.TRASLADO_CONFIRMADO,
            EstadoCamaEnum.ALTA_SUGERIDA, EstadoCamaEnum.CAMA_ALTA,
            EstadoCamaEnum.ESPERA_DERIVACION, EstadoCamaEnum.DERIVACION_CONFIRMADA
        ]])
        camas_traslado = len([c for c in camas if c.estado == EstadoCamaEnum.TRASLADO_ENTRANTE])
        camas_limpieza = len([c for c in camas if c.estado == EstadoCamaEnum.EN_LIMPIEZA])
        camas_bloqueadas = len([c for c in camas if c.estado == EstadoCamaEnum.BLOQUEADA])
        
        total_hospital = len(camas)
        ocupacion = (camas_ocupadas / total_hospital * 100) if total_hospital > 0 else 0
        
        # Pacientes en espera
        cola = gestor_colas_global.obtener_cola(hospital.id)
        pacientes_espera = cola.tamano()
        
        # Derivados pendientes
        query_derivados = select(Paciente).where(
            Paciente.derivacion_hospital_destino_id == hospital.id,
            Paciente.derivacion_estado == "pendiente"
        )
        derivados = len(session.exec(query_derivados).all())
        
        stats_hospitales.append(EstadisticasHospitalResponse(
            hospital_id=hospital.id,
            hospital_nombre=hospital.nombre,
            total_camas=total_hospital,
            camas_libres=camas_libres,
            camas_ocupadas=camas_ocupadas,
            camas_traslado=camas_traslado,
            camas_limpieza=camas_limpieza,
            camas_bloqueadas=camas_bloqueadas,
            pacientes_en_espera=pacientes_espera,
            pacientes_derivados_pendientes=derivados,
            ocupacion_porcentaje=round(ocupacion, 1)
        ))
        
        total_camas += total_hospital
        total_pacientes += camas_ocupadas
    
    ocupacion_promedio = (total_pacientes / total_camas * 100) if total_camas > 0 else 0
    
    return EstadisticasGlobalesResponse(
        hospitales=stats_hospitales,
        total_camas_sistema=total_camas,
        total_pacientes_sistema=total_pacientes,
        ocupacion_promedio=round(ocupacion_promedio, 1)
    )


# ============================================
# ENDPOINTS DE ARCHIVOS
# ============================================

@app.post("/api/pacientes/{paciente_id}/documento")
async def subir_documento(
    paciente_id: str,
    archivo: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    """Sube un documento PDF para un paciente."""
    if not archivo.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")
    
    paciente = session.get(Paciente, paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    # Guardar archivo
    filename = f"{paciente_id}_{archivo.filename}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    with open(filepath, "wb") as f:
        content = await archivo.read()
        f.write(content)
    
    # Actualizar paciente
    paciente.documento_adjunto = filename
    session.add(paciente)
    session.commit()
    
    return {"success": True, "filename": filename}


@app.get("/api/documentos/{filename}")
async def obtener_documento(filename: str):
    """Descarga un documento."""
    filepath = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    return FileResponse(filepath, media_type="application/pdf")


@app.delete("/api/pacientes/{paciente_id}/documento")
async def eliminar_documento(paciente_id: str, session: Session = Depends(get_session)):
    """Elimina el documento de un paciente."""
    paciente = session.get(Paciente, paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    if paciente.documento_adjunto:
        filepath = os.path.join(UPLOAD_DIR, paciente.documento_adjunto)
        if os.path.exists(filepath):
            os.remove(filepath)
        
        paciente.documento_adjunto = None
        session.add(paciente)
        session.commit()
    
    return {"success": True}


# ============================================
# ENDPOINT DE SALUD
# ============================================

@app.get("/api/health")
def health_check():
    """Verifica el estado del servidor."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)