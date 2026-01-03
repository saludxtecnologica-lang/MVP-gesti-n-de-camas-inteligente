"""
Tareas en segundo plano del sistema.
Procesos automáticos de asignación y limpieza.

ACTUALIZADO v3.0:
- PROBLEMA 1: Corregida verificación de compatibilidad post-pausa de oxígeno
- PROBLEMA 6: Corregido procesamiento de timers de monitorización/observación
  con cambio de estado de cama cuando corresponde

Ubicación: app/core/background_tasks.py
"""
import asyncio
import logging
import json
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
    _obtener_nivel_complejidad,
)

logger = logging.getLogger("gestion_camas.background")


async def proceso_automatico():
    """
    Proceso en segundo plano para asignación automática y limpieza.
    
    Ejecuta periódicamente:
    1. Procesamiento de camas en limpieza
    2. Procesamiento de pacientes esperando evaluación de oxígeno
    3. Procesamiento de timers de monitorización/observación clínica
    4. Asignación automática de camas (si no está en modo manual)
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
                    
                    # 3. Procesar timers de monitorización/observación
                    await procesar_timers_monitorizacion_observacion(session)
                    
                    # 4. SIEMPRE ejecutar asignación automática
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
    
    PROBLEMA 1 CORREGIDO: Ahora verifica si la cama actual es compatible
    con la nueva complejidad del paciente antes de cambiar a CAMA_EN_ESPERA.
    
    Después del tiempo de espera, evalúa y cambia el estado de la cama a:
    - ALTA_SUGERIDA: Si el paciente no tiene requerimientos (puede ser dado de alta)
    - CAMA_EN_ESPERA: Si el paciente requiere nueva cama (complejidad incompatible)
    - OCUPADA: Si el paciente es compatible con la cama actual
    
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
    
    # Crear servicios necesarios
    compatibilidad_service = CompatibilidadService(session)
    
    from app.services.asignacion_service import AsignacionService
    asignacion_service = AsignacionService(session)
    
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
        
        # ============================================
        # PROBLEMA 1: VERIFICAR COMPATIBILIDAD REAL
        # ============================================
        
        # Calcular complejidades
        complejidad_paciente = asignacion_service.calcular_complejidad(paciente)
        complejidad_cama = asignacion_service.obtener_complejidad_cama(cama)
        
        nivel_paciente = _obtener_nivel_complejidad(complejidad_paciente)
        nivel_cama = _obtener_nivel_complejidad(complejidad_cama)
        
        logger.info(
            f"  Complejidad paciente: {complejidad_paciente.value} (nivel {nivel_paciente}), "
            f"Complejidad cama: {complejidad_cama.value} (nivel {nivel_cama})"
        )
        
        # PRIMERO: Verificar si puede sugerir alta (sin requerimientos)
        if asignacion_service.puede_sugerir_alta(paciente):
            cama.estado = EstadoCamaEnum.ALTA_SUGERIDA
            cama.mensaje_estado = "Se sugiere evaluar alta"
            paciente.requiere_nueva_cama = False
            logger.info(f"  → Paciente {paciente.nombre}: ALTA_SUGERIDA (sin requerimientos)")
        
        # SEGUNDO: Verificar si la cama actual es INCOMPATIBLE (nivel inferior)
        elif nivel_cama < nivel_paciente:
            # La cama NO soporta la complejidad del paciente
            cama.estado = EstadoCamaEnum.CAMA_EN_ESPERA
            cama.mensaje_estado = "Paciente requiere cama de mayor complejidad"
            paciente.requiere_nueva_cama = True
            logger.info(
                f"  → Paciente {paciente.nombre}: CAMA_EN_ESPERA "
                f"(cama nivel {nivel_cama} < paciente nivel {nivel_paciente})"
            )
        
        # TERCERO: Si tiene flag de requiere_nueva_cama Y hay camas disponibles
        elif paciente.requiere_nueva_cama:
            # Verificar si hay camas del nivel correcto disponibles
            hay_alternativas = compatibilidad_service.hay_camas_nivel_correcto_disponibles(
                paciente, paciente.hospital_id
            )
            
            if hay_alternativas and nivel_cama > nivel_paciente:
                # Hay camas del nivel correcto y está en cama de mayor complejidad
                cama.estado = EstadoCamaEnum.CAMA_EN_ESPERA
                cama.mensaje_estado = "Paciente puede ir a cama de menor complejidad"
                logger.info(
                    f"  → Paciente {paciente.nombre}: CAMA_EN_ESPERA "
                    f"(hay camas nivel {nivel_paciente} disponibles)"
                )
            else:
                # No hay alternativas o la cama es del nivel correcto
                cama.estado = EstadoCamaEnum.OCUPADA
                cama.mensaje_estado = None
                paciente.requiere_nueva_cama = False
                logger.info(
                    f"  → Paciente {paciente.nombre}: OCUPADA "
                    f"(cama compatible, no hay mejores alternativas)"
                )
        
        # CUARTO: Cama compatible, paciente se queda
        else:
            # Verificación final de compatibilidad completa
            es_compatible, problemas = compatibilidad_service.verificar_compatibilidad_arribo(
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


async def procesar_timers_monitorizacion_observacion(session: Session) -> dict:
    """
    Procesa los timers de monitorización y observación clínica.
    
    PROBLEMA 6 CORREGIDO: 
    - Guarda correctamente los timers
    - Desmarca automáticamente al cumplirse
    - Cambia estado de cama a CAMA_EN_ESPERA si corresponde
    
    Cuando un timer se completa:
    1. Desmarca automáticamente el requerimiento correspondiente
    2. Recalcula la complejidad del paciente
    3. Evalúa si necesita cambio de cama
    4. Genera una notificación
    
    Returns:
        Dict con conteo de timers procesados
    """
    from app.services.asignacion_service import AsignacionService
    from app.services.compatibilidad_service import CompatibilidadService, _obtener_nivel_complejidad
    
    ahora = datetime.utcnow()
    timers_completados = {
        'observacion': [],
        'monitorizacion': []
    }
    
    asignacion_service = AsignacionService(session)
    compatibilidad_service = CompatibilidadService(session)
    
    # ============================================
    # PROCESAR TIMERS DE OBSERVACIÓN CLÍNICA
    # ============================================
    
    query_obs = select(Paciente).where(
        Paciente.observacion_tiempo_horas.isnot(None),
        Paciente.observacion_inicio.isnot(None),
        Paciente.cama_id.isnot(None)  # Solo pacientes con cama
    )
    pacientes_obs = session.exec(query_obs).all()
    
    for paciente in pacientes_obs:
        tiempo_total_seg = paciente.observacion_tiempo_horas * 3600
        tiempo_transcurrido = (ahora - paciente.observacion_inicio).total_seconds()
        
        if tiempo_transcurrido >= tiempo_total_seg:
            # Timer completado - desmarcar observación
            logger.info(
                f"Timer de observación completado para {paciente.nombre} "
                f"({paciente.observacion_tiempo_horas}h)"
            )
            
            # Actualizar requerimientos - remover "Observación clínica"
            req_baja = paciente.get_requerimientos_lista('requerimientos_baja')
            if 'Observación clínica' in req_baja:
                req_baja.remove('Observación clínica')
                paciente.requerimientos_baja = json.dumps(req_baja)
            
            # Limpiar campos de observación
            paciente.observacion_tiempo_horas = None
            paciente.observacion_inicio = None
            paciente.motivo_observacion = None
            paciente.justificacion_observacion = None
            
            # Recalcular complejidad
            complejidad_anterior = paciente.complejidad_requerida
            paciente.complejidad_requerida = asignacion_service.calcular_complejidad(paciente)
            
            # Obtener cama actual
            cama = session.get(Cama, paciente.cama_id)
            
            if cama:
                # Evaluar si necesita cambio de cama
                complejidad_cama = asignacion_service.obtener_complejidad_cama(cama)
                nivel_paciente = _obtener_nivel_complejidad(paciente.complejidad_requerida)
                nivel_cama = _obtener_nivel_complejidad(complejidad_cama)
                
                # Si puede sugerir alta
                if asignacion_service.puede_sugerir_alta(paciente):
                    cama.estado = EstadoCamaEnum.ALTA_SUGERIDA
                    cama.mensaje_estado = "Se sugiere evaluar alta (timer observación completado)"
                    paciente.requiere_nueva_cama = False
                    logger.info(f"  → {paciente.nombre}: ALTA_SUGERIDA")
                # Si la cama es de mayor complejidad y hay alternativas
                elif nivel_cama > nivel_paciente:
                    if compatibilidad_service.hay_camas_nivel_correcto_disponibles(
                        paciente, paciente.hospital_id
                    ):
                        cama.estado = EstadoCamaEnum.CAMA_EN_ESPERA
                        cama.mensaje_estado = "Paciente puede bajar de complejidad (timer completado)"
                        paciente.requiere_nueva_cama = True
                        logger.info(f"  → {paciente.nombre}: CAMA_EN_ESPERA (bajar complejidad)")
                    else:
                        cama.estado = EstadoCamaEnum.OCUPADA
                        cama.mensaje_estado = None
                        logger.info(f"  → {paciente.nombre}: OCUPADA (sin alternativas)")
                else:
                    cama.estado = EstadoCamaEnum.OCUPADA
                    cama.mensaje_estado = None
                    logger.info(f"  → {paciente.nombre}: OCUPADA (cama compatible)")
                
                cama.estado_updated_at = ahora
                session.add(cama)
            
            paciente.updated_at = ahora
            session.add(paciente)
            
            timers_completados['observacion'].append({
                'paciente_id': paciente.id,
                'nombre': paciente.nombre,
                'hospital_id': paciente.hospital_id,
                'nuevo_estado': cama.estado.value if cama else None
            })
    
    # ============================================
    # PROCESAR TIMERS DE MONITORIZACIÓN
    # ============================================
    
    query_mon = select(Paciente).where(
        Paciente.monitorizacion_tiempo_horas.isnot(None),
        Paciente.monitorizacion_inicio.isnot(None),
        Paciente.cama_id.isnot(None)  # Solo pacientes con cama
    )
    pacientes_mon = session.exec(query_mon).all()
    
    for paciente in pacientes_mon:
        tiempo_total_seg = paciente.monitorizacion_tiempo_horas * 3600
        tiempo_transcurrido = (ahora - paciente.monitorizacion_inicio).total_seconds()
        
        if tiempo_transcurrido >= tiempo_total_seg:
            # Timer completado - desmarcar monitorización
            logger.info(
                f"Timer de monitorización completado para {paciente.nombre} "
                f"({paciente.monitorizacion_tiempo_horas}h)"
            )
            
            # Actualizar requerimientos - remover "Monitorización continua"
            req_uti = paciente.get_requerimientos_lista('requerimientos_uti')
            if 'Monitorización continua' in req_uti:
                req_uti.remove('Monitorización continua')
                paciente.requerimientos_uti = json.dumps(req_uti)
            
            # Limpiar campos de monitorización
            paciente.monitorizacion_tiempo_horas = None
            paciente.monitorizacion_inicio = None
            paciente.motivo_monitorizacion = None
            paciente.justificacion_monitorizacion = None
            
            # Recalcular complejidad
            complejidad_anterior = paciente.complejidad_requerida
            paciente.complejidad_requerida = asignacion_service.calcular_complejidad(paciente)
            
            # Obtener cama actual
            cama = session.get(Cama, paciente.cama_id)
            
            if cama:
                # Evaluar si necesita cambio de cama
                complejidad_cama = asignacion_service.obtener_complejidad_cama(cama)
                nivel_paciente = _obtener_nivel_complejidad(paciente.complejidad_requerida)
                nivel_cama = _obtener_nivel_complejidad(complejidad_cama)
                
                logger.info(
                    f"  Complejidad: antes={complejidad_anterior.value if complejidad_anterior else 'N/A'}, "
                    f"ahora={paciente.complejidad_requerida.value}, "
                    f"cama={complejidad_cama.value}"
                )
                
                # Si puede sugerir alta
                if asignacion_service.puede_sugerir_alta(paciente):
                    cama.estado = EstadoCamaEnum.ALTA_SUGERIDA
                    cama.mensaje_estado = "Se sugiere evaluar alta (timer monitorización completado)"
                    paciente.requiere_nueva_cama = False
                    logger.info(f"  → {paciente.nombre}: ALTA_SUGERIDA")
                # Si la cama es de mayor complejidad y hay alternativas
                elif nivel_cama > nivel_paciente:
                    if compatibilidad_service.hay_camas_nivel_correcto_disponibles(
                        paciente, paciente.hospital_id
                    ):
                        cama.estado = EstadoCamaEnum.CAMA_EN_ESPERA
                        cama.mensaje_estado = "Paciente puede bajar de complejidad (timer completado)"
                        paciente.requiere_nueva_cama = True
                        logger.info(f"  → {paciente.nombre}: CAMA_EN_ESPERA (bajar de UTI)")
                    else:
                        cama.estado = EstadoCamaEnum.OCUPADA
                        cama.mensaje_estado = None
                        logger.info(f"  → {paciente.nombre}: OCUPADA (sin alternativas de menor complejidad)")
                else:
                    cama.estado = EstadoCamaEnum.OCUPADA
                    cama.mensaje_estado = None
                    logger.info(f"  → {paciente.nombre}: OCUPADA (cama compatible)")
                
                cama.estado_updated_at = ahora
                session.add(cama)
            
            paciente.updated_at = ahora
            session.add(paciente)
            
            timers_completados['monitorizacion'].append({
                'paciente_id': paciente.id,
                'nombre': paciente.nombre,
                'hospital_id': paciente.hospital_id,
                'nuevo_estado': cama.estado.value if cama else None
            })
    
    # ============================================
    # COMMIT Y NOTIFICACIONES
    # ============================================
    
    total_procesados = len(timers_completados['observacion']) + len(timers_completados['monitorizacion'])
    
    if total_procesados > 0:
        session.commit()
        
        # Notificación de observación completada
        for item in timers_completados['observacion']:
            await manager.broadcast({
                "tipo": "timer_observacion_completado",
                "paciente_id": item['paciente_id'],
                "paciente_nombre": item['nombre'],
                "hospital_id": item['hospital_id'],
                "nuevo_estado": item.get('nuevo_estado'),
                "reload": True,
                "play_sound": True,
                "mensaje": f"Tiempo de observación clínica completado para {item['nombre']}"
            })
        
        # Notificación de monitorización completada
        for item in timers_completados['monitorizacion']:
            await manager.broadcast({
                "tipo": "timer_monitorizacion_completado",
                "paciente_id": item['paciente_id'],
                "paciente_nombre": item['nombre'],
                "hospital_id": item['hospital_id'],
                "nuevo_estado": item.get('nuevo_estado'),
                "reload": True,
                "play_sound": True,
                "mensaje": f"Tiempo de monitorización completado para {item['nombre']}"
            })
        
        logger.info(
            f"Timers procesados: {len(timers_completados['observacion'])} observación, "
            f"{len(timers_completados['monitorizacion'])} monitorización"
        )
    
    return timers_completados


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