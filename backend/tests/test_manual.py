"""
Tests para endpoints de modo manual.
"""
import pytest
from fastapi import status

from app.models.enums import EstadoCamaEnum


class TestModoManual:
    """Tests para operaciones en modo manual."""
    
    def test_traslado_manual(self, client, session, hospital_con_camas, crear_paciente):
        """Test traslado manual inmediato."""
        hospital = hospital_con_camas["hospital"]
        camas = hospital_con_camas["camas"]
        
        paciente = crear_paciente(hospital.id)
        paciente.cama_id = camas[0].id
        session.add(paciente)
        
        camas[0].estado = EstadoCamaEnum.OCUPADA
        session.add(camas[0])
        session.commit()
        
        response = client.post(
            "/api/manual/traslado",
            json={
                "paciente_id": paciente.id,
                "cama_destino_id": camas[1].id
            }
        )
        assert response.status_code == status.HTTP_200_OK
        
        # Verificar cama origen en limpieza
        session.refresh(camas[0])
        assert camas[0].estado == EstadoCamaEnum.EN_LIMPIEZA
        
        # Verificar cama destino ocupada
        session.refresh(camas[1])
        assert camas[1].estado == EstadoCamaEnum.OCUPADA
        
        # Verificar paciente en cama destino
        session.refresh(paciente)
        assert paciente.cama_id == camas[1].id
    
    def test_traslado_manual_cama_no_disponible(self, client, session, hospital_con_camas, crear_paciente):
        """Test traslado manual a cama no disponible."""
        hospital = hospital_con_camas["hospital"]
        camas = hospital_con_camas["camas"]
        
        paciente = crear_paciente(hospital.id)
        paciente.cama_id = camas[0].id
        session.add(paciente)
        
        camas[0].estado = EstadoCamaEnum.OCUPADA
        camas[1].estado = EstadoCamaEnum.BLOQUEADA  # No disponible
        session.add(camas[0])
        session.add(camas[1])
        session.commit()
        
        response = client.post(
            "/api/manual/traslado",
            json={
                "paciente_id": paciente.id,
                "cama_destino_id": camas[1].id
            }
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_intercambiar_pacientes(self, client, session, hospital_con_camas, crear_paciente):
        """Test intercambio de camas entre dos pacientes."""
        hospital = hospital_con_camas["hospital"]
        camas = hospital_con_camas["camas"]
        
        paciente_a = crear_paciente(hospital.id, nombre="Paciente A", run="11111111-1")
        paciente_a.cama_id = camas[0].id
        session.add(paciente_a)
        
        paciente_b = crear_paciente(hospital.id, nombre="Paciente B", run="22222222-2")
        paciente_b.cama_id = camas[1].id
        session.add(paciente_b)
        
        camas[0].estado = EstadoCamaEnum.OCUPADA
        camas[1].estado = EstadoCamaEnum.OCUPADA
        session.add(camas[0])
        session.add(camas[1])
        session.commit()
        
        response = client.post(
            "/api/manual/intercambiar",
            json={
                "paciente_a_id": paciente_a.id,
                "paciente_b_id": paciente_b.id
            }
        )
        assert response.status_code == status.HTTP_200_OK
        
        # Verificar intercambio
        session.refresh(paciente_a)
        session.refresh(paciente_b)
        assert paciente_a.cama_id == camas[1].id
        assert paciente_b.cama_id == camas[0].id
    
    def test_intercambiar_paciente_sin_cama(self, client, session, hospital_con_camas, crear_paciente):
        """Test intercambio falla si un paciente no tiene cama."""
        hospital = hospital_con_camas["hospital"]
        camas = hospital_con_camas["camas"]
        
        paciente_a = crear_paciente(hospital.id, nombre="Paciente A", run="11111111-1")
        paciente_a.cama_id = camas[0].id
        session.add(paciente_a)
        
        paciente_b = crear_paciente(hospital.id, nombre="Paciente B", run="22222222-2")
        # paciente_b no tiene cama
        session.add(paciente_b)
        session.commit()
        
        response = client.post(
            "/api/manual/intercambiar",
            json={
                "paciente_a_id": paciente_a.id,
                "paciente_b_id": paciente_b.id
            }
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_egresar_manual(self, client, session, hospital_con_camas, crear_paciente):
        """Test egreso manual de paciente."""
        hospital = hospital_con_camas["hospital"]
        cama = hospital_con_camas["camas"][0]
        
        paciente = crear_paciente(hospital.id)
        paciente.cama_id = cama.id
        session.add(paciente)
        
        cama.estado = EstadoCamaEnum.OCUPADA
        session.add(cama)
        session.commit()
        
        response = client.post(f"/api/manual/egresar/{paciente.id}")
        assert response.status_code == status.HTTP_200_OK
        
        # Verificar paciente sin cama
        session.refresh(paciente)
        assert paciente.cama_id is None
        
        # Verificar cama en limpieza
        session.refresh(cama)
        assert cama.estado == EstadoCamaEnum.EN_LIMPIEZA
    
    def test_egresar_de_lista(self, client, session, crear_hospital, crear_paciente):
        """Test remover paciente de lista de espera."""
        from datetime import datetime
        
        hospital = crear_hospital()
        paciente = crear_paciente(hospital.id)
        paciente.en_lista_espera = True
        paciente.timestamp_lista_espera = datetime.utcnow()
        session.add(paciente)
        session.commit()
        
        response = client.delete(f"/api/manual/egresar-de-lista/{paciente.id}")
        assert response.status_code == status.HTTP_200_OK
        
        session.refresh(paciente)
        assert paciente.en_lista_espera == False
        assert paciente.timestamp_lista_espera is None
    
    def test_egresar_de_lista_no_en_lista(self, client, session, crear_hospital, crear_paciente):
        """Test remover paciente que no está en lista."""
        hospital = crear_hospital()
        paciente = crear_paciente(hospital.id)
        paciente.en_lista_espera = False
        session.add(paciente)
        session.commit()
        
        response = client.delete(f"/api/manual/egresar-de-lista/{paciente.id}")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_asignar_desde_lista(self, client, session, hospital_con_camas, crear_paciente):
        """Test asignar paciente de lista a cama específica."""
        from datetime import datetime
        
        hospital = hospital_con_camas["hospital"]
        cama = hospital_con_camas["camas"][0]
        
        paciente = crear_paciente(hospital.id)
        paciente.en_lista_espera = True
        paciente.timestamp_lista_espera = datetime.utcnow()
        session.add(paciente)
        session.commit()
        
        response = client.post(
            "/api/manual/asignar-desde-lista",
            json={
                "paciente_id": paciente.id,
                "cama_destino_id": cama.id
            }
        )
        assert response.status_code == status.HTTP_200_OK
        
        # Verificar asignación
        session.refresh(cama)
        assert cama.estado == EstadoCamaEnum.TRASLADO_ENTRANTE
