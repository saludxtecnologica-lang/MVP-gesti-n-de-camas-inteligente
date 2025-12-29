"""
Tests para endpoints de traslados.
"""
import pytest
from fastapi import status

from app.models.enums import EstadoCamaEnum, EstadoListaEsperaEnum


class TestTraslados:
    """Tests para operaciones de traslados."""
    
    def test_completar_traslado(
        self, 
        client, 
        session,
        crear_hospital, 
        crear_servicio,
        crear_sala,
        crear_cama,
        crear_paciente
    ):
        """Test completar traslado exitoso."""
        # Setup
        hospital = crear_hospital()
        servicio = crear_servicio(hospital.id)
        sala = crear_sala(servicio.id)
        cama_origen = crear_cama(sala.id, numero=101, identificador="MED-101")
        cama_destino = crear_cama(sala.id, numero=102, identificador="MED-102")
        
        # Cambiar estado cama destino a traslado entrante
        cama_destino.estado = EstadoCamaEnum.TRASLADO_ENTRANTE
        session.add(cama_destino)
        
        # Crear paciente con cama origen y destino
        paciente = crear_paciente(hospital.id)
        paciente.cama_id = cama_origen.id
        paciente.cama_destino_id = cama_destino.id
        
        # Cambiar estado cama origen
        cama_origen.estado = EstadoCamaEnum.TRASLADO_SALIENTE
        session.add(cama_origen)
        session.add(paciente)
        session.commit()
        
        # Ejecutar
        response = client.post(f"/api/traslados/{paciente.id}/completar")
        
        # Verificar
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == True
        assert "cama_destino_id" in data["data"]
        
        # Verificar estados en DB
        session.refresh(cama_origen)
        session.refresh(cama_destino)
        session.refresh(paciente)
        
        assert cama_origen.estado == EstadoCamaEnum.EN_LIMPIEZA
        assert cama_destino.estado == EstadoCamaEnum.OCUPADA
        assert paciente.cama_id == cama_destino.id
        assert paciente.cama_destino_id is None
    
    def test_completar_traslado_paciente_no_existe(self, client):
        """Test completar traslado de paciente que no existe."""
        response = client.post("/api/traslados/no-existe/completar")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_completar_traslado_sin_cama_destino(
        self, 
        client, 
        session,
        crear_hospital, 
        crear_paciente
    ):
        """Test completar traslado cuando no hay cama destino."""
        hospital = crear_hospital()
        paciente = crear_paciente(hospital.id)
        
        response = client.post(f"/api/traslados/{paciente.id}/completar")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_cancelar_traslado(
        self, 
        client, 
        session,
        crear_hospital, 
        crear_servicio,
        crear_sala,
        crear_cama,
        crear_paciente
    ):
        """Test cancelar traslado pendiente."""
        # Setup
        hospital = crear_hospital()
        servicio = crear_servicio(hospital.id)
        sala = crear_sala(servicio.id)
        cama_origen = crear_cama(sala.id, numero=101, identificador="MED-101")
        cama_destino = crear_cama(sala.id, numero=102, identificador="MED-102")
        
        # Configurar estados
        cama_origen.estado = EstadoCamaEnum.TRASLADO_SALIENTE
        cama_destino.estado = EstadoCamaEnum.TRASLADO_ENTRANTE
        session.add(cama_origen)
        session.add(cama_destino)
        
        paciente = crear_paciente(hospital.id)
        paciente.cama_id = cama_origen.id
        paciente.cama_destino_id = cama_destino.id
        paciente.en_lista_espera = True
        session.add(paciente)
        session.commit()
        
        # Ejecutar
        response = client.post(f"/api/traslados/{paciente.id}/cancelar")
        
        # Verificar
        assert response.status_code == status.HTTP_200_OK
        
        session.refresh(cama_origen)
        session.refresh(cama_destino)
        session.refresh(paciente)
        
        assert cama_origen.estado == EstadoCamaEnum.OCUPADA
        assert cama_destino.estado == EstadoCamaEnum.LIBRE
        assert paciente.cama_destino_id is None
        assert paciente.en_lista_espera == False
    
    def test_cancelar_traslado_paciente_nuevo(
        self, 
        client, 
        session,
        crear_hospital, 
        crear_servicio,
        crear_sala,
        crear_cama,
        crear_paciente
    ):
        """Test cancelar traslado de paciente nuevo (sin cama origen)."""
        hospital = crear_hospital()
        servicio = crear_servicio(hospital.id)
        sala = crear_sala(servicio.id)
        cama_destino = crear_cama(sala.id, numero=102, identificador="MED-102")
        
        cama_destino.estado = EstadoCamaEnum.TRASLADO_ENTRANTE
        session.add(cama_destino)
        
        paciente = crear_paciente(hospital.id)
        paciente.cama_id = None  # Sin cama origen
        paciente.cama_destino_id = cama_destino.id
        paciente.en_lista_espera = True
        session.add(paciente)
        session.commit()
        
        response = client.post(f"/api/traslados/{paciente.id}/cancelar")
        
        assert response.status_code == status.HTTP_200_OK
        
        session.refresh(cama_destino)
        session.refresh(paciente)
        
        assert cama_destino.estado == EstadoCamaEnum.LIBRE
        assert paciente.cama_destino_id is None


