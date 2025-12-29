"""
Inicialización de datos del sistema.
Crea hospitales, servicios, salas y camas según especificaciones.

ESTRUCTURA DE HOSPITALES:
========================

Hospital Puerto Montt (Central) - 39 camas:
- UCI: 3 camas individuales (200, 201, 202)
- UTI: 3 camas individuales (203, 204, 205)
- Medicina: 9 camas en 3 salas de 3 (500-A/B/C, 501-A/B/C, 502-A/B/C)
- Aislamiento: 3 camas individuales (509, 510, 511)
- Cirugía: 9 camas en 3 salas de 3 (600-A/B/C, 601-A/B/C, 602-A/B/C)
- Obstetricia: 6 camas en 2 salas de 3 (300-A/B/C, 301-A/B/C)
- Pediatría: 6 camas en 2 salas de 3 (700-A/B/C, 701-A/B/C)

Hospital Llanquihue - 16 camas:
- Médico-Quirúrgico: 16 camas en 4 salas de 4 (100-A/B/C/D ... 103-A/B/C/D)

Hospital Calbuco - 16 camas:
- Médico-Quirúrgico: 16 camas en 4 salas de 4 (100-A/B/C/D ... 103-A/B/C/D)
"""
from sqlmodel import Session, select
from datetime import datetime

from app.models.hospital import Hospital
from app.models.servicio import Servicio
from app.models.sala import Sala
from app.models.cama import Cama
from app.models.configuracion import ConfiguracionSistema
from app.models.enums import TipoServicioEnum, EstadoCamaEnum


def inicializar_datos(session: Session) -> None:
    """
    Inicializa los datos básicos del sistema si no existen.
    
    Args:
        session: Sesión de base de datos
    """
    # Verificar si ya hay datos
    hospitales_existentes = session.exec(select(Hospital)).first()
    if hospitales_existentes:
        return
    
    # ========================================
    # CREAR HOSPITALES
    # ========================================
    hospital_pm = Hospital(
        nombre="Hospital de Puerto Montt",
        codigo="PM",
        es_central=True
    )
    hospital_ll = Hospital(
        nombre="Hospital Llanquihue",
        codigo="LL",
        es_central=False
    )
    hospital_ca = Hospital(
        nombre="Hospital Calbuco",
        codigo="CA",
        es_central=False
    )
    
    session.add(hospital_pm)
    session.add(hospital_ll)
    session.add(hospital_ca)
    session.commit()
    session.refresh(hospital_pm)
    session.refresh(hospital_ll)
    session.refresh(hospital_ca)
    
    # ========================================
    # HOSPITAL PUERTO MONTT (CENTRAL)
    # ========================================
    crear_servicios_puerto_montt(session, hospital_pm.id)
    
    # ========================================
    # HOSPITAL LLANQUIHUE
    # ========================================
    crear_servicio_medico_quirurgico(session, hospital_ll.id, "Llanquihue")
    
    # ========================================
    # HOSPITAL CALBUCO
    # ========================================
    crear_servicio_medico_quirurgico(session, hospital_ca.id, "Calbuco")
    
    # ========================================
    # CONFIGURACIÓN INICIAL
    # ========================================
    config = ConfiguracionSistema(
        modo_manual=False,
        tiempo_limpieza_segundos=60,
        tiempo_espera_oxigeno_segundos=120,
    )
    session.add(config)
    session.commit()


