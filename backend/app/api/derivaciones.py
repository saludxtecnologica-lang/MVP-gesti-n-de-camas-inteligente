"""
Endpoints de Derivaciones.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List

from app.core.database import get_session
from app.core.auth_dependencies import get_current_user
from app.core.rbac_service import rbac_service
from app.core.websocket_manager import manager
from app.core.exceptions import PacienteNotFoundError, ValidationError
from app.models.usuario import Usuario, PermisoEnum, RolEnum
from app.schemas.derivacion import DerivacionRequest, DerivacionAccionRequest
from app.schemas.paciente import PacienteDerivadoResponse
from app.schemas.responses import MessageResponse
from app.services.derivacion_service import DerivacionService
from app.repositories.paciente_repo import PacienteRepository

router = APIRouter()


@router.get("/hospital/{hospital_id}", response_model=List[PacienteDerivadoResponse])
def obtener_derivados(
    hospital_id: str,
    current_user: Usuario = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Obtiene pacientes derivados pendientes hacia un hospital. Filtrado por permisos del usuario."""
    service = DerivacionService(session)
    pacientes = service.obtener_derivados_pendientes(hospital_id)

    resultado = []
    for paciente in pacientes:
        # Obtener hospital de origen
        from app.repositories.hospital_repo import HospitalRepository
        from app.repositories.cama_repo import CamaRepository
        hospital_repo = HospitalRepository(session)
        cama_repo = CamaRepository(session)
        hospital_origen = hospital_repo.obtener_por_id(paciente.hospital_id)

        # Determinar servicio de origen y destino para filtrado RBAC
        paciente_servicio_origen = None
        paciente_servicio_destino = getattr(paciente, 'servicio_destino', None)

        # Obtener servicio de origen desde cama_origen_derivacion_id
        if paciente.cama_origen_derivacion_id:
            cama_origen = cama_repo.obtener_por_id(paciente.cama_origen_derivacion_id)
            if cama_origen and cama_origen.sala and cama_origen.sala.servicio:
                paciente_servicio_origen = cama_origen.sala.servicio.nombre

        # Aplicar filtro RBAC - Solo mostrar si el usuario puede ver este paciente
        if not rbac_service.puede_ver_paciente(
            current_user,
            paciente_servicio_origen,
            paciente_servicio_destino,
            paciente.hospital_id
        ):
            continue

        resultado.append(PacienteDerivadoResponse(
            paciente_id=paciente.id,
            nombre=paciente.nombre,
            run=paciente.run,
            prioridad=paciente.prioridad_calculada,
            tiempo_en_lista_min=paciente.tiempo_espera_min,
            hospital_origen_id=paciente.hospital_id,
            hospital_origen_nombre=hospital_origen.nombre if hospital_origen else "Desconocido",
            motivo_derivacion=paciente.derivacion_motivo or "",
            tipo_paciente=paciente.tipo_paciente.value,
            complejidad=paciente.complejidad_requerida.value,
            diagnostico=paciente.diagnostico
        ))

    return resultado


