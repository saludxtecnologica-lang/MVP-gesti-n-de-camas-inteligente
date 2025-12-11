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
    EstadoListaEsperaEnum, SexoEnum, TipoAislamientoEnum, TipoEnfermedadEnum
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
    completar_traslado, cancelar_asignacion,
    verificar_alta_sugerida, iniciar_alta, ejecutar_alta, cancelar_alta,
    procesar_camas_en_limpieza, actualizar_sexo_sala_si_vacia,
    asignar_cama_a_paciente, determinar_estado_cama_tras_reevaluacion,
    obtener_requerimientos_oxigeno_actuales, procesar_pacientes_espera_oxigeno,
    cama_es_compatible 
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
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass
    
    async def send_notification(self, message: dict, notification_type: str = "info", play_sound: bool = False):
        """
        Envía una notificación con tipo específico (incluye audio).
        CORRECCIÓN: play_sound ahora es un parámetro explícito para mejor control.
        """
        notification = {
            **message,
            "notification_type": notification_type,
            "play_sound": play_sound or notification_type == "asignacion"
        }
        await self.broadcast(notification)

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
    '''
    Proceso en segundo plano para asignación automática y limpieza.
    CORRECCIÓN PROBLEMA 5: Incluye procesamiento automático de espera de oxígeno.
    '''
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
                
                # CORRECCIÓN PROBLEMA 5: Procesar pacientes en espera por oxígeno
                tiempo_oxigeno = config.tiempo_espera_oxigeno_segundos if config else 120
                cambios_oxigeno = procesar_pacientes_espera_oxigeno(session, tiempo_oxigeno)
                
                if cambios_oxigeno:
                    await manager.send_notification({
                        "tipo": "cambios_oxigeno",
                        "cambios": cambios_oxigeno,
                        "message": "Cambio de estado por evaluación de oxígeno completada"
                    }, notification_type="info", play_sound=True)
                
                # Ejecutar asignación automática
                hospitales = session.exec(select(Hospital)).all()
                for hospital in hospitales:
                    asignaciones = ejecutar_asignacion_automatica(hospital.id, session)
                    
                    if asignaciones:
                        await manager.send_notification({
                            "tipo": "asignaciones",
                            "hospital_id": hospital.id,
                            "hospital_nombre": hospital.nombre,
                            "asignaciones": asignaciones,
                            "message": f"Nueva cama asignada en {hospital.nombre}"
                        }, notification_type="asignacion", play_sound=True)
                
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
            # CORRECCIÓN: Para DERIVACION_CONFIRMADA, buscar el paciente derivado asociado
            elif cama.estado in [EstadoCamaEnum.DERIVACION_CONFIRMADA, EstadoCamaEnum.ESPERA_DERIVACION] and cama.paciente_derivado_id:
                paciente_derivado = session.get(Paciente, cama.paciente_derivado_id)
                if paciente_derivado:
                    paciente = crear_paciente_response(paciente_derivado)
        
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


