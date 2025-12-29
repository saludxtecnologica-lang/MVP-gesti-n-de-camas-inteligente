"""
Tareas en segundo plano del sistema.
Procesos automáticos de asignación y limpieza.

ACTUALIZADO: Incluye actualización de sexo de sala y verificación de compatibilidad.

Ubicación: app/core/background_tasks.py
"""
import asyncio
import logging
from datetime import datetime, timedelta
from sqlmodel import Session, select

from app.config import settings
from app.core.database import get_session_direct
from app.core.websocket_manager import manager
from app.models.enums import EstadoCamaEnum
from app.models.cama import Cama
from app.models.paciente import Paciente
from app.models.configuracion import ConfiguracionSistema
from app.models.hospital import Hospital

# NUEVO IMPORT
from app.services.compatibilidad_service import (
    CompatibilidadService,
    verificar_y_actualizar_sexo_sala_al_egreso,
)

logger = logging.getLogger("gestion_camas.background")


async def proceso_automatico():
    """
    Proceso en segundo plano para asignación automática y limpieza.
    
    Ejecuta periódicamente:
    1. Procesamiento de camas en limpieza
    2. Procesamiento de pacientes esperando evaluación de oxígeno
    3. Asignación automática de camas (si no está en modo manual)
    """
    logger.info("Iniciando proceso automático")
    
    while True:
        try:
            session = get_session_direct()
            
            try:
                # Obtener configuración
                config = session.exec(select(ConfiguracionSistema)).first()
                
                if not config or not config.modo_manual:
                    # Solo ejecutar si no está en modo manual
                    
                    # 1. Procesar camas en limpieza
                    tiempo_limpieza = (
                        config.tiempo_limpieza_segundos 
                        if config else settings.TIEMPO_LIMPIEZA_DEFAULT
                    )
                    await procesar_camas_en_limpieza(
                        session, 
                        tiempo_limpieza
                    )
                    
                    # 2. Procesar pacientes esperando evaluación de oxígeno
                    tiempo_oxigeno = (
                        config.tiempo_espera_oxigeno_segundos
                        if config and hasattr(config, 'tiempo_espera_oxigeno_segundos') 
                        else getattr(settings, 'TIEMPO_ESPERA_OXIGENO_DEFAULT', 120)
                    )
                    await procesar_pacientes_espera_oxigeno(
                        session,
                        tiempo_oxigeno
                    )
                    
                    # 3. SIEMPRE ejecutar asignación automática
                    await ejecutar_asignacion_automatica_todas(session)
                
            finally:
                session.close()
            
        except Exception as e:
            logger.error(f"Error en proceso automático: {e}")
        
        await asyncio.sleep(settings.PROCESO_AUTOMATICO_INTERVALO)


async def procesar_camas_en_limpieza(
    session: Session, 
    tiempo_limpieza_segundos: int
) -> list:
    """
    Procesa camas que han terminado su tiempo de limpieza.
    
    ACTUALIZADO: Incluye actualización de sexo de sala al liberar.
    
    Args:
        session: Sesión de base de datos
        tiempo_limpieza_segundos: Tiempo de limpieza en segundos
    
    Returns:
        Lista de IDs de camas liberadas
    """
    camas_liberadas = []
    ahora = datetime.utcnow()
    
    # Buscar camas en limpieza
    query = select(Cama).where(Cama.estado == EstadoCamaEnum.EN_LIMPIEZA)
    camas = session.exec(query).all()
    
    for cama in camas:
        if cama.limpieza_inicio:
            tiempo_transcurrido = (ahora - cama.limpieza_inicio).total_seconds()
            
            if tiempo_transcurrido >= tiempo_limpieza_segundos:
                # Liberar cama
                cama.estado = EstadoCamaEnum.LIBRE
                cama.limpieza_inicio = None
                cama.mensaje_estado = None
                cama.estado_updated_at = ahora
                session.add(cama)
                camas_liberadas.append(cama.id)
                
                # NUEVO: Actualizar sexo de sala al liberar
                verificar_y_actualizar_sexo_sala_al_egreso(session, cama)
                
                logger.info(f"Cama {cama.identificador} liberada tras limpieza")
    
    if camas_liberadas:
        session.commit()
        
        # Notificar CON reload: true para que el frontend recargue
        await manager.broadcast({
            "tipo": "limpieza_completada",
            "cama_ids": camas_liberadas,
            "reload": True,
            "mensaje": f"{len(camas_liberadas)} cama(s) liberada(s) tras limpieza"
        })
    
    return camas_liberadas