@router.get("/hospital/{hospital_id}/enviados")
def obtener_derivados_enviados(
    hospital_id: str,
    current_user: Usuario = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Obtiene pacientes derivados DESDE este hospital a otros hospitales.
    Filtrado por permisos del usuario.

    Retorna la lista de pacientes que han sido derivados a otros hospitales,
    mostrando su estado actual (pendiente o aceptada).
    """
    service = DerivacionService(session)
    pacientes = service.obtener_derivados_enviados(hospital_id)

    resultado = []
    from app.repositories.hospital_repo import HospitalRepository
    from app.repositories.cama_repo import CamaRepository
    hospital_repo = HospitalRepository(session)
    cama_repo = CamaRepository(session)

    for paciente in pacientes:
        # Determinar servicio de origen y destino para filtrado RBAC
        paciente_servicio_origen = None
        paciente_servicio_destino = getattr(paciente, 'servicio_destino', None)

        # Obtener cama origen y servicio de origen
        cama_origen = None
        cama_identificador = None
        if paciente.cama_origen_derivacion_id:
            cama_origen = cama_repo.obtener_por_id(paciente.cama_origen_derivacion_id)
            if cama_origen:
                cama_identificador = cama_origen.identificador
                if cama_origen.sala and cama_origen.sala.servicio:
                    paciente_servicio_origen = cama_origen.sala.servicio.nombre

        # Aplicar filtro RBAC - Solo mostrar si el usuario puede ver este paciente
        if not rbac_service.puede_ver_paciente(
            current_user,
            paciente_servicio_origen,
            paciente_servicio_destino,
            paciente.hospital_id
        ):
            continue

        # Obtener hospital destino
        hospital_destino = None
        if paciente.derivacion_hospital_destino_id:
            hospital_destino = hospital_repo.obtener_por_id(paciente.derivacion_hospital_destino_id)

        resultado.append({
            "paciente_id": paciente.id,
            "nombre": paciente.nombre,
            "run": paciente.run,
            "hospital_destino_id": paciente.derivacion_hospital_destino_id,
            "hospital_destino_nombre": hospital_destino.nombre if hospital_destino else "Desconocido",
            "motivo_derivacion": paciente.derivacion_motivo or "",
            "estado_derivacion": paciente.derivacion_estado,
            "cama_origen_identificador": cama_identificador,
            "tiempo_en_proceso_min": paciente.tiempo_espera_min,
            "complejidad": paciente.complejidad_requerida.value if paciente.complejidad_requerida else "ninguna",
            "diagnostico": paciente.diagnostico
        })

    return resultado


@router.post("/{paciente_id}/solicitar", response_model=MessageResponse)
async def solicitar_derivacion(
    paciente_id: str,
    request: DerivacionRequest,
    current_user: Usuario = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Solicita una derivación para un paciente. Solo MEDICO puede solicitar derivaciones."""
    # Verificar que solo MEDICO puede solicitar derivaciones
    if current_user.rol not in [RolEnum.MEDICO, RolEnum.PROGRAMADOR]:
        raise HTTPException(
            status_code=403,
            detail="Solo los médicos pueden solicitar derivaciones"
        )

    # Verificar permiso
    if not current_user.tiene_permiso(PermisoEnum.DERIVACION_SOLICITAR):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para solicitar derivaciones"
        )
    service = DerivacionService(session)

    try:
        resultado = service.solicitar_derivacion(
            paciente_id,
            request.hospital_destino_id,
            request.motivo,
            cama_reservada_id=request.cama_reservada_id  # Pasar cama reservada si existe
        )

        await manager.send_notification(
            {
                "tipo": "derivacion_solicitada",
                "paciente_id": paciente_id,
                "hospital_destino_id": request.hospital_destino_id,
            },
            notification_type="info",
            hospital_id=request.hospital_destino_id
        )

        return MessageResponse(success=True, message=resultado.mensaje)

    except PacienteNotFoundError:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{paciente_id}/accion", response_model=MessageResponse)
