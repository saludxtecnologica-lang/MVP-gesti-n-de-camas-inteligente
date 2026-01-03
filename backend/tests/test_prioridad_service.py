"""
Tests del Sistema de Priorización v3.1

Tests unitarios para validar el correcto funcionamiento del sistema
de priorización, incluyendo IVC, FRC, tiempo no lineal y rescate.

Ubicación: tests/test_prioridad_service.py

Usa las fixtures definidas en conftest.py
"""
import pytest
from datetime import datetime, timedelta

from app.services.prioridad_service import (
    PrioridadService,
    ExplicacionPrioridad,
    gestor_colas_global,
    _normalizar_tipo_paciente,
    _normalizar_complejidad,
)
from app.models.enums import (
    TipoPacienteEnum,
    ComplejidadEnum,
    TipoAislamientoEnum,
    EdadCategoriaEnum,
    SexoEnum,
    TipoEnfermedadEnum,
)


# ============================================
# TESTS DE TIPO EFECTIVO
# ============================================

class TestTipoEfectivo:
    """Tests para la determinación del tipo efectivo de paciente."""
    
    def test_paciente_con_cama_es_hospitalizado(self, session, crear_hospital, crear_servicio, crear_sala, crear_cama, crear_paciente):
        """Un paciente con cama asignada debe ser tratado como hospitalizado."""
        hospital = crear_hospital()
        servicio = crear_servicio(hospital.id)
        sala = crear_sala(servicio.id)
        cama = crear_cama(sala.id)
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            tipo_paciente=TipoPacienteEnum.URGENCIA,
            cama_id=cama.id  # Tiene cama asignada
        )
        
        service = PrioridadService(session)
        tipo_efectivo = service._obtener_tipo_efectivo(paciente)
        
        assert tipo_efectivo == 'hospitalizado'
    
    def test_ambulatorio_estabilizacion_es_urgencia(self, session, crear_hospital, crear_paciente):
        """Un ambulatorio por estabilización clínica debe tratarse como urgencia."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            tipo_paciente=TipoPacienteEnum.AMBULATORIO,
            motivo_ingreso_ambulatorio='estabilizacion_clinica'
        )
        
        service = PrioridadService(session)
        tipo_efectivo = service._obtener_tipo_efectivo(paciente)
        
        assert tipo_efectivo == 'urgencia'
    
    def test_ambulatorio_tratamiento_sigue_siendo_ambulatorio(self, session, crear_hospital, crear_paciente):
        """Un ambulatorio por tratamiento debe mantener su tipo."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            tipo_paciente=TipoPacienteEnum.AMBULATORIO,
            motivo_ingreso_ambulatorio='tratamiento'
        )
        
        service = PrioridadService(session)
        tipo_efectivo = service._obtener_tipo_efectivo(paciente)
        
        assert tipo_efectivo == 'ambulatorio'
    
    def test_urgencia_sin_cama_sigue_siendo_urgencia(self, session, crear_hospital, crear_paciente):
        """Una urgencia sin cama debe mantener su tipo."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            tipo_paciente=TipoPacienteEnum.URGENCIA,
            cama_id=None
        )
        
        service = PrioridadService(session)
        tipo_efectivo = service._obtener_tipo_efectivo(paciente)
        
        assert tipo_efectivo == 'urgencia'


# ============================================
# TESTS DE IVC (Índice de Vulnerabilidad Clínica)
# ============================================

class TestIVC:
    """Tests para el Índice de Vulnerabilidad Clínica."""
    
    def test_ivc_edad_muy_mayor(self, session, crear_hospital, crear_paciente):
        """Paciente ≥80 años debe recibir bonus máximo de edad."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            edad=85,
            edad_categoria=EdadCategoriaEnum.ADULTO_MAYOR
        )
        
        service = PrioridadService(session)
        ivc, detalles = service._calcular_ivc(paciente)
        
        assert any('≥80' in d for d in detalles)
        assert ivc >= 25  # Bonus por edad muy mayor
    
    def test_ivc_edad_70_79(self, session, crear_hospital, crear_paciente):
        """Paciente 70-79 años debe recibir bonus correspondiente."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            edad=75,
            edad_categoria=EdadCategoriaEnum.ADULTO_MAYOR
        )
        
        service = PrioridadService(session)
        ivc, detalles = service._calcular_ivc(paciente)
        
        assert any('70-79' in d for d in detalles)
        assert ivc >= 20
    
    def test_ivc_edad_infante(self, session, crear_hospital, crear_paciente):
        """Paciente <5 años debe recibir bonus de infante."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            edad=3,
            edad_categoria=EdadCategoriaEnum.PEDIATRICO
        )
        
        service = PrioridadService(session)
        ivc, detalles = service._calcular_ivc(paciente)
        
        assert any('Infante' in d or '<5' in d for d in detalles)
        assert ivc >= 20
    
    def test_ivc_edad_nino(self, session, crear_hospital, crear_paciente):
        """Paciente 5-14 años debe recibir bonus de niño."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            edad=10,
            edad_categoria=EdadCategoriaEnum.PEDIATRICO
        )
        
        service = PrioridadService(session)
        ivc, detalles = service._calcular_ivc(paciente)
        
        assert any('Niño' in d or '5-14' in d for d in detalles)
        assert ivc >= 15
    
    def test_ivc_monitorizacion_activa(self, session, crear_hospital, crear_paciente):
        """Paciente con monitorización activa debe recibir bonus."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            edad=45,
            monitorizacion_inicio=datetime.utcnow(),
            monitorizacion_tiempo_horas=4
        )
        
        service = PrioridadService(session)
        ivc, detalles = service._calcular_ivc(paciente)
        
        assert any('Monitorización' in d for d in detalles)
        assert ivc >= 20
    
    def test_ivc_observacion_activa(self, session, crear_hospital, crear_paciente):
        """Paciente con observación activa debe recibir bonus."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            edad=45,
            observacion_inicio=datetime.utcnow(),
            observacion_tiempo_horas=6
        )
        
        service = PrioridadService(session)
        ivc, detalles = service._calcular_ivc(paciente)
        
        assert any('Observación' in d for d in detalles)
        assert ivc >= 15
    
    def test_ivc_embarazada(self, session, crear_hospital, crear_paciente):
        """Paciente embarazada debe recibir bonus."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            edad=30,
            sexo=SexoEnum.MUJER,
            es_embarazada=True
        )
        
        service = PrioridadService(session)
        ivc, detalles = service._calcular_ivc(paciente)
        
        assert any('Embarazada' in d for d in detalles)
        assert ivc >= 20
    
    def test_ivc_complejidad_alta(self, session, crear_hospital, crear_paciente):
        """Paciente con complejidad alta (UCI) debe recibir bonus máximo."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            edad=45,
            complejidad_requerida=ComplejidadEnum.ALTA
        )
        
        service = PrioridadService(session)
        ivc, detalles = service._calcular_ivc(paciente)
        
        assert any('UCI' in d or 'Complejidad' in d for d in detalles)
        assert ivc >= 30
    
    def test_ivc_complejidad_media(self, session, crear_hospital, crear_paciente):
        """Paciente con complejidad media (UTI) debe recibir bonus correspondiente."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            edad=45,
            complejidad_requerida=ComplejidadEnum.MEDIA
        )
        
        service = PrioridadService(session)
        ivc, detalles = service._calcular_ivc(paciente)
        
        assert any('UTI' in d for d in detalles)
        assert ivc >= 20
    
    def test_ivc_aislamiento_aereo(self, session, crear_hospital, crear_paciente):
        """Paciente con aislamiento aéreo debe recibir bonus."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            edad=45,
            tipo_aislamiento=TipoAislamientoEnum.AEREO
        )
        
        service = PrioridadService(session)
        ivc, detalles = service._calcular_ivc(paciente)
        
        assert any('aéreo' in d.lower() or 'aereo' in d.lower() for d in detalles)
        assert ivc >= 20


# ============================================
# TESTS DE FRC (Factor de Requerimientos Críticos)
# ============================================

class TestFRC:
    """Tests para el Factor de Requerimientos Críticos."""
    
    def test_frc_drogas_vasoactivas(self, session, crear_hospital, crear_paciente):
        """Paciente con drogas vasoactivas debe recibir bonus."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            requerimientos_uci=['drogas_vasoactivas', 'monitoreo_invasivo']
        )
        
        service = PrioridadService(session)
        frc, detalles = service._calcular_frc(paciente)
        
        assert any('vasoactivas' in d.lower() for d in detalles)
        assert frc >= 15
    
    def test_frc_noradrenalina(self, session, crear_hospital, crear_paciente):
        """Paciente con noradrenalina debe detectarse como drogas vasoactivas."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            requerimientos_uci=['noradrenalina']
        )
        
        service = PrioridadService(session)
        frc, detalles = service._calcular_frc(paciente)
        
        assert any('vasoactivas' in d.lower() for d in detalles)
        assert frc >= 15
    
    def test_frc_sedacion(self, session, crear_hospital, crear_paciente):
        """Paciente con sedación debe recibir bonus."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            requerimientos_uci=['sedacion', 'propofol']
        )
        
        service = PrioridadService(session)
        frc, detalles = service._calcular_frc(paciente)
        
        assert any('Sedación' in d for d in detalles)
        assert frc >= 12
    
    def test_frc_oxigeno_cnaf(self, session, crear_hospital, crear_paciente):
        """Paciente con CNAF debe recibir bonus por oxígeno."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            requerimientos_uti=['cnaf', 'monitoreo']
        )
        
        service = PrioridadService(session)
        frc, detalles = service._calcular_frc(paciente)
        
        assert any('Oxígeno' in d for d in detalles)
        assert frc >= 10
    
    def test_frc_oxigeno_naricera(self, session, crear_hospital, crear_paciente):
        """Paciente con naricera debe recibir bonus por oxígeno."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            requerimientos_baja=['naricera']
        )
        
        service = PrioridadService(session)
        frc, detalles = service._calcular_frc(paciente)
        
        assert any('Oxígeno' in d for d in detalles)
        assert frc >= 10
    
    def test_frc_procedimiento_invasivo_campo(self, session, crear_hospital, crear_paciente):
        """Paciente con campo procedimiento_invasivo=True debe recibir bonus."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            procedimiento_invasivo=True
        )
        
        service = PrioridadService(session)
        frc, detalles = service._calcular_frc(paciente)
        
        assert any('invasivo' in d.lower() for d in detalles)
        assert frc >= 10
    
    def test_frc_aspiracion_secreciones(self, session, crear_hospital, crear_paciente):
        """Paciente con aspiración de secreciones debe recibir bonus."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            requerimientos_uti=['aspiracion_secreciones']
        )
        
        service = PrioridadService(session)
        frc, detalles = service._calcular_frc(paciente)
        
        assert any('Aspiración' in d for d in detalles)
        assert frc >= 10
    
    def test_frc_acumulativo(self, session, crear_hospital, crear_paciente):
        """FRC debe ser acumulativo para múltiples requerimientos."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            requerimientos_uci=['noradrenalina', 'sedacion'],
            requerimientos_uti=['cnaf'],
            procedimiento_invasivo=True
        )
        
        service = PrioridadService(session)
        frc, detalles = service._calcular_frc(paciente)
        
        # Debe acumular: vasoactivas(15) + sedación(12) + oxígeno(10) + procedimiento(10) = 47
        assert frc >= 47
        
        # Debe tener al menos 4 detalles de FRC
        frc_detalles = [d for d in detalles if 'FRC' in d]
        assert len(frc_detalles) >= 4
    
    def test_frc_sin_requerimientos_criticos(self, session, crear_hospital, crear_paciente):
        """Paciente sin requerimientos críticos debe tener FRC = 0."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            requerimientos_baja=['tratamiento_ev_frecuente']
        )
        
        service = PrioridadService(session)
        frc, detalles = service._calcular_frc(paciente)
        
        assert frc == 0
        assert len(detalles) == 0


