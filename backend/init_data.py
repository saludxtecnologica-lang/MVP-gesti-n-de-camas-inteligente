"""
Script de inicialización de datos para el Sistema de Gestión de Camas.
Crea los hospitales, servicios, salas y camas según especificaciones.
"""

from sqlmodel import Session, select
from models import (
    Hospital, Servicio, Sala, Cama, ConfiguracionSistema,
    TipoServicioEnum, EstadoCamaEnum
)


def inicializar_datos(session: Session):
    """Inicializa todos los datos del sistema."""
    
    # Verificar si ya hay datos
    hospitales_existentes = session.exec(select(Hospital)).first()
    if hospitales_existentes:
        print("✅ Datos ya inicializados")
        return
    
    print("🏥 Inicializando datos del sistema...")
    
    # Crear hospitales
    hospital_pm = Hospital(
        nombre="Hospital de Puerto Montt",
        codigo="PM",
        es_central=True
    )
    hospital_ll = Hospital(
        nombre="Hospital de Llanquihue",
        codigo="LL",
        es_central=False
    )
    hospital_ca = Hospital(
        nombre="Hospital de Calbuco",
        codigo="CA",
        es_central=False
    )
    
    session.add_all([hospital_pm, hospital_ll, hospital_ca])
    session.commit()
    
    # ========== HOSPITAL PUERTO MONTT ==========
    crear_servicios_puerto_montt(session, hospital_pm)
    
    # ========== HOSPITAL LLANQUIHUE ==========
    crear_servicio_medico_quirurgico(session, hospital_ll, 100)
    
    # ========== HOSPITAL CALBUCO ==========
    crear_servicio_medico_quirurgico(session, hospital_ca, 100)
    
    # Crear configuración del sistema
    config = ConfiguracionSistema(
        modo_manual=False,
        tiempo_limpieza_segundos=60
    )
    session.add(config)
    session.commit()
    
    print("✅ Datos inicializados correctamente")


def crear_servicios_puerto_montt(session: Session, hospital: Hospital):
    """Crea los servicios del Hospital de Puerto Montt."""
    
    # UCI - 3 camas individuales (desde 200)
    servicio_uci = Servicio(
        nombre="Unidad de Cuidados Intensivos",
        codigo="UCI",
        tipo=TipoServicioEnum.UCI,
        hospital_id=hospital.id,
        numero_inicio_camas=200
    )
    session.add(servicio_uci)
    session.commit()
    
    for i in range(3):
        sala = Sala(
            numero=i + 1,
            es_individual=True,
            servicio_id=servicio_uci.id
        )
        session.add(sala)
        session.commit()
        
        cama = Cama(
            numero=200 + i,
            identificador=f"UCI-{200 + i}",
            sala_id=sala.id,
            estado=EstadoCamaEnum.LIBRE
        )
        session.add(cama)
    
    # UTI - 3 camas individuales (desde 203)
    servicio_uti = Servicio(
        nombre="Unidad de Tratamiento Intermedio",
        codigo="UTI",
        tipo=TipoServicioEnum.UTI,
        hospital_id=hospital.id,
        numero_inicio_camas=203
    )
    session.add(servicio_uti)
    session.commit()
    
    for i in range(3):
        sala = Sala(
            numero=i + 1,
            es_individual=True,
            servicio_id=servicio_uti.id
        )
        session.add(sala)
        session.commit()
        
        cama = Cama(
            numero=203 + i,
            identificador=f"UTI-{203 + i}",
            sala_id=sala.id,
            estado=EstadoCamaEnum.LIBRE
        )
        session.add(cama)
    
    # Medicina - 9 camas en 3 salas de 3 camas (desde 500)
    servicio_med = Servicio(
        nombre="Medicina",
        codigo="MED",
        tipo=TipoServicioEnum.MEDICINA,
        hospital_id=hospital.id,
        numero_inicio_camas=500
    )
    session.add(servicio_med)
    session.commit()
    
    crear_salas_compartidas(session, servicio_med, 3, 3, 500, "MED")
    
    # Aislamiento - 3 camas individuales (desde 509)
    servicio_aisl = Servicio(
        nombre="Aislamiento",
        codigo="AISL",
        tipo=TipoServicioEnum.AISLAMIENTO,
        hospital_id=hospital.id,
        numero_inicio_camas=509
    )
    session.add(servicio_aisl)
    session.commit()
    
    for i in range(3):
        sala = Sala(
            numero=i + 1,
            es_individual=True,
            servicio_id=servicio_aisl.id
        )
        session.add(sala)
        session.commit()
        
        cama = Cama(
            numero=509 + i,
            identificador=f"AISL-{509 + i}",
            sala_id=sala.id,
            estado=EstadoCamaEnum.LIBRE
        )
        session.add(cama)
    
    # Cirugía - 9 camas en 3 salas de 3 camas (desde 600)
    servicio_cir = Servicio(
        nombre="Cirugía",
        codigo="CIR",
        tipo=TipoServicioEnum.CIRUGIA,
        hospital_id=hospital.id,
        numero_inicio_camas=600
    )
    session.add(servicio_cir)
    session.commit()
    
    crear_salas_compartidas(session, servicio_cir, 3, 3, 600, "CIR")
    
    # Obstetricia - 6 camas en 2 salas de 3 camas (desde 300)
    servicio_obs = Servicio(
        nombre="Obstetricia",
        codigo="OBS",
        tipo=TipoServicioEnum.OBSTETRICIA,
        hospital_id=hospital.id,
        numero_inicio_camas=300
    )
    session.add(servicio_obs)
    session.commit()
    
    crear_salas_compartidas(session, servicio_obs, 2, 3, 300, "OBS")
    
    # Pediatría - 6 camas en 2 salas de 3 camas (desde 700)
    servicio_ped = Servicio(
        nombre="Pediatría",
        codigo="PED",
        tipo=TipoServicioEnum.PEDIATRIA,
        hospital_id=hospital.id,
        numero_inicio_camas=700
    )
    session.add(servicio_ped)
    session.commit()
    
    crear_salas_compartidas(session, servicio_ped, 2, 3, 700, "PED")
    
    session.commit()