async def accion_derivacion(
    paciente_id: str,
    request: DerivacionAccionRequest,
    current_user: Usuario = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Acepta o rechaza una derivación. Solo MEDICO puede aceptar/rechazar."""
    # Verificar que solo MEDICO puede aceptar/rechazar derivaciones
    if current_user.rol not in [RolEnum.MEDICO, RolEnum.PROGRAMADOR]:
        raise HTTPException(
            status_code=403,
            detail="Solo los médicos pueden aceptar o rechazar derivaciones"
        )

    # Verificar permisos según la acción
    if request.accion == "aceptar":
        if not current_user.tiene_permiso(PermisoEnum.DERIVACION_ACEPTAR):
            raise HTTPException(
                status_code=403,
                detail="No tienes permisos para aceptar derivaciones"
            )
    else:
        if not current_user.tiene_permiso(PermisoEnum.DERIVACION_RECHAZAR):
            raise HTTPException(
                status_code=403,
                detail="No tienes permisos para rechazar derivaciones"
            )
    service = DerivacionService(session)
    
    try:
        if request.accion == "aceptar":
            resultado = service.aceptar_derivacion(paciente_id)
            notification_type = "success"
        else:
            if not request.motivo_rechazo:
                raise HTTPException(
                    status_code=400,
                    detail="Debe indicar el motivo del rechazo"
                )
            resultado = service.rechazar_derivacion(paciente_id, request.motivo_rechazo)
            notification_type = "warning"
        
        await manager.send_notification(
            {
                "tipo": f"derivacion_{request.accion}da",
                "paciente_id": paciente_id,
            },
            notification_type=notification_type
        )
        
        return MessageResponse(success=True, message=resultado.mensaje)
        
    except PacienteNotFoundError:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{paciente_id}/confirmar-egreso", response_model=MessageResponse)
async def confirmar_egreso_derivacion(
    paciente_id: str,
    session: Session = Depends(get_session)
):
    """Confirma el egreso del paciente del hospital de origen."""
    service = DerivacionService(session)

    try:
        resultado = service.confirmar_egreso_derivacion(paciente_id)

        await manager.broadcast({
            "tipo": "egreso_confirmado",
            "paciente_id": paciente_id
        })

        return MessageResponse(success=True, message=resultado.mensaje)

    except PacienteNotFoundError:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{paciente_id}/cancelar-desde-origen", response_model=MessageResponse)
async def cancelar_derivacion_desde_origen(
    paciente_id: str,
    session: Session = Depends(get_session)
):
    """
    Cancela la derivación desde el hospital de origen.
    
    Flujo:
    - Paciente se elimina del hospital destino (lista espera o asignación)
    - Cama origen vuelve a estado "OCUPADA"
    - Paciente permanece en hospital de origen
    """
    service = DerivacionService(session)
    
    try:
        resultado = service.cancelar_derivacion_desde_origen(paciente_id)
        
        await manager.broadcast({
            "tipo": "derivacion_cancelada_origen",
            "paciente_id": paciente_id
        })
        
        return MessageResponse(success=True, message=resultado.mensaje)
        
    except PacienteNotFoundError:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{paciente_id}/verificar-viabilidad/{hospital_destino_id}")
def verificar_viabilidad_derivacion(
    paciente_id: str,
    hospital_destino_id: str,
    session: Session = Depends(get_session)
):
    """
    Verifica si una derivación es viable ANTES de solicitarla.
    
    Retorna información sobre si el hospital destino tiene las 
    capacidades necesarias para atender al paciente.
    """
    service = DerivacionService(session)
    
    try:
        resultado = service.verificar_viabilidad_derivacion(
            paciente_id,
            hospital_destino_id
        )
        
        return {
            "es_viable": resultado.es_viable,
            "mensaje": resultado.mensaje,
            "motivos_rechazo": resultado.motivos_rechazo,
            "hospital_destino_nombre": resultado.hospital_destino_nombre,
            "paciente_id": paciente_id
        }
        
    except PacienteNotFoundError:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{paciente_id}/cancelar", response_model=MessageResponse)
async def cancelar_derivacion(
    paciente_id: str,
    session: Session = Depends(get_session)
):
    """
    Cancela una derivación pendiente (antes de ser aceptada).
    
    Flujo:
    - Paciente sale de lista de derivados
    - Cama origen vuelve a estado "OCUPADA"
    """
    service = DerivacionService(session)
    paciente_repo = PacienteRepository(session)
    
    paciente = paciente_repo.obtener_por_id(paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    if paciente.derivacion_estado != "pendiente":
        raise HTTPException(
            status_code=400,
            detail="Solo se pueden cancelar derivaciones pendientes"
        )
    
    try:
        # Usar rechazo sin motivo para cancelar
        resultado = service.rechazar_derivacion(paciente_id, "Cancelada por el usuario")
        
        await manager.broadcast({
            "tipo": "derivacion_cancelada",
            "paciente_id": paciente_id
        })
        
        return MessageResponse(success=True, message="Derivación cancelada")
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