async def procesar_pacientes_espera_oxigeno(
    session: Session,
    tiempo_espera_segundos: int
) -> list:
    """
    Procesa pacientes esperando evaluación tras descalaje de oxígeno.
    
    ACTUALIZADO: Usa el servicio de compatibilidad para verificaciones.
    
    Después del tiempo de espera, evalúa y cambia el estado de la cama a:
    - ALTA_SUGERIDA: Si el paciente no tiene requerimientos (puede ser dado de alta)
    - CAMA_EN_ESPERA: Si el paciente requiere nueva cama (flag o incompatible)
    - OCUPADA: Si el paciente es compatible con la cama actual
    
    IMPORTANTE: Respeta el flag requiere_nueva_cama que pudo haberse establecido
    durante reevaluaciones previas dentro del período de pausa.
    
    Args:
        session: Sesión de base de datos
        tiempo_espera_segundos: Tiempo de espera en segundos
    
    Returns:
        Lista de IDs de pacientes procesados
    """
    pacientes_procesados = []
    ahora = datetime.utcnow()
    limite = ahora - timedelta(seconds=tiempo_espera_segundos)
    
    # Buscar pacientes con flag de espera de oxígeno activo Y tiempo cumplido
    query = select(Paciente).where(
        Paciente.esperando_evaluacion_oxigeno == True,
        Paciente.oxigeno_desactivado_at.isnot(None),
        Paciente.oxigeno_desactivado_at <= limite,
        Paciente.cama_id.isnot(None)
    )
    pacientes = session.exec(query).all()
    
    # Crear servicio de compatibilidad
    compatibilidad_service = CompatibilidadService(session)
    
    for paciente in pacientes:
        cama = session.get(Cama, paciente.cama_id)
        if not cama:
            continue
        
        logger.info(
            f"Procesando paciente {paciente.nombre} - "
            f"Tiempo de espera oxígeno cumplido ({tiempo_espera_segundos}s). "
            f"Flag requiere_nueva_cama: {paciente.requiere_nueva_cama}"
        )
        
        # Limpiar campos de espera de oxígeno
        paciente.esperando_evaluacion_oxigeno = False
        paciente.oxigeno_desactivado_at = None
        paciente.requerimientos_oxigeno_previos = None
        
        # Determinar nuevo estado usando el servicio de asignación
        from app.services.asignacion_service import AsignacionService
        service = AsignacionService(session)
        
        # PRIMERO: Verificar si puede sugerir alta (sin requerimientos)
        if service.puede_sugerir_alta(paciente):
            cama.estado = EstadoCamaEnum.ALTA_SUGERIDA
            cama.mensaje_estado = "Se sugiere evaluar alta"
            paciente.requiere_nueva_cama = False
            logger.info(f"  → Paciente {paciente.nombre}: ALTA_SUGERIDA (sin requerimientos)")
        
        # SEGUNDO: Verificar si tiene flag de requiere_nueva_cama
        elif paciente.requiere_nueva_cama:
            cama.estado = EstadoCamaEnum.CAMA_EN_ESPERA
            cama.mensaje_estado = "Paciente requiere nueva cama"
            logger.info(f"  → Paciente {paciente.nombre}: CAMA_EN_ESPERA (flag activo)")
        
        # TERCERO: Verificar compatibilidad completa (incluye sexo y aislamiento)
        else:
            es_compatible, problemas = compatibilidad_service.verificar_compatibilidad_completa(
                paciente, cama
            )
            
            if not es_compatible:
                cama.estado = EstadoCamaEnum.CAMA_EN_ESPERA
                cama.mensaje_estado = "Paciente requiere nueva cama: " + "; ".join(problemas)
                paciente.requiere_nueva_cama = True
                logger.info(f"  → Paciente {paciente.nombre}: CAMA_EN_ESPERA (incompatible: {problemas})")
            else:
                cama.estado = EstadoCamaEnum.OCUPADA
                cama.mensaje_estado = None
                paciente.requiere_nueva_cama = False
                logger.info(f"  → Paciente {paciente.nombre}: OCUPADA (compatible con cama actual)")
        
        cama.estado_updated_at = ahora
        paciente.updated_at = ahora
        
        session.add(cama)
        session.add(paciente)
        pacientes_procesados.append(paciente.id)
    
    if pacientes_procesados:
        session.commit()
        
        # Broadcast con reload: true para que frontend se actualice
        await manager.broadcast({
            "tipo": "evaluacion_oxigeno_completada",
            "paciente_ids": pacientes_procesados,
            "reload": True,
            "play_sound": True,
            "mensaje": f"{len(pacientes_procesados)} paciente(s) procesado(s) tras evaluación de oxígeno"
        })
    
    return pacientes_procesados


async def ejecutar_asignacion_automatica_todas(session: Session) -> None:
    """
    Ejecuta asignación automática para todos los hospitales.
    
    Args:
        session: Sesión de base de datos
    """
    from app.services.asignacion_service import AsignacionService
    
    hospitales = session.exec(select(Hospital)).all()
    
    for hospital in hospitales:
        try:
            service = AsignacionService(session)
            asignaciones = await service.ejecutar_asignacion_automatica(hospital.id)
            
            if asignaciones:
                exitosas = [a for a in asignaciones if a.exito]
                if exitosas:
                    logger.info(
                        f"Hospital {hospital.nombre}: {len(exitosas)} asignaciones automáticas"
                    )
                    
                    # Broadcast con reload: true para que frontend se actualice
                    await manager.broadcast({
                        "tipo": "asignacion_automatica",
                        "hospital_id": hospital.id,
                        "cantidad": len(exitosas),
                        "reload": True,
                        "play_sound": True,
                        "mensaje": f"{len(exitosas)} asignación(es) automática(s) completada(s)"
                    })
                
        except Exception as e:
            logger.error(f"Error en asignación automática para {hospital.nombre}: {e}")