# ============================================
# TESTS DE TIEMPO NO LINEAL
# ============================================

class TestTiempoNoLineal:
    """Tests para el cálculo de tiempo no lineal."""
    
    def test_tiempo_urgencia_fase1(self, session, crear_hospital, crear_paciente):
        """Urgencia en fase 1 (<4h) debe usar tasa baja."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            tipo_paciente=TipoPacienteEnum.URGENCIA,
            tiempo_espera_min=120  # 2 horas
        )
        
        service = PrioridadService(session)
        pts, desc = service._calcular_tiempo_no_lineal(paciente)
        
        # 2h * 3pts/h = 6 pts
        assert pts == 6
        assert 'urgencia' in desc.lower()
    
    def test_tiempo_urgencia_fase2(self, session, crear_hospital, crear_paciente):
        """Urgencia en fase 2 (4-8h) debe usar tasa media."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            tipo_paciente=TipoPacienteEnum.URGENCIA,
            tiempo_espera_min=360  # 6 horas
        )
        
        service = PrioridadService(session)
        pts, desc = service._calcular_tiempo_no_lineal(paciente)
        
        # 4h * 3pts + 2h * 5pts = 12 + 10 = 22 pts
        assert pts == 22
    
    def test_tiempo_urgencia_fase3_con_boost(self, session, crear_hospital, crear_paciente):
        """Urgencia en fase 3 (>8h) debe incluir boost."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            tipo_paciente=TipoPacienteEnum.URGENCIA,
            tiempo_espera_min=600  # 10 horas
        )
        
        service = PrioridadService(session)
        pts, desc = service._calcular_tiempo_no_lineal(paciente)
        
        # 4h * 3pts + 4h * 5pts + 2h * 8pts + boost(40) = 12 + 20 + 16 + 40 = 88 pts
        assert pts == 88
    
    def test_tiempo_derivado_fase1(self, session, crear_hospital, crear_paciente):
        """Derivado en fase 1 (<12h) debe usar tasa correspondiente."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            tipo_paciente=TipoPacienteEnum.DERIVADO,
            tiempo_espera_min=360  # 6 horas
        )
        
        service = PrioridadService(session)
        pts, desc = service._calcular_tiempo_no_lineal(paciente)
        
        # 6h * 2pts/h = 12 pts
        assert pts == 12
        assert 'derivado' in desc.lower()
    
    def test_tiempo_ambulatorio_fase1(self, session, crear_hospital, crear_paciente):
        """Ambulatorio en fase 1 (<48h) debe usar tasa baja."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            tipo_paciente=TipoPacienteEnum.AMBULATORIO,
            tiempo_espera_min=1440  # 24 horas
        )
        
        service = PrioridadService(session)
        pts, desc = service._calcular_tiempo_no_lineal(paciente)
        
        # 24h * 1pts/h = 24 pts
        assert pts == 24
        assert 'ambulatorio' in desc.lower()
    
    def test_tiempo_ambulatorio_mas_lento_que_urgencia(self, session, crear_hospital, crear_paciente):
        """Ambulatorio debe acumular tiempo más lento que urgencia."""
        hospital = crear_hospital()
        
        paciente_urgencia = crear_paciente(
            hospital_id=hospital.id,
            nombre="Urgencia Test",
            run="11111111-1",
            tipo_paciente=TipoPacienteEnum.URGENCIA,
            tiempo_espera_min=120  # 2 horas
        )
        
        paciente_ambulatorio = crear_paciente(
            hospital_id=hospital.id,
            nombre="Ambulatorio Test",
            run="22222222-2",
            tipo_paciente=TipoPacienteEnum.AMBULATORIO,
            tiempo_espera_min=120  # 2 horas
        )
        
        service = PrioridadService(session)
        
        pts_urgencia, _ = service._calcular_tiempo_no_lineal(paciente_urgencia)
        pts_ambulatorio, _ = service._calcular_tiempo_no_lineal(paciente_ambulatorio)
        
        # Urgencia: 2h * 3pts = 6
        # Ambulatorio: 2h * 1pts = 2
        assert pts_urgencia > pts_ambulatorio
        assert pts_urgencia == 6
        assert pts_ambulatorio == 2


# ============================================
# TESTS DE MECANISMO DE RESCATE
# ============================================

class TestRescate:
    """Tests para el mecanismo de rescate."""
    
    def test_rescate_urgencia_mayor_24h(self, session, crear_hospital, crear_paciente):
        """Urgencia con >24h debe activar rescate."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            tipo_paciente=TipoPacienteEnum.URGENCIA,
            tiempo_espera_min=1500  # 25 horas
        )
        
        service = PrioridadService(session)
        debe_rescate = service._debe_activar_rescate(paciente)
        
        assert debe_rescate is True
    
    def test_no_rescate_urgencia_menor_24h(self, session, crear_hospital, crear_paciente):
        """Urgencia con <24h no debe activar rescate."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            tipo_paciente=TipoPacienteEnum.URGENCIA,
            tiempo_espera_min=1200  # 20 horas
        )
        
        service = PrioridadService(session)
        debe_rescate = service._debe_activar_rescate(paciente)
        
        assert debe_rescate is False
    
    def test_rescate_derivado_mayor_48h(self, session, crear_hospital, crear_paciente):
        """Derivado con >48h debe activar rescate."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            tipo_paciente=TipoPacienteEnum.DERIVADO,
            tiempo_espera_min=3000  # 50 horas
        )
        
        service = PrioridadService(session)
        debe_rescate = service._debe_activar_rescate(paciente)
        
        assert debe_rescate is True
    
    def test_rescate_ambulatorio_mayor_7_dias(self, session, crear_hospital, crear_paciente):
        """Ambulatorio con >7 días debe activar rescate."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            tipo_paciente=TipoPacienteEnum.AMBULATORIO,
            tiempo_espera_min=10200  # 170 horas (~7.08 días)
        )
        
        service = PrioridadService(session)
        debe_rescate = service._debe_activar_rescate(paciente)
        
        assert debe_rescate is True
    
    def test_rescate_devuelve_500(self, session, crear_hospital, crear_paciente):
        """Paciente en rescate debe recibir prioridad 500."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            tipo_paciente=TipoPacienteEnum.URGENCIA,
            tiempo_espera_min=1500  # 25 horas (>24h rescate)
        )
        
        service = PrioridadService(session)
        prioridad = service.calcular_prioridad(paciente)
        
        assert prioridad == 500
    
    def test_hospitalizado_no_tiene_rescate(self, session, crear_hospital, crear_servicio, crear_sala, crear_cama, crear_paciente):
        """Hospitalizado no debe activar rescate (ya tiene prioridad máxima)."""
        hospital = crear_hospital()
        servicio = crear_servicio(hospital.id)
        sala = crear_sala(servicio.id)
        cama = crear_cama(sala.id)
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            tipo_paciente=TipoPacienteEnum.URGENCIA,
            cama_id=cama.id,  # Tiene cama = hospitalizado
            tiempo_espera_min=3000  # 50 horas
        )
        
        service = PrioridadService(session)
        debe_rescate = service._debe_activar_rescate(paciente)
        
        # Hospitalizado no tiene rescate (ya tiene prioridad máxima)
        assert debe_rescate is False