def crear_servicios_puerto_montt(session: Session, hospital_id: str) -> None:
    """
    Crea los servicios del Hospital de Puerto Montt.
    
    Servicios:
    - UCI: 3 camas individuales, desde 200
    - UTI: 3 camas individuales, desde 203
    - Medicina: 9 camas (3 salas x 3), desde 500
    - Aislamiento: 3 camas individuales, desde 509
    - Cirugía: 9 camas (3 salas x 3), desde 600
    - Obstetricia: 6 camas (2 salas x 3), desde 300
    - Pediatría: 6 camas (2 salas x 3), desde 700
    """
    
    # ----------------------------------------
    # UCI - 3 camas individuales (200-202)
    # ----------------------------------------
    servicio_uci = Servicio(
        nombre="UCI",
        codigo="UCI",
        tipo=TipoServicioEnum.UCI,
        hospital_id=hospital_id,
        numero_inicio_camas=200,
        es_uci=True,
        es_uti=False,
        permite_pediatria=False
    )
    session.add(servicio_uci)
    session.commit()
    session.refresh(servicio_uci)
    
    crear_camas_individuales(
        session=session,
        servicio_id=servicio_uci.id,
        codigo_servicio="UCI",
        numero_inicio=200,
        cantidad_camas=3
    )
    
    # ----------------------------------------
    # UTI - 3 camas individuales (203-205)
    # ----------------------------------------
    servicio_uti = Servicio(
        nombre="UTI",
        codigo="UTI",
        tipo=TipoServicioEnum.UTI,
        hospital_id=hospital_id,
        numero_inicio_camas=203,
        es_uci=False,
        es_uti=True,
        permite_pediatria=False
    )
    session.add(servicio_uti)
    session.commit()
    session.refresh(servicio_uti)
    
    crear_camas_individuales(
        session=session,
        servicio_id=servicio_uti.id,
        codigo_servicio="UTI",
        numero_inicio=203,
        cantidad_camas=3
    )
    
    # ----------------------------------------
    # MEDICINA - 9 camas en 3 salas de 3 (500-502)
    # ----------------------------------------
    servicio_med = Servicio(
        nombre="Medicina",
        codigo="Med",
        tipo=TipoServicioEnum.MEDICINA,
        hospital_id=hospital_id,
        numero_inicio_camas=500,
        es_uci=False,
        es_uti=False,
        permite_pediatria=False
    )
    session.add(servicio_med)
    session.commit()
    session.refresh(servicio_med)
    
    crear_camas_compartidas(
        session=session,
        servicio_id=servicio_med.id,
        codigo_servicio="Med",
        numero_inicio=500,
        cantidad_salas=3,
        camas_por_sala=3
    )
    
    # ----------------------------------------
    # AISLAMIENTO - 3 camas individuales (509-511)
    # ----------------------------------------
    servicio_aisl = Servicio(
        nombre="Aislamiento",
        codigo="Aisl",
        tipo=TipoServicioEnum.AISLAMIENTO,
        hospital_id=hospital_id,
        numero_inicio_camas=509,
        es_uci=False,
        es_uti=False,
        permite_pediatria=False
    )
    session.add(servicio_aisl)
    session.commit()
    session.refresh(servicio_aisl)
    
    crear_camas_individuales(
        session=session,
        servicio_id=servicio_aisl.id,
        codigo_servicio="Aisl",
        numero_inicio=509,
        cantidad_camas=3
    )
    
    # ----------------------------------------
    # CIRUGÍA - 9 camas en 3 salas de 3 (600-602)
    # ----------------------------------------
    servicio_cir = Servicio(
        nombre="Cirugía",
        codigo="Cirug",
        tipo=TipoServicioEnum.CIRUGIA,
        hospital_id=hospital_id,
        numero_inicio_camas=600,
        es_uci=False,
        es_uti=False,
        permite_pediatria=False
    )
    session.add(servicio_cir)
    session.commit()
    session.refresh(servicio_cir)
    
    crear_camas_compartidas(
        session=session,
        servicio_id=servicio_cir.id,
        codigo_servicio="Cirug",
        numero_inicio=600,
        cantidad_salas=3,
        camas_por_sala=3
    )
    
    # ----------------------------------------
    # OBSTETRICIA - 6 camas en 2 salas de 3 (300-301)
    # ----------------------------------------
    servicio_obs = Servicio(
        nombre="Obstetricia",
        codigo="Obst",
        tipo=TipoServicioEnum.OBSTETRICIA,
        hospital_id=hospital_id,
        numero_inicio_camas=300,
        es_uci=False,
        es_uti=False,
        permite_pediatria=False
    )
    session.add(servicio_obs)
    session.commit()
    session.refresh(servicio_obs)
    
    crear_camas_compartidas(
        session=session,
        servicio_id=servicio_obs.id,
        codigo_servicio="Obst",
        numero_inicio=300,
        cantidad_salas=2,
        camas_por_sala=3
    )
    
    # ----------------------------------------
    # PEDIATRÍA - 6 camas en 2 salas de 3 (700-701)
    # ----------------------------------------
    servicio_ped = Servicio(
        nombre="Pediatría",
        codigo="Ped",
        tipo=TipoServicioEnum.PEDIATRIA,
        hospital_id=hospital_id,
        numero_inicio_camas=700,
        es_uci=False,
        es_uti=False,
        permite_pediatria=True
    )
    session.add(servicio_ped)
    session.commit()
    session.refresh(servicio_ped)
    
    crear_camas_compartidas(
        session=session,
        servicio_id=servicio_ped.id,
        codigo_servicio="Ped",
        numero_inicio=700,
        cantidad_salas=2,
        camas_por_sala=3
    )