def crear_servicio_medico_quirurgico(session: Session, hospital: Hospital, inicio_camas: int):
    """Crea el servicio médico-quirúrgico para hospitales pequeños."""
    
    servicio = Servicio(
        nombre="Médico-Quirúrgico",
        codigo="MQ",
        tipo=TipoServicioEnum.MEDICO_QUIRURGICO,
        hospital_id=hospital.id,
        numero_inicio_camas=inicio_camas
    )
    session.add(servicio)
    session.commit()
    
    # 4 salas con 4 camas cada una
    crear_salas_compartidas(session, servicio, 4, 4, inicio_camas, "MQ")
    
    session.commit()


def crear_salas_compartidas(
    session: Session, 
    servicio: Servicio, 
    num_salas: int, 
    camas_por_sala: int, 
    inicio_numero: int,
    codigo_servicio: str
):
    """Crea salas compartidas con sus camas."""
    
    letras = ['A', 'B', 'C', 'D', 'E', 'F']
    numero_cama = inicio_numero
    
    for i in range(num_salas):
        sala = Sala(
            numero=i + 1,
            es_individual=False,
            servicio_id=servicio.id
        )
        session.add(sala)
        session.commit()
        
        for j in range(camas_por_sala):
            letra = letras[j] if j < len(letras) else str(j + 1)
            cama = Cama(
                numero=numero_cama,
                letra=letra,
                identificador=f"{codigo_servicio}-{numero_cama}-{letra}",
                sala_id=sala.id,
                estado=EstadoCamaEnum.LIBRE
            )
            session.add(cama)
        
        numero_cama += 1
    
    session.commit()


def reiniciar_datos(session: Session):
    """Reinicia todos los datos del sistema."""
    from models import Paciente, LogActividad
    
    # Eliminar en orden por dependencias
    session.exec(select(Paciente)).delete()
    session.exec(select(Cama)).delete()
    session.exec(select(Sala)).delete()
    session.exec(select(Servicio)).delete()
    session.exec(select(Hospital)).delete()
    session.exec(select(ConfiguracionSistema)).delete()
    session.exec(select(LogActividad)).delete()
    session.commit()
    
    # Reinicializar
    inicializar_datos(session)