def crear_paciente_response(paciente):
    import json
    from datetime import datetime
    from models import TipoAislamientoEnum, ComplejidadEnum, EstadoListaEsperaEnum
    from schemas import PacienteResponse
    
    # Función auxiliar para parseo seguro de JSON
    def safe_json_loads(value, default=None):
        if default is None:
            default = []
        if not value:
            return default
        try:
            if isinstance(value, str):
                return json.loads(value)
            elif isinstance(value, list):
                return value
            return default
        except (json.JSONDecodeError, TypeError, ValueError):
            return default
    
    # Valores por defecto seguros
    try:
        return PacienteResponse(
            id=paciente.id or "",
            nombre=paciente.nombre or "",
            run=paciente.run or "",
            sexo=paciente.sexo,
            edad=paciente.edad if paciente.edad is not None else 0,
            edad_categoria=paciente.edad_categoria,
            es_embarazada=bool(paciente.es_embarazada) if paciente.es_embarazada is not None else False,
            diagnostico=paciente.diagnostico or "",
            tipo_enfermedad=paciente.tipo_enfermedad,
            tipo_aislamiento=paciente.tipo_aislamiento if paciente.tipo_aislamiento else TipoAislamientoEnum.NINGUNO,
            notas_adicionales=paciente.notas_adicionales,
            complejidad_requerida=paciente.complejidad_requerida if paciente.complejidad_requerida else ComplejidadEnum.NINGUNA,
            tipo_paciente=paciente.tipo_paciente,
            hospital_id=paciente.hospital_id or "",
            cama_id=paciente.cama_id,
            cama_destino_id=paciente.cama_destino_id,
            en_lista_espera=bool(paciente.en_lista_espera) if paciente.en_lista_espera is not None else False,
            estado_lista_espera=paciente.estado_lista_espera if paciente.estado_lista_espera else EstadoListaEsperaEnum.ESPERANDO,
            prioridad_calculada=float(paciente.prioridad_calculada) if paciente.prioridad_calculada is not None else 0.0,
            tiempo_espera_min=paciente.tiempo_espera_min if paciente.tiempo_espera_min is not None else 0,
            requiere_nueva_cama=bool(paciente.requiere_nueva_cama) if paciente.requiere_nueva_cama is not None else False,
            derivacion_hospital_destino_id=paciente.derivacion_hospital_destino_id,
            derivacion_motivo=paciente.derivacion_motivo,
            derivacion_estado=paciente.derivacion_estado,
            alta_solicitada=bool(paciente.alta_solicitada) if paciente.alta_solicitada is not None else False,
            created_at=paciente.created_at if paciente.created_at else datetime.utcnow(),
            updated_at=paciente.updated_at if paciente.updated_at else datetime.utcnow(),
            requerimientos_no_definen=safe_json_loads(paciente.requerimientos_no_definen),
            requerimientos_baja=safe_json_loads(paciente.requerimientos_baja),
            requerimientos_uti=safe_json_loads(paciente.requerimientos_uti),
            requerimientos_uci=safe_json_loads(paciente.requerimientos_uci),
            casos_especiales=safe_json_loads(paciente.casos_especiales),
            motivo_observacion=paciente.motivo_observacion,
            justificacion_observacion=paciente.justificacion_observacion,
            procedimiento_invasivo=paciente.procedimiento_invasivo
        )
    except Exception as e:
        # Log del error para debugging
        print(f"Error creando PacienteResponse para paciente {paciente.id if paciente else 'None'}: {e}")
        raise