def crear_servicio_medico_quirurgico(
    session: Session, 
    hospital_id: str, 
    nombre_hospital: str
) -> None:
    """
    Crea el servicio médico-quirúrgico para hospitales periféricos.
    
    16 camas en 4 salas de 4 camas cada una.
    Numeración desde 100.
    """
    servicio_mq = Servicio(
        nombre="Médico-Quirúrgico",
        codigo="MQ",
        tipo=TipoServicioEnum.MEDICO_QUIRURGICO,
        hospital_id=hospital_id,
        numero_inicio_camas=100,
        es_uci=False,
        es_uti=False,
        permite_pediatria=False  # Sin pediatría según especificaciones
    )
    session.add(servicio_mq)
    session.commit()
    session.refresh(servicio_mq)
    
    crear_camas_compartidas(
        session=session,
        servicio_id=servicio_mq.id,
        codigo_servicio="MQ",
        numero_inicio=100,
        cantidad_salas=4,
        camas_por_sala=4
    )


def crear_camas_individuales(
    session: Session,
    servicio_id: str,
    codigo_servicio: str,
    numero_inicio: int,
    cantidad_camas: int
) -> None:
    """
    Crea camas en salas individuales.
    
    Cada cama está en su propia sala individual.
    Identificador: CODIGO-NUMERO (sin letra)
    
    Args:
        session: Sesión de base de datos
        servicio_id: ID del servicio
        codigo_servicio: Código del servicio (UCI, UTI, Aisl)
        numero_inicio: Número de la primera cama
        cantidad_camas: Cantidad de camas a crear
    """
    for i in range(cantidad_camas):
        numero_cama = numero_inicio + i
        
        # Crear sala individual
        sala = Sala(
            numero=i + 1,
            es_individual=True,
            servicio_id=servicio_id,
            sexo_asignado=None  # Las salas individuales no tienen sexo fijo
        )
        session.add(sala)
        session.commit()
        session.refresh(sala)
        
        # Crear cama (sin letra para salas individuales)
        identificador = f"{codigo_servicio}-{numero_cama}"
        
        cama = Cama(
            numero=numero_cama,
            letra=None,
            identificador=identificador,
            sala_id=sala.id,
            estado=EstadoCamaEnum.LIBRE
        )
        session.add(cama)
    
    session.commit()


def crear_camas_compartidas(
    session: Session,
    servicio_id: str,
    codigo_servicio: str,
    numero_inicio: int,
    cantidad_salas: int,
    camas_por_sala: int
) -> None:
    """
    Crea camas en salas compartidas.
    
    Cada sala tiene múltiples camas con letras (A, B, C, D...).
    Identificador: CODIGO-NUMERO-LETRA
    
    Args:
        session: Sesión de base de datos
        servicio_id: ID del servicio
        codigo_servicio: Código del servicio (Med, Cirug, etc)
        numero_inicio: Número de la primera sala
        cantidad_salas: Cantidad de salas a crear
        camas_por_sala: Cantidad de camas por sala
    """
    for i in range(cantidad_salas):
        numero_sala = numero_inicio + i
        
        # Crear sala compartida
        sala = Sala(
            numero=i + 1,
            es_individual=False,
            servicio_id=servicio_id,
            sexo_asignado=None  # Se asigna dinámicamente al primer paciente
        )
        session.add(sala)
        session.commit()
        session.refresh(sala)
        
        # Crear camas con letras
        for j in range(camas_por_sala):
            letra = chr(65 + j)  # A, B, C, D...
            identificador = f"{codigo_servicio}-{numero_sala}-{letra}"
            
            cama = Cama(
                numero=numero_sala,
                letra=letra,
                identificador=identificador,
                sala_id=sala.id,
                estado=EstadoCamaEnum.LIBRE
            )
            session.add(cama)
    
    session.commit()