class TestTrasladosManual:
    """Tests para operaciones de traslado manual."""
    
    def test_traslado_manual(
        self, 
        client, 
        session,
        crear_hospital, 
        crear_servicio,
        crear_sala,
        crear_cama,
        crear_paciente
    ):
        """Test traslado manual inmediato."""
        hospital = crear_hospital()
        servicio = crear_servicio(hospital.id)
        sala = crear_sala(servicio.id)
        cama_origen = crear_cama(sala.id, numero=101, identificador="MED-101", estado=EstadoCamaEnum.OCUPADA)
        cama_destino = crear_cama(sala.id, numero=102, identificador="MED-102")
        
        paciente = crear_paciente(hospital.id)
        paciente.cama_id = cama_origen.id
        session.add(paciente)
        session.commit()
        
        response = client.post("/api/manual/traslado", json={
            "paciente_id": paciente.id,
            "cama_destino_id": cama_destino.id
        })
        
        assert response.status_code == status.HTTP_200_OK
        
        session.refresh(cama_origen)
        session.refresh(cama_destino)
        session.refresh(paciente)
        
        assert cama_origen.estado == EstadoCamaEnum.EN_LIMPIEZA
        assert cama_destino.estado == EstadoCamaEnum.OCUPADA
        assert paciente.cama_id == cama_destino.id
    
    def test_traslado_manual_cama_no_disponible(
        self, 
        client, 
        session,
        crear_hospital, 
        crear_servicio,
        crear_sala,
        crear_cama,
        crear_paciente
    ):
        """Test traslado manual a cama ocupada."""
        hospital = crear_hospital()
        servicio = crear_servicio(hospital.id)
        sala = crear_sala(servicio.id)
        cama_origen = crear_cama(sala.id, numero=101, identificador="MED-101", estado=EstadoCamaEnum.OCUPADA)
        cama_destino = crear_cama(sala.id, numero=102, identificador="MED-102", estado=EstadoCamaEnum.OCUPADA)
        
        paciente = crear_paciente(hospital.id)
        paciente.cama_id = cama_origen.id
        session.add(paciente)
        session.commit()
        
        response = client.post("/api/manual/traslado", json={
            "paciente_id": paciente.id,
            "cama_destino_id": cama_destino.id
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestIntercambio:
    """Tests para intercambio de pacientes."""
    
    def test_intercambiar_pacientes(
        self, 
        client, 
        session,
        crear_hospital, 
        crear_servicio,
        crear_sala,
        crear_cama,
        crear_paciente
    ):
        """Test intercambio exitoso de pacientes."""
        hospital = crear_hospital()
        servicio = crear_servicio(hospital.id)
        sala = crear_sala(servicio.id)
        cama_a = crear_cama(sala.id, numero=101, identificador="MED-101", estado=EstadoCamaEnum.OCUPADA)
        cama_b = crear_cama(sala.id, numero=102, identificador="MED-102", estado=EstadoCamaEnum.OCUPADA)
        
        paciente_a = crear_paciente(hospital.id, nombre="Paciente A", run="11111111-1")
        paciente_a.cama_id = cama_a.id
        
        paciente_b = crear_paciente(hospital.id, nombre="Paciente B", run="22222222-2")
        paciente_b.cama_id = cama_b.id
        
        session.add(paciente_a)
        session.add(paciente_b)
        session.commit()
        
        response = client.post("/api/manual/intercambiar", json={
            "paciente_a_id": paciente_a.id,
            "paciente_b_id": paciente_b.id
        })
        
        assert response.status_code == status.HTTP_200_OK
        
        session.refresh(paciente_a)
        session.refresh(paciente_b)
        
        assert paciente_a.cama_id == cama_b.id
        assert paciente_b.cama_id == cama_a.id
    
    def test_intercambiar_paciente_sin_cama(
        self, 
        client, 
        session,
        crear_hospital, 
        crear_servicio,
        crear_sala,
        crear_cama,
        crear_paciente
    ):
        """Test intercambio cuando un paciente no tiene cama."""
        hospital = crear_hospital()
        servicio = crear_servicio(hospital.id)
        sala = crear_sala(servicio.id)
        cama = crear_cama(sala.id, numero=101, identificador="MED-101", estado=EstadoCamaEnum.OCUPADA)
        
        paciente_a = crear_paciente(hospital.id, nombre="Paciente A", run="11111111-1")
        paciente_a.cama_id = cama.id
        
        paciente_b = crear_paciente(hospital.id, nombre="Paciente B", run="22222222-2")
        paciente_b.cama_id = None  # Sin cama
        
        session.add(paciente_a)
        session.add(paciente_b)
        session.commit()
        
        response = client.post("/api/manual/intercambiar", json={
            "paciente_a_id": paciente_a.id,
            "paciente_b_id": paciente_b.id
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestBusquedaCama:
    """Tests para búsqueda de cama para paciente hospitalizado."""
    
    def test_iniciar_busqueda_cama(
        self, 
        client, 
        session,
        crear_hospital, 
        crear_servicio,
        crear_sala,
        crear_cama,
        crear_paciente
    ):
        """Test iniciar búsqueda de nueva cama."""
        hospital = crear_hospital()
        servicio = crear_servicio(hospital.id)
        sala = crear_sala(servicio.id)
        cama = crear_cama(sala.id, numero=101, identificador="MED-101", estado=EstadoCamaEnum.OCUPADA)
        
        paciente = crear_paciente(hospital.id)
        paciente.cama_id = cama.id
        session.add(paciente)
        session.commit()
        
        response = client.post(f"/api/pacientes/{paciente.id}/buscar-cama")
        
        assert response.status_code == status.HTTP_200_OK
        
        session.refresh(cama)
        session.refresh(paciente)
        
        assert cama.estado == EstadoCamaEnum.TRASLADO_SALIENTE
        assert paciente.en_lista_espera == True
    
    def test_cancelar_busqueda_cama(
        self, 
        client, 
        session,
        crear_hospital, 
        crear_servicio,
        crear_sala,
        crear_cama,
        crear_paciente
    ):
        """Test cancelar búsqueda de cama."""
        hospital = crear_hospital()
        servicio = crear_servicio(hospital.id)
        sala = crear_sala(servicio.id)
        cama = crear_cama(sala.id, numero=101, identificador="MED-101", estado=EstadoCamaEnum.TRASLADO_SALIENTE)
        
        paciente = crear_paciente(hospital.id)
        paciente.cama_id = cama.id
        paciente.en_lista_espera = True
        session.add(paciente)
        session.commit()
        
        response = client.delete(f"/api/pacientes/{paciente.id}/cancelar-busqueda")
        
        assert response.status_code == status.HTTP_200_OK
        
        session.refresh(cama)
        session.refresh(paciente)
        
        assert cama.estado == EstadoCamaEnum.OCUPADA
        assert paciente.en_lista_espera == False
