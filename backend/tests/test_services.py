"""
Tests unitarios para servicios.
"""
import pytest
from datetime import datetime, timedelta

from app.models.enums import (
    ComplejidadEnum, TipoPacienteEnum, EdadCategoriaEnum,
    TipoAislamientoEnum, EstadoCamaEnum
)


class TestAsignacionService:
    """Tests para AsignacionService."""
    
    def test_calcular_complejidad_uci(self, session, crear_hospital, crear_paciente):
        """Test cálculo de complejidad UCI."""
        from app.services.asignacion_service import AsignacionService
        
        hospital = crear_hospital()
        paciente = crear_paciente(hospital.id)
        paciente.requerimientos_uci = '["vmi"]'
        session.add(paciente)
        session.commit()
        
        service = AsignacionService(session)
        complejidad = service.calcular_complejidad(paciente)
        
        assert complejidad == ComplejidadEnum.ALTA
    
    def test_calcular_complejidad_uti(self, session, crear_hospital, crear_paciente):
        """Test cálculo de complejidad UTI."""
        from app.services.asignacion_service import AsignacionService
        
        hospital = crear_hospital()
        paciente = crear_paciente(hospital.id)
        paciente.requerimientos_uti = '["droga_vasoactiva"]'
        session.add(paciente)
        session.commit()
        
        service = AsignacionService(session)
        complejidad = service.calcular_complejidad(paciente)
        
        assert complejidad == ComplejidadEnum.MEDIA
    
    def test_calcular_complejidad_baja(self, session, crear_hospital, crear_paciente):
        """Test cálculo de complejidad baja."""
        from app.services.asignacion_service import AsignacionService
        
        hospital = crear_hospital()
        paciente = crear_paciente(hospital.id)
        paciente.requerimientos_baja = '["tratamiento_ev"]'
        session.add(paciente)
        session.commit()
        
        service = AsignacionService(session)
        complejidad = service.calcular_complejidad(paciente)
        
        assert complejidad == ComplejidadEnum.BAJA
    
    def test_calcular_complejidad_sin_requerimientos(self, session, crear_hospital, crear_paciente):
        """Test cálculo de complejidad sin requerimientos."""
        from app.services.asignacion_service import AsignacionService
        
        hospital = crear_hospital()
        paciente = crear_paciente(hospital.id)
        session.add(paciente)
        session.commit()
        
        service = AsignacionService(session)
        complejidad = service.calcular_complejidad(paciente)
        
        assert complejidad == ComplejidadEnum.NINGUNA


class TestPrioridadService:
    """Tests para PrioridadService."""
    
    def test_calcular_prioridad_urgencia(self, session, crear_hospital, crear_paciente):
        """Test prioridad de paciente de urgencia."""
        from app.services.prioridad_service import PrioridadService
        
        hospital = crear_hospital()
        paciente = crear_paciente(
            hospital.id,
            tipo_paciente=TipoPacienteEnum.URGENCIA
        )
        
        service = PrioridadService(session)
        prioridad = service.calcular_prioridad(paciente)
        
        # Urgencia tiene peso 100
        assert prioridad >= 100
    
    def test_calcular_prioridad_ambulatorio(self, session, crear_hospital, crear_paciente):
        """Test prioridad de paciente ambulatorio."""
        from app.services.prioridad_service import PrioridadService
        
        hospital = crear_hospital()
        paciente = crear_paciente(
            hospital.id,
            tipo_paciente=TipoPacienteEnum.AMBULATORIO
        )
        
        service = PrioridadService(session)
        prioridad = service.calcular_prioridad(paciente)
        
        # Ambulatorio tiene peso 40
        assert prioridad >= 40
        assert prioridad < 100  # Menor que urgencia
    
    def test_prioridad_adulto_mayor_bonus(self, session, crear_hospital, crear_paciente):
        """Test que adulto mayor tiene bonus de prioridad."""
        from app.services.prioridad_service import PrioridadService
        
        hospital = crear_hospital()
        
        # Paciente adulto
        paciente_adulto = crear_paciente(
            hospital.id,
            nombre="Adulto",
            run="11111111-1",
            edad=40
        )
        paciente_adulto.edad_categoria = EdadCategoriaEnum.ADULTO
        session.add(paciente_adulto)
        
        # Paciente adulto mayor
        paciente_mayor = crear_paciente(
            hospital.id,
            nombre="Mayor",
            run="22222222-2",
            edad=70
        )
        paciente_mayor.edad_categoria = EdadCategoriaEnum.ADULTO_MAYOR
        session.add(paciente_mayor)
        session.commit()
        
        service = PrioridadService(session)
        prioridad_adulto = service.calcular_prioridad(paciente_adulto)
        prioridad_mayor = service.calcular_prioridad(paciente_mayor)
        
        # Adulto mayor debe tener mayor prioridad
        assert prioridad_mayor > prioridad_adulto
    
    def test_prioridad_aislamiento_bonus(self, session, crear_hospital, crear_paciente):
        """Test que aislamiento aéreo tiene bonus."""
        from app.services.prioridad_service import PrioridadService
        
        hospital = crear_hospital()
        
        paciente_sin_aislamiento = crear_paciente(
            hospital.id,
            nombre="Sin Aislamiento",
            run="11111111-1"
        )
        paciente_sin_aislamiento.tipo_aislamiento = TipoAislamientoEnum.NINGUNO
        session.add(paciente_sin_aislamiento)
        
        paciente_aereo = crear_paciente(
            hospital.id,
            nombre="Aéreo",
            run="22222222-2"
        )
        paciente_aereo.tipo_aislamiento = TipoAislamientoEnum.AEREO
        session.add(paciente_aereo)
        session.commit()
        
        service = PrioridadService(session)
        prioridad_normal = service.calcular_prioridad(paciente_sin_aislamiento)
        prioridad_aereo = service.calcular_prioridad(paciente_aereo)
        
        assert prioridad_aereo > prioridad_normal
    
    def test_explicar_prioridad(self, session, crear_hospital, crear_paciente):
        """Test explicación de prioridad."""
        from app.services.prioridad_service import PrioridadService
        
        hospital = crear_hospital()
        paciente = crear_paciente(hospital.id)
        
        service = PrioridadService(session)
        explicacion = service.explicar_prioridad(paciente)
        
        assert explicacion.puntaje_total > 0
        assert len(explicacion.detalles) > 0