@app.post("/api/pacientes", response_model=PacienteResponse)
async def registrar_paciente(
    data: PacienteCreate,
    session: Session = Depends(get_session)
):
    """Registra un nuevo paciente."""
    
    # Determinar categoría de edad
    edad_categoria = determinar_edad_categoria(data.edad)
    
    # CORRECCIÓN PROBLEMA 10: Validar tipo_paciente
    # Solo permitir URGENCIA o AMBULATORIO para nuevos pacientes
    tipo_paciente_valido = data.tipo_paciente
    if tipo_paciente_valido not in [TipoPacienteEnum.URGENCIA, TipoPacienteEnum.AMBULATORIO]:
        # Si viene otro tipo, asignar URGENCIA por defecto
        tipo_paciente_valido = TipoPacienteEnum.URGENCIA
    
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
        tipo_paciente=tipo_paciente_valido,
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
    
    paciente = session.get(Paciente, paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    cama_actual = session.get(Cama, paciente.cama_id) if paciente.cama_id else None
    
    # Guardar estado previo para comparación
    reqs_oxigeno_previos = obtener_requerimientos_oxigeno_actuales(paciente)
    tipo_enfermedad_previo = paciente.tipo_enfermedad
    tipo_aislamiento_previo = paciente.tipo_aislamiento
    
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
    
    # Determinar estado de la cama tras reevaluación
    if cama_actual:
        nuevo_estado, mensaje, necesita_espera_oxigeno = determinar_estado_cama_tras_reevaluacion(
            paciente, 
            cama_actual, 
            session, 
            reqs_oxigeno_previos, 
            tipo_enfermedad_previo,
            tipo_aislamiento_previo
        )
        
        # Manejar espera por desactivación de oxígeno
        if necesita_espera_oxigeno:
            # Iniciar periodo de espera de 2 minutos
            paciente.oxigeno_desactivado_at = datetime.utcnow()
            paciente.requerimientos_oxigeno_previos = json.dumps(reqs_oxigeno_previos)
            # Mantener cama ocupada durante el periodo de espera
            cama_actual.estado = EstadoCamaEnum.OCUPADA
            cama_actual.mensaje_estado = "Evaluando desescalaje de oxígeno"
            
            session.add(cama_actual)
            session.add(paciente)
            session.commit()
            
            await manager.broadcast({
                "tipo": "evaluando_oxigeno",
                "paciente_id": paciente.id,
                "cama_id": cama_actual.id,
                "hospital_id": paciente.hospital_id,
                "mensaje": "Evaluando desescalaje de oxígeno"
            })
            
            return crear_paciente_response(paciente)
        
        # Aplicar nuevo estado normalmente (sin espera de oxígeno)
        cama_actual.estado = nuevo_estado
        cama_actual.mensaje_estado = mensaje
        
        # Si requiere nueva cama (sin espera de oxígeno), agregar a lista de espera
        if nuevo_estado == EstadoCamaEnum.CAMA_EN_ESPERA:
            paciente.requiere_nueva_cama = True
            
            # Solo agregar a lista de espera si no está ya en ella
            if not paciente.en_lista_espera:
                # Cambiar estado de cama a TRASLADO_SALIENTE para indicar
                # que el paciente está buscando otra cama
                cama_actual.estado = EstadoCamaEnum.TRASLADO_SALIENTE
                cama_actual.mensaje_estado = mensaje or "Paciente requiere nueva cama"
                
                # Marcar como HOSPITALIZADO para la cola de prioridad
                paciente.tipo_paciente = TipoPacienteEnum.HOSPITALIZADO
                paciente.en_lista_espera = True
                paciente.timestamp_lista_espera = datetime.utcnow()
                paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
                
                session.add(cama_actual)
                session.add(paciente)
                session.commit()
                
                # Agregar a la cola de prioridad
                gestor_colas_global.agregar_paciente(paciente, paciente.hospital_id, session)
                
                await manager.broadcast({
                    "tipo": "paciente_requiere_nueva_cama",
                    "hospital_id": paciente.hospital_id,
                    "paciente_id": paciente.id,
                    "cama_actual_id": cama_actual.id,
                    "motivo": mensaje
                })
                
                return crear_paciente_response(paciente)
        else:
            paciente.requiere_nueva_cama = False
        
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
    
    # CORRECCIÓN PROBLEMA 10: Marcar como HOSPITALIZADO al buscar cama
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


app.post("/api/pacientes/{paciente_id}/cancelar-busqueda", response_model=MessageResponse)
async def cancelar_busqueda_cama(paciente_id: str, session: Session = Depends(get_session)):
    """
    Cancela búsqueda de cama. Delega a función unificada.
    Mantiene compatibilidad con llamadas existentes.
    """
    resultado = cancelar_asignacion(paciente_id, session)
    
    if "error" in resultado:
        raise HTTPException(status_code=400, detail=resultado["error"])
    
    await manager.broadcast({
        "tipo": "busqueda_cancelada",
        "paciente_id": paciente_id,
        "accion": resultado.get("accion", "cancelacion")
    })
    
    return MessageResponse(
        success=True,
        message="Búsqueda cancelada correctamente",
        data=resultado
    )


# ============================================
# ENDPOINTS DE TRASLADOS (RUTAS CONSISTENTES)
# ============================================

@app.post("/api/traslados/completar/{paciente_id}", response_model=MessageResponse)
async def completar_traslado_endpoint(paciente_id: str, session: Session = Depends(get_session)):
    """Completa el traslado de un paciente a su cama asignada."""
    resultado = completar_traslado(paciente_id, session)
    
    if "error" in resultado:
        raise HTTPException(status_code=400, detail=resultado["error"])
    
    await manager.send_notification({
        "tipo": "traslado_completado",
        "paciente_id": paciente_id,
        "cama_id": resultado.get("cama_nueva_id")
    }, notification_type="asignacion")
    
    return MessageResponse(
        success=True,
        message="Traslado completado correctamente",
        data=resultado
    )


@app.post("/api/traslados/cancelar/{paciente_id}", response_model=MessageResponse)
async def cancelar_traslado_endpoint(paciente_id: str, session: Session = Depends(get_session)):
    """
    ENDPOINT PRINCIPAL DE CANCELACIÓN - UNIFICADO
    
    Cancela traslado, derivación o elimina paciente según su estado.
    
    Flujos implementados:
    1. Desde cama origen (TRASLADO_SALIENTE/CONFIRMADO): 
       → Cama a CAMA_EN_ESPERA, paciente SALE de lista
    2. Desde cama destino (TRASLADO_ENTRANTE): 
       → Cama libre, paciente vuelve a lista
    3. Derivación desde destino: 
       → Paciente vuelve a lista derivación, cama origen a ESPERA_DERIVACION
    4. Derivación desde origen: 
       → Cama a OCUPADA, derivación cancelada
    5. Paciente nuevo: 
       → Eliminado del sistema (requiere confirmación previa en frontend)
    """
    resultado = cancelar_asignacion(paciente_id, session)
    
    if "error" in resultado:
        raise HTTPException(status_code=400, detail=resultado["error"])
    
    await manager.broadcast({
        "tipo": "traslado_cancelado",
        "paciente_id": paciente_id,
        "accion": resultado.get("accion", "cancelacion")
    })
    
    # Mensaje descriptivo según la acción
    mensajes = {
        "paciente_vuelve_a_cama_origen": "Búsqueda cancelada. Paciente permanece en cama actual.",
        "paciente_vuelve_a_lista_espera": "Asignación cancelada. Paciente vuelve a lista de espera.",
        "derivado_vuelve_a_lista_derivacion": "Cancelado. Paciente vuelve a lista de derivación.",
        "derivacion_cancelada_desde_origen": "Derivación cancelada. Paciente permanece en cama actual.",
        "paciente_nuevo_eliminado": "Paciente eliminado del sistema.",
        "cancelacion_basica": "Asignación cancelada."
    }
    
    mensaje = mensajes.get(resultado.get("accion"), "Cancelación completada")
    
    return MessageResponse(
        success=True,
        message=mensaje,
        data=resultado
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
    """
    Acepta o rechaza una derivación.
    
    CORRECCIÓN: Al rechazar, usa cama_origen_derivacion_id en lugar de cama_id
    porque cuando se acepta la derivación, cama_id se limpia.
    """
    paciente = session.get(Paciente, paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    if paciente.derivacion_estado != "pendiente":
        raise HTTPException(status_code=400, detail="La derivación no está pendiente")
    
    hospital_destino_id = paciente.derivacion_hospital_destino_id
    hospital_origen_id = paciente.hospital_id
    
    # CORRECCIÓN: Usar cama_origen_derivacion_id si existe, sino cama_id
    cama_origen_id = paciente.cama_origen_derivacion_id or paciente.cama_id
    
    if data.accion == "aceptar":
        # Actualizar cama origen a DERIVACION_CONFIRMADA
        if cama_origen_id:
            cama_origen = session.get(Cama, cama_origen_id)
            if cama_origen:
                cama_origen.estado = EstadoCamaEnum.DERIVACION_CONFIRMADA
                cama_origen.mensaje_estado = "Derivación aceptada - Esperando asignación en destino"
                cama_origen.paciente_derivado_id = paciente.id
                session.add(cama_origen)
        
        # Cambiar hospital del paciente
        paciente.hospital_id = hospital_destino_id
        paciente.derivacion_estado = "aceptado"
        paciente.tipo_paciente = TipoPacienteEnum.DERIVADO
        paciente.en_lista_espera = True
        paciente.timestamp_lista_espera = datetime.utcnow()
        paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
        
        # CORRECCIÓN: Guardar referencia a cama origen para poder restaurarla después
        paciente.cama_origen_derivacion_id = cama_origen_id
        # Limpiar cama_id porque la cama queda en hospital origen
        paciente.cama_id = None
        
        session.add(paciente)
        session.commit()
        
        # Agregar a cola del hospital destino
        gestor_colas_global.agregar_paciente(paciente, hospital_destino_id, session)
        
        await manager.broadcast({
            "tipo": "derivacion_aceptada",
            "paciente_id": paciente.id,
            "hospital_origen_id": hospital_origen_id,
            "hospital_destino_id": hospital_destino_id,
            "cama_origen_id": cama_origen_id
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
        
        # CORRECCIÓN: Usar cama_origen_derivacion_id si existe (caso de re-rechazo después de volver a lista)
        cama_a_actualizar_id = paciente.cama_origen_derivacion_id or paciente.cama_id
        
        if cama_a_actualizar_id:
            cama_origen = session.get(Cama, cama_a_actualizar_id)
            if cama_origen:
                # Verificar si necesita otra cama
                if paciente.requiere_nueva_cama:
                    cama_origen.estado = EstadoCamaEnum.CAMA_EN_ESPERA
                    cama_origen.mensaje_estado = "Paciente requiere nueva cama"
                else:
                    cama_origen.estado = EstadoCamaEnum.OCUPADA
                    cama_origen.mensaje_estado = None
                cama_origen.paciente_derivado_id = None
                session.add(cama_origen)
                
                # CORRECCIÓN: Restaurar cama_id del paciente
                paciente.cama_id = cama_a_actualizar_id
        
        # Limpiar referencias de derivación
        paciente.cama_origen_derivacion_id = None
        paciente.en_lista_espera = False
        
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
    """
    Confirma el egreso de un paciente derivado de su hospital de origen.
    Este endpoint se usa cuando el paciente tiene cama asignada en destino.
    Libera la cama de origen usando la referencia guardada.
    """
    paciente = session.get(Paciente, paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    if paciente.derivacion_estado != "aceptado":
        raise HTTPException(status_code=400, detail="La derivación no está confirmada")
    
    # Verificar que tiene cama asignada en el hospital destino
    if not paciente.cama_destino_id:
        raise HTTPException(status_code=400, detail="El paciente no tiene cama asignada en el hospital destino")
    
    # CORRECCIÓN: Usar la referencia guardada de la cama de origen
    cama_origen = None
    if paciente.cama_origen_derivacion_id:
        cama_origen = session.get(Cama, paciente.cama_origen_derivacion_id)
    
    # Fallback: buscar por paciente_derivado_id si no hay referencia directa
    if not cama_origen:
        query_camas = select(Cama).where(
            Cama.paciente_derivado_id == paciente.id
        )
        cama_origen = session.exec(query_camas).first()
    
    # Último fallback: buscar camas en DERIVACION_CONFIRMADA sin paciente
    if not cama_origen:
        query_camas = select(Cama).where(
            Cama.estado == EstadoCamaEnum.DERIVACION_CONFIRMADA
        )
        camas_derivacion = session.exec(query_camas).all()
        for cama in camas_derivacion:
            query_pac = select(Paciente).where(Paciente.cama_id == cama.id)
            pac_en_cama = session.exec(query_pac).first()
            if not pac_en_cama:
                cama_origen = cama
                break
    
    if cama_origen:
        cama_origen.estado = EstadoCamaEnum.EN_LIMPIEZA
        cama_origen.limpieza_inicio = datetime.utcnow()
        cama_origen.mensaje_estado = "En limpieza"
        cama_origen.paciente_derivado_id = None  # Limpiar referencia
        session.add(cama_origen)
        
        actualizar_sexo_sala_si_vacia(cama_origen.sala_id, session)
    
    # Limpiar la referencia en el paciente
    paciente.cama_origen_derivacion_id = None
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

@app.post("/api/derivaciones/{paciente_id}/cancelar-desde-origen", response_model=MessageResponse)
async def cancelar_derivacion_desde_origen(paciente_id: str, session: Session = Depends(get_session)):
    """
    Cancela una derivación desde la cama de origen.
    La cama vuelve a estado "ocupada".
    
    CORRECCIÓN: Este endpoint delega a cancelar_asignacion para evitar duplicación.
    """
    paciente = session.get(Paciente, paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    # Verificar que tiene derivación activa
    if not paciente.derivacion_estado or paciente.derivacion_estado == "cancelado":
        raise HTTPException(status_code=400, detail="El paciente no tiene derivación activa")
    
    # Verificar que la cama origen está en estado de derivación
    cama_origen = session.get(Cama, paciente.cama_id) if paciente.cama_id else None
    if not cama_origen or cama_origen.estado not in [EstadoCamaEnum.ESPERA_DERIVACION, EstadoCamaEnum.DERIVACION_CONFIRMADA]:
        raise HTTPException(status_code=400, detail="La cama no está en estado de derivación")
    
    # Usar la función unificada
    resultado = cancelar_asignacion(paciente_id, session)
    
    if "error" in resultado:
        raise HTTPException(status_code=400, detail=resultado["error"])
    
    await manager.broadcast({
        "tipo": "derivacion_cancelada_origen",
        "paciente_id": paciente_id
    })
    
    return MessageResponse(
        success=True,
        message="Derivación cancelada. Paciente permanece en cama actual.",
        data=resultado
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
        tiempo_limpieza_segundos=config.tiempo_limpieza_segundos,
        tiempo_espera_oxigeno_segundos=config.tiempo_espera_oxigeno_segundos
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
    
    # PROBLEMA 12: Actualizar tiempo de espera de oxígeno
    if data.tiempo_espera_oxigeno_segundos is not None:
        config.tiempo_espera_oxigeno_segundos = data.tiempo_espera_oxigeno_segundos
    
    config.updated_at = datetime.utcnow()
    session.add(config)
    session.commit()
    
    await manager.broadcast({
        "tipo": "configuracion_actualizada",
        "modo_manual": config.modo_manual
    })
    
    return ConfiguracionResponse(
        modo_manual=config.modo_manual,
        tiempo_limpieza_segundos=config.tiempo_limpieza_segundos,
        tiempo_espera_oxigeno_segundos=config.tiempo_espera_oxigeno_segundos
    )


async def activar_modo_manual(session: Session):
    '''
    Comportamiento:
    - Camas en "traslado entrante" → libres (pacientes vuelven a lista de espera)
    - Camas en "traslado confirmado" → "traslado saliente" (pacientes en lista de espera)
    - Se pausa todo el proceso automático
    '''
    from models import Cama, Paciente, EstadoCamaEnum, EstadoListaEsperaEnum
    from sqlmodel import select
    
    # PASO 1: Cancelar camas en traslado entrante
    # Los pacientes asignados vuelven a la lista de espera
    query_entrante = select(Cama).where(Cama.estado == EstadoCamaEnum.TRASLADO_ENTRANTE)
    camas_entrantes = session.exec(query_entrante).all()
    
    for cama in camas_entrantes:
        # Buscar paciente asignado a esta cama
        query_paciente = select(Paciente).where(Paciente.cama_destino_id == cama.id)
        paciente = session.exec(query_paciente).first()
        
        if paciente:
            # Paciente vuelve a lista de espera sin asignación
            paciente.cama_destino_id = None
            paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
            session.add(paciente)
        
        # Cama queda libre
        cama.estado = EstadoCamaEnum.LIBRE
        cama.mensaje_estado = None
        session.add(cama)
    
    # PASO 2: Convertir traslados confirmados a salientes
    # Los pacientes con cama asignada pasan a "traslado saliente" (en lista de espera)
    query_confirmado = select(Cama).where(Cama.estado == EstadoCamaEnum.TRASLADO_CONFIRMADO)
    camas_confirmadas = session.exec(query_confirmado).all()
    
    for cama in camas_confirmadas:
        # Buscar paciente en esta cama
        query_paciente = select(Paciente).where(Paciente.cama_id == cama.id)
        paciente = session.exec(query_paciente).first()
        
        if paciente and paciente.cama_destino_id:
            # Liberar cama destino
            cama_destino = session.get(Cama, paciente.cama_destino_id)
            if cama_destino:
                cama_destino.estado = EstadoCamaEnum.LIBRE
                cama_destino.mensaje_estado = None
                session.add(cama_destino)
            
            # Paciente vuelve a lista de espera
            paciente.cama_destino_id = None
            paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
            session.add(paciente)
        
        # Cama pasa a traslado saliente
        cama.estado = EstadoCamaEnum.TRASLADO_SALIENTE
        cama.cama_asignada_destino = None
        cama.mensaje_estado = "En espera de asignación manual"
        session.add(cama)
    
    session.commit()
    
    # Notificar cambio de modo
    await manager.broadcast({
        "tipo": "modo_manual_activado",
        "camas_liberadas": len(camas_entrantes),
        "camas_en_espera": len(camas_confirmadas)
    })


async def desactivar_modo_manual(session: Session):
    '''
    Comportamiento:
    - Los pacientes en lista de espera con estado "asignado" (asignados manualmente)
      NO se reasignan automáticamente
    - Los demás pacientes se reasignan según prioridad
    '''
    from models import Hospital
    from sqlmodel import select
    
    # Sincronizar colas con DB para todos los hospitales
    hospitales = session.exec(select(Hospital)).all()
    
    for hospital in hospitales:
        gestor_colas_global.sincronizar_cola_con_db(hospital.id, session)
    
    # Notificar cambio de modo
    await manager.broadcast({
        "tipo": "modo_automatico_activado"
    })


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

@app.post("/api/manual/asignar-desde-cama", response_model=MessageResponse)
async def asignar_manual_desde_cama(data: TrasladoManualRequest, session: Session = Depends(get_session)):
    '''
    CORRECCIÓN PROBLEMA 1: Asigna manualmente una cama a un paciente desde la vista de cama.
    Solo disponible en modo manual.
    El paciente debe estar en una cama ocupada.
    '''
    config = session.exec(select(ConfiguracionSistema)).first()
    if not config or not config.modo_manual:
        raise HTTPException(status_code=400, detail="El modo manual no está activado")
    
    paciente = session.get(Paciente, data.paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    if not paciente.cama_id:
        raise HTTPException(status_code=400, detail="El paciente debe tener una cama asignada")
    
    cama_destino = session.get(Cama, data.cama_destino_id)
    if not cama_destino:
        raise HTTPException(status_code=404, detail="Cama destino no encontrada")
    
    if cama_destino.estado != EstadoCamaEnum.LIBRE:
        raise HTTPException(status_code=400, detail="La cama destino no está libre")
    
    # Obtener cama origen
    cama_origen = session.get(Cama, paciente.cama_id)
    
    # Asignar cama destino al paciente
    paciente.cama_destino_id = cama_destino.id
    paciente.estado_lista_espera = EstadoListaEsperaEnum.ASIGNADO
    paciente.en_lista_espera = True
    session.add(paciente)
    
    # Actualizar cama destino
    cama_destino.estado = EstadoCamaEnum.TRASLADO_ENTRANTE
    cama_destino.mensaje_estado = f"Asignación manual: {paciente.nombre}"
    session.add(cama_destino)
    
    # Actualizar cama origen
    if cama_origen:
        cama_origen.estado = EstadoCamaEnum.TRASLADO_CONFIRMADO
        cama_origen.cama_asignada_destino = cama_destino.identificador
        cama_origen.mensaje_estado = f"Cama asignada: {cama_destino.identificador}"
        session.add(cama_origen)
    
    session.commit()
    
    await manager.broadcast({
        "tipo": "asignacion_manual",
        "paciente_id": paciente.id,
        "cama_origen_id": paciente.cama_id,
        "cama_destino_id": cama_destino.id
    })
    
    return MessageResponse(
        success=True,
        message=f"Paciente {paciente.nombre} asignado manualmente a cama {cama_destino.identificador}"
    )


@app.post("/api/manual/asignar-desde-lista", response_model=MessageResponse)
async def asignar_manual_desde_lista(data: TrasladoManualRequest, session: Session = Depends(get_session)):
    '''
    CORRECCIÓN PROBLEMA 1: Asigna manualmente una cama a un paciente desde la lista de espera.
    Solo disponible en modo manual.
    '''
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
    
    # Obtener cama origen si existe
    cama_origen = session.get(Cama, paciente.cama_id) if paciente.cama_id else None
    
    # Asignar cama destino al paciente
    paciente.cama_destino_id = cama_destino.id
    paciente.estado_lista_espera = EstadoListaEsperaEnum.ASIGNADO
    paciente.en_lista_espera = True
    session.add(paciente)
    
    # Actualizar cama destino
    cama_destino.estado = EstadoCamaEnum.TRASLADO_ENTRANTE
    cama_destino.mensaje_estado = f"Asignación manual: {paciente.nombre}"
    session.add(cama_destino)
    
    # Si tiene cama origen, actualizarla
    if cama_origen:
        cama_origen.estado = EstadoCamaEnum.TRASLADO_CONFIRMADO
        cama_origen.cama_asignada_destino = cama_destino.identificador
        cama_origen.mensaje_estado = f"Cama asignada: {cama_destino.identificador}"
        session.add(cama_origen)
    
    session.commit()
    
    await manager.broadcast({
        "tipo": "asignacion_manual_lista",
        "paciente_id": paciente.id,
        "cama_destino_id": cama_destino.id
    })
    
    return MessageResponse(
        success=True,
        message=f"Paciente {paciente.nombre} asignado manualmente a cama {cama_destino.identificador}"
    )


@app.post("/api/manual/egresar/{paciente_id}", response_model=MessageResponse)
async def egresar_manual(paciente_id: str, session: Session = Depends(get_session)):
    '''
    CORRECCIÓN PROBLEMA 1: Egresa manualmente a un paciente del sistema.
    Solo disponible en modo manual.
    '''
    config = session.exec(select(ConfiguracionSistema)).first()
    if not config or not config.modo_manual:
        raise HTTPException(status_code=400, detail="El modo manual no está activado")
    
    paciente = session.get(Paciente, paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    cama_id = paciente.cama_id
    
    # Si tiene cama, liberarla
    if cama_id:
        cama = session.get(Cama, cama_id)
        if cama:
            cama.estado = EstadoCamaEnum.EN_LIMPIEZA
            cama.limpieza_inicio = datetime.utcnow()
            cama.mensaje_estado = "En limpieza"
            session.add(cama)
            
            actualizar_sexo_sala_si_vacia(cama.sala_id, session)
    
    # Si tiene cama destino asignada, liberarla
    if paciente.cama_destino_id:
        cama_destino = session.get(Cama, paciente.cama_destino_id)
        if cama_destino:
            cama_destino.estado = EstadoCamaEnum.LIBRE
            cama_destino.mensaje_estado = None
            session.add(cama_destino)
    
    # Remover de cola si está
    if paciente.en_lista_espera:
        gestor_colas_global.remover_paciente(
            paciente.id,
            paciente.hospital_id,
            session,
            paciente
        )
    
    # Eliminar paciente
    nombre_paciente = paciente.nombre
    session.delete(paciente)
    session.commit()
    
    await manager.broadcast({
        "tipo": "egreso_manual",
        "paciente_id": paciente_id,
        "cama_liberada": cama_id
    })
    
    return MessageResponse(
        success=True,
        message=f"Paciente {nombre_paciente} egresado del sistema"
    )


@app.post("/api/manual/egresar-lista/{paciente_id}", response_model=MessageResponse)
async def egresar_de_lista(paciente_id: str, session: Session = Depends(get_session)):
    """
    Egresa a un paciente de la lista de espera.
    Disponible en modo manual.
    
    CORRECCIÓN: Usa cancelar_asignacion para unificar lógica.
    Maneja correctamente:
    - Pacientes hospitalizados: vuelven a CAMA_EN_ESPERA
    - Pacientes derivados: vuelven a lista de derivación
    - Pacientes nuevos: eliminados del sistema
    """
    config = session.exec(select(ConfiguracionSistema)).first()
    if not config or not config.modo_manual:
        raise HTTPException(status_code=400, detail="El modo manual no está activado")
    
    paciente = session.get(Paciente, paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    if not paciente.en_lista_espera:
        raise HTTPException(status_code=400, detail="El paciente no está en la lista de espera")
    
    # Guardar nombre antes de posible eliminación
    nombre_paciente = paciente.nombre
    
    # Usar la función unificada
    resultado = cancelar_asignacion(paciente_id, session)
    
    if "error" in resultado:
        raise HTTPException(status_code=400, detail=resultado["error"])
    
    # Determinar mensaje según acción
    accion = resultado.get("accion", "")
    if accion == "paciente_nuevo_eliminado":
        mensaje = f"Paciente {nombre_paciente} eliminado del sistema"
        tipo_broadcast = "paciente_eliminado"
    elif accion == "derivado_vuelve_a_lista_derivacion":
        mensaje = f"Paciente {nombre_paciente} devuelto a lista de derivación"
        tipo_broadcast = "paciente_devuelto_derivacion"
    else:
        mensaje = f"Paciente {nombre_paciente} removido de la lista de espera"
        tipo_broadcast = "paciente_removido_lista"
    
    await manager.broadcast({
        "tipo": tipo_broadcast,
        "paciente_id": paciente_id,
        "accion": accion
    })
    
    return MessageResponse(
        success=True,
        message=mensaje,
        data=resultado
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