# ============================================
# TESTS DE CÁLCULO COMPLETO DE PRIORIDAD
# ============================================

class TestCalculoPrioridad:
    """Tests para el cálculo completo de prioridad."""
    
    def test_prioridad_basica_urgencia(self, session, crear_hospital, crear_paciente):
        """Test de prioridad básica para urgencia."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            tipo_paciente=TipoPacienteEnum.URGENCIA,
            edad=45,
            complejidad_requerida=ComplejidadEnum.BAJA,
            tiempo_espera_min=60  # 1 hora
        )
        
        service = PrioridadService(session)
        prioridad = service.calcular_prioridad(paciente)
        
        # Base urgencia (100) + IVC complejidad baja (5) + tiempo (1h * 3 = 3) = 108
        assert prioridad >= 100
        assert prioridad < 200  # No debe llegar a hospitalizado
    
    def test_prioridad_hospitalizado_mayor_que_urgencia(self, session, crear_hospital, crear_servicio, crear_sala, crear_cama, crear_paciente):
        """Hospitalizado debe tener mayor prioridad base que urgencia."""
        hospital = crear_hospital()
        servicio = crear_servicio(hospital.id)
        sala = crear_sala(servicio.id)
        cama = crear_cama(sala.id)
        
        paciente_hospitalizado = crear_paciente(
            hospital_id=hospital.id,
            nombre="Hospitalizado Test",
            run="11111111-1",
            tipo_paciente=TipoPacienteEnum.URGENCIA,
            cama_id=cama.id,
            edad=45,
            tiempo_espera_min=60
        )
        
        paciente_urgencia = crear_paciente(
            hospital_id=hospital.id,
            nombre="Urgencia Test",
            run="22222222-2",
            tipo_paciente=TipoPacienteEnum.URGENCIA,
            cama_id=None,
            edad=45,
            tiempo_espera_min=60
        )
        
        service = PrioridadService(session)
        
        prioridad_hosp = service.calcular_prioridad(paciente_hospitalizado)
        prioridad_urg = service.calcular_prioridad(paciente_urgencia)
        
        # Hospitalizado (200) > Urgencia (100)
        assert prioridad_hosp > prioridad_urg
        assert prioridad_hosp >= 200


# ============================================
# TESTS DE CASOS DE EJEMPLO DEL DOCUMENTO
# ============================================

class TestCasosEjemploDocumento:
    """Tests que replican los ejemplos del documento de propuesta."""
    
    def test_caso_desempate_frc(self, session, crear_hospital, crear_paciente):
        """
        Dos pacientes UTI iguales, uno con requerimientos críticos.
        El que tiene FRC debe tener mayor prioridad.
        """
        hospital = crear_hospital()
        
        # Paciente A: Solo monitoreo (sin requerimientos críticos)
        paciente_a = crear_paciente(
            hospital_id=hospital.id,
            nombre="Paciente A",
            run="11111111-1",
            tipo_paciente=TipoPacienteEnum.URGENCIA,
            edad=45,
            complejidad_requerida=ComplejidadEnum.MEDIA,
            tiempo_espera_min=360,  # 6 horas
            requerimientos_uti=['monitoreo_continuo']
        )
        
        # Paciente B: Con soporte activo (requerimientos críticos)
        paciente_b = crear_paciente(
            hospital_id=hospital.id,
            nombre="Paciente B",
            run="22222222-2",
            tipo_paciente=TipoPacienteEnum.URGENCIA,
            edad=45,
            complejidad_requerida=ComplejidadEnum.MEDIA,
            tiempo_espera_min=360,  # 6 horas
            requerimientos_uci=['noradrenalina', 'sedacion'],
            requerimientos_uti=['cnaf']
        )
        
        service = PrioridadService(session)
        
        prioridad_a = service.calcular_prioridad(paciente_a)
        prioridad_b = service.calcular_prioridad(paciente_b)
        
        # Paciente B debe tener mayor prioridad por FRC
        assert prioridad_b > prioridad_a
        
        # La diferencia debe ser significativa (FRC aporta ~37 puntos)
        diferencia = prioridad_b - prioridad_a
        assert diferencia >= 30
    
    def test_caso_ambulatorio_estabilizacion_vs_tratamiento(self, session, crear_hospital, crear_paciente):
        """
        Ambulatorio por estabilización debe tener mayor prioridad
        que ambulatorio por tratamiento.
        """
        hospital = crear_hospital()
        
        # Paciente con tratamiento programado
        paciente_tratamiento = crear_paciente(
            hospital_id=hospital.id,
            nombre="Tratamiento Test",
            run="11111111-1",
            tipo_paciente=TipoPacienteEnum.AMBULATORIO,
            motivo_ingreso_ambulatorio='tratamiento',
            edad=50,
            complejidad_requerida=ComplejidadEnum.BAJA,
            tiempo_espera_min=120  # 2 horas
        )
        
        # Paciente con estabilización clínica
        paciente_estabilizacion = crear_paciente(
            hospital_id=hospital.id,
            nombre="Estabilización Test",
            run="22222222-2",
            tipo_paciente=TipoPacienteEnum.AMBULATORIO,
            motivo_ingreso_ambulatorio='estabilizacion_clinica',
            edad=50,
            complejidad_requerida=ComplejidadEnum.BAJA,
            tiempo_espera_min=120  # 2 horas
        )
        
        service = PrioridadService(session)
        
        prioridad_tratamiento = service.calcular_prioridad(paciente_tratamiento)
        prioridad_estabilizacion = service.calcular_prioridad(paciente_estabilizacion)
        
        # Estabilización debe tener mayor prioridad (tipo efectivo = urgencia)
        assert prioridad_estabilizacion > prioridad_tratamiento
        
        # La diferencia debe ser al menos 35 (100 urgencia - 60 ambulatorio + diferencia tiempo)
        diferencia = prioridad_estabilizacion - prioridad_tratamiento
        assert diferencia >= 35
    
    def test_caso_adulto_mayor_con_multiples_factores(self, session, crear_hospital, crear_paciente):
        """
        Adulto mayor con múltiples factores de riesgo debe acumular puntos.
        """
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            tipo_paciente=TipoPacienteEnum.URGENCIA,
            edad=82,  # ≥80 años
            edad_categoria=EdadCategoriaEnum.ADULTO_MAYOR,
            complejidad_requerida=ComplejidadEnum.MEDIA,  # UTI
            tiempo_espera_min=360,  # 6 horas
            monitorizacion_inicio=datetime.utcnow(),
            monitorizacion_tiempo_horas=4,
            requerimientos_uci=['noradrenalina'],  # Drogas vasoactivas
            requerimientos_uti=['cnaf']  # Oxígeno
        )
        
        service = PrioridadService(session)
        prioridad = service.calcular_prioridad(paciente)
        
        # Debe acumular:
        # - Base urgencia: 100
        # - IVC edad ≥80: 25
        # - IVC monitorización: 20
        # - IVC complejidad UTI: 20
        # - FRC drogas vasoactivas: 15
        # - FRC oxígeno: 10
        # - Tiempo 6h: 22
        # Total mínimo esperado: ~212
        assert prioridad >= 200


# ============================================
# TESTS DE EXPLICAR PRIORIDAD
# ============================================

class TestExplicarPrioridad:
    """Tests para el método explicar_prioridad."""
    
    def test_explicar_incluye_detalles(self, session, crear_hospital, crear_paciente):
        """La explicación debe incluir detalles del cálculo."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            tipo_paciente=TipoPacienteEnum.URGENCIA,
            edad=75,
            complejidad_requerida=ComplejidadEnum.MEDIA,
            tiempo_espera_min=360,
            requerimientos_uti=['cnaf']
        )
        
        service = PrioridadService(session)
        explicacion = service.explicar_prioridad(paciente)
        
        # Debe tener puntaje total
        assert explicacion.puntaje_total > 0
        
        # Debe tener detalles
        assert len(explicacion.detalles) > 0
        
        # Debe incluir tipo efectivo
        assert explicacion.tipo_efectivo == 'urgencia'
        
        # Debe incluir IVC y FRC
        assert explicacion.puntaje_ivc > 0
        assert explicacion.puntaje_frc >= 0
    
    def test_explicar_rescate_indica_claramente(self, session, crear_hospital, crear_paciente):
        """Paciente en rescate debe indicarlo en la explicación."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            tipo_paciente=TipoPacienteEnum.URGENCIA,
            tiempo_espera_min=1500  # >24h = rescate
        )
        
        service = PrioridadService(session)
        explicacion = service.explicar_prioridad(paciente)
        
        assert explicacion.es_rescate is True
        assert explicacion.puntaje_total == 500
        assert any('RESCATE' in d for d in explicacion.detalles)
    
    def test_explicar_tipo_efectivo_diferente(self, session, crear_hospital, crear_paciente):
        """Debe mostrar cuando tipo efectivo difiere del original."""
        hospital = crear_hospital()
        
        paciente = crear_paciente(
            hospital_id=hospital.id,
            tipo_paciente=TipoPacienteEnum.AMBULATORIO,
            motivo_ingreso_ambulatorio='estabilizacion_clinica'
        )
        
        service = PrioridadService(session)
        explicacion = service.explicar_prioridad(paciente)
        
        # Tipo efectivo debe ser urgencia
        assert explicacion.tipo_efectivo == 'urgencia'
        
        # Debe mencionar el cambio en los detalles
        assert any('efectivo' in d.lower() or 'original' in d.lower() for d in explicacion.detalles)