class TestLimpiezaService:
    """Tests para LimpiezaService."""
    
    def test_iniciar_limpieza(self, session, hospital_con_camas):
        """Test iniciar limpieza de cama."""
        from app.services.limpieza_service import LimpiezaService
        
        cama = hospital_con_camas["camas"][0]
        cama.estado = EstadoCamaEnum.OCUPADA
        session.add(cama)
        session.commit()
        
        service = LimpiezaService(session)
        cama_actualizada = service.iniciar_limpieza(cama.id)
        
        assert cama_actualizada.estado == EstadoCamaEnum.EN_LIMPIEZA
        assert cama_actualizada.limpieza_inicio is not None
    
    def test_finalizar_limpieza(self, session, hospital_con_camas):
        """Test finalizar limpieza de cama."""
        from app.services.limpieza_service import LimpiezaService
        
        cama = hospital_con_camas["camas"][0]
        cama.estado = EstadoCamaEnum.EN_LIMPIEZA
        cama.limpieza_inicio = datetime.utcnow()
        session.add(cama)
        session.commit()
        
        service = LimpiezaService(session)
        cama_actualizada = service.finalizar_limpieza(cama.id)
        
        assert cama_actualizada.estado == EstadoCamaEnum.LIBRE
        assert cama_actualizada.limpieza_inicio is None
    
    def test_procesar_camas_en_limpieza(self, session, hospital_con_camas):
        """Test procesamiento automático de camas en limpieza."""
        from app.services.limpieza_service import LimpiezaService
        
        camas = hospital_con_camas["camas"]
        
        # Poner cama 0 en limpieza hace 2 minutos
        camas[0].estado = EstadoCamaEnum.EN_LIMPIEZA
        camas[0].limpieza_inicio = datetime.utcnow() - timedelta(seconds=120)
        session.add(camas[0])
        
        # Poner cama 1 en limpieza recién
        camas[1].estado = EstadoCamaEnum.EN_LIMPIEZA
        camas[1].limpieza_inicio = datetime.utcnow()
        session.add(camas[1])
        
        session.commit()
        
        service = LimpiezaService(session)
        resultado = service.procesar_camas_en_limpieza(tiempo_limpieza_segundos=60)
        
        # Solo cama 0 debería haberse liberado
        assert len(resultado.camas_liberadas) == 1
        assert camas[0].id in resultado.camas_liberadas
        
        session.refresh(camas[0])
        session.refresh(camas[1])
        
        assert camas[0].estado == EstadoCamaEnum.LIBRE
        assert camas[1].estado == EstadoCamaEnum.EN_LIMPIEZA
    
    def test_tiempo_restante_limpieza(self, session, hospital_con_camas):
        """Test cálculo de tiempo restante de limpieza."""
        from app.services.limpieza_service import LimpiezaService
        
        cama = hospital_con_camas["camas"][0]
        cama.estado = EstadoCamaEnum.EN_LIMPIEZA
        cama.limpieza_inicio = datetime.utcnow() - timedelta(seconds=30)
        session.add(cama)
        session.commit()
        
        service = LimpiezaService(session)
        restante = service.tiempo_restante_limpieza(cama, tiempo_limpieza_segundos=60)
        
        # Debería quedar aproximadamente 30 segundos
        assert 25 <= restante <= 35


class TestAltaService:
    """Tests para AltaService."""
    
    def test_verificar_alta_sugerida_sin_requerimientos(self, session, crear_hospital, crear_paciente):
        """Test que paciente sin requerimientos puede tener alta sugerida."""
        from app.services.alta_service import AltaService
        
        hospital = crear_hospital()
        paciente = crear_paciente(hospital.id)
        paciente.requerimientos_baja = "[]"
        paciente.requerimientos_uti = "[]"
        paciente.requerimientos_uci = "[]"
        paciente.casos_especiales = "[]"
        session.add(paciente)
        session.commit()
        
        service = AltaService(session)
        puede_alta = service.verificar_alta_sugerida(paciente)
        
        assert puede_alta == True
    
    def test_verificar_alta_sugerida_con_requerimientos(self, session, crear_hospital, crear_paciente):
        """Test que paciente con requerimientos no puede tener alta sugerida."""
        from app.services.alta_service import AltaService
        
        hospital = crear_hospital()
        paciente = crear_paciente(hospital.id)
        paciente.requerimientos_baja = '["tratamiento_ev"]'
        session.add(paciente)
        session.commit()
        
        service = AltaService(session)
        puede_alta = service.verificar_alta_sugerida(paciente)
        
        assert puede_alta == False
