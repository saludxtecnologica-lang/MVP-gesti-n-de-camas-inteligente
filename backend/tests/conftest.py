"""
Fixtures de pytest para tests.
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from app.core.database import get_session
from main import app


# Engine para tests (SQLite en memoria)
@pytest.fixture(name="engine")
def engine_fixture():
    """Crea un engine de test en memoria."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="session")
def session_fixture(engine):
    """Crea una sesión de test."""
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session):
    """Crea un cliente de test con sesión inyectada."""
    def get_session_override():
        yield session
    
    app.dependency_overrides[get_session] = get_session_override
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()


# Fixtures de datos de prueba

@pytest.fixture
def hospital_data():
    """Datos de hospital de prueba."""
    return {
        "nombre": "Hospital de Prueba",
        "codigo": "TEST",
        "es_central": True
    }


@pytest.fixture
def paciente_data():
    """Datos de paciente de prueba."""
    return {
        "nombre": "Juan Pérez",
        "run": "12345678-5",
        "sexo": "hombre",
        "edad": 45,
        "es_embarazada": False,
        "diagnostico": "Neumonía",
        "tipo_enfermedad": "medica",
        "tipo_aislamiento": "ninguno",
        "requerimientos_no_definen": [],
        "requerimientos_baja": ["tratamiento_ev_frecuente"],
        "requerimientos_uti": [],
        "requerimientos_uci": [],
        "casos_especiales": [],
        "tipo_paciente": "urgencia",
        "hospital_id": ""  # Se llenará en el test
    }


@pytest.fixture
def crear_hospital(session):
    """Factory fixture para crear hospitales."""
    from app.models.hospital import Hospital
    
    def _crear_hospital(nombre="Hospital Test", codigo="TST", es_central=False):
        hospital = Hospital(nombre=nombre, codigo=codigo, es_central=es_central)
        session.add(hospital)
        session.commit()
        session.refresh(hospital)
        return hospital
    
    return _crear_hospital


@pytest.fixture
def crear_servicio(session):
    """Factory fixture para crear servicios."""
    from app.models.servicio import Servicio
    from app.models.enums import TipoServicioEnum
    
    def _crear_servicio(hospital_id, nombre="Medicina", codigo="MED", tipo=TipoServicioEnum.MEDICINA):
        servicio = Servicio(
            nombre=nombre,
            codigo=codigo,
            tipo=tipo,
            hospital_id=hospital_id
        )
        session.add(servicio)
        session.commit()
        session.refresh(servicio)
        return servicio
    
    return _crear_servicio


@pytest.fixture
def crear_sala(session):
    """Factory fixture para crear salas."""
    from app.models.sala import Sala
    
    def _crear_sala(servicio_id, numero=1, es_individual=False):
        sala = Sala(
            numero=numero,
            es_individual=es_individual,
            servicio_id=servicio_id
        )
        session.add(sala)
        session.commit()
        session.refresh(sala)
        return sala
    
    return _crear_sala


@pytest.fixture
def crear_cama(session):
    """Factory fixture para crear camas."""
    from app.models.cama import Cama
    from app.models.enums import EstadoCamaEnum
    
    def _crear_cama(sala_id, numero=101, letra=None, identificador=None, estado=EstadoCamaEnum.LIBRE):
        if identificador is None:
            identificador = f"TEST-{numero}"
            if letra:
                identificador += f"-{letra}"
        
        cama = Cama(
            numero=numero,
            letra=letra,
            identificador=identificador,
            sala_id=sala_id,
            estado=estado
        )
        session.add(cama)
        session.commit()
        session.refresh(cama)
        return cama
    
    return _crear_cama


@pytest.fixture
def crear_paciente(session):
    """Factory fixture para crear pacientes."""
    from app.models.paciente import Paciente
    from app.models.enums import (
        SexoEnum, EdadCategoriaEnum, TipoEnfermedadEnum,
        TipoAislamientoEnum, ComplejidadEnum, TipoPacienteEnum
    )
    
    def _crear_paciente(
        hospital_id,
        nombre="Paciente Test",
        run="11111111-1",
        edad=40,
        tipo_paciente=TipoPacienteEnum.URGENCIA,
        **kwargs
    ):
        defaults = {
            "sexo": SexoEnum.HOMBRE,
            "edad_categoria": EdadCategoriaEnum.ADULTO,
            "es_embarazada": False,
            "diagnostico": "Diagnóstico de prueba",
            "tipo_enfermedad": TipoEnfermedadEnum.MEDICA,
            "tipo_aislamiento": TipoAislamientoEnum.NINGUNO,
            "complejidad_requerida": ComplejidadEnum.BAJA,
        }
        defaults.update(kwargs)
        
        paciente = Paciente(
            nombre=nombre,
            run=run,
            edad=edad,
            tipo_paciente=tipo_paciente,
            hospital_id=hospital_id,
            **defaults
        )
        session.add(paciente)
        session.commit()
        session.refresh(paciente)
        return paciente
    
    return _crear_paciente


@pytest.fixture
def hospital_con_camas(crear_hospital, crear_servicio, crear_sala, crear_cama):
    """Crea un hospital completo con camas para tests."""
    hospital = crear_hospital(nombre="Hospital Completo", codigo="HC")
    servicio = crear_servicio(hospital.id)
    sala = crear_sala(servicio.id)
    
    camas = []
    for i in range(1, 5):
        cama = crear_cama(sala.id, numero=100 + i, identificador=f"MED-10{i}")
        camas.append(cama)
    
    return {
        "hospital": hospital,
        "servicio": servicio,
        "sala": sala,
        "camas": camas
    }
