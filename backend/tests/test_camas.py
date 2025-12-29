"""
Tests para endpoints de camas.
"""
import pytest
from fastapi import status

from app.models.enums import EstadoCamaEnum


class TestCamas:
    """Tests para operaciones de camas."""
    
    def test_obtener_cama(self, client, hospital_con_camas):
        """Test obtener cama por ID."""
        cama = hospital_con_camas["camas"][0]
        
        response = client.get(f"/api/camas/{cama.id}")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["identificador"] == cama.identificador
        assert data["estado"] == "libre"
    
    def test_obtener_cama_no_existe(self, client):
        """Test obtener cama que no existe."""
        response = client.get("/api/camas/no-existe")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_bloquear_cama_libre(self, client, hospital_con_camas):
        """Test bloquear una cama libre."""
        cama = hospital_con_camas["camas"][0]
        
        response = client.post(
            f"/api/camas/{cama.id}/bloquear",
            json={"bloquear": True}
        )
        assert response.status_code == status.HTTP_200_OK
        
        # Verificar estado
        response = client.get(f"/api/camas/{cama.id}")
        assert response.json()["estado"] == "bloqueada"
    
    def test_desbloquear_cama(self, client, session, hospital_con_camas):
        """Test desbloquear una cama bloqueada."""
        cama = hospital_con_camas["camas"][0]
        
        # Primero bloquear
        cama.estado = EstadoCamaEnum.BLOQUEADA
        session.add(cama)
        session.commit()
        
        response = client.post(
            f"/api/camas/{cama.id}/bloquear",
            json={"bloquear": False}
        )
        assert response.status_code == status.HTTP_200_OK
        
        # Verificar estado
        response = client.get(f"/api/camas/{cama.id}")
        assert response.json()["estado"] == "libre"
    
    def test_bloquear_cama_ocupada_falla(self, client, session, hospital_con_camas):
        """Test que no se puede bloquear cama ocupada."""
        cama = hospital_con_camas["camas"][0]
        
        # Poner cama como ocupada
        cama.estado = EstadoCamaEnum.OCUPADA
        session.add(cama)
        session.commit()
        
        response = client.post(
            f"/api/camas/{cama.id}/bloquear",
            json={"bloquear": True}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_obtener_camas_libres_servicio(self, client, hospital_con_camas, session):
        """Test obtener camas libres del mismo servicio."""
        camas = hospital_con_camas["camas"]
        
        # Ocupar una cama
        camas[0].estado = EstadoCamaEnum.OCUPADA
        session.add(camas[0])
        session.commit()
        
        response = client.get(f"/api/camas/{camas[0].id}/libres")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        # Debería haber 3 camas libres (4 total - 1 ocupada)
        assert len(data) == 3


class TestEstadosCama:
    """Tests para diferentes estados de cama."""
    
    def test_cama_en_limpieza(self, client, session, hospital_con_camas):
        """Test cama en estado de limpieza."""
        cama = hospital_con_camas["camas"][0]
        
        cama.estado = EstadoCamaEnum.EN_LIMPIEZA
        session.add(cama)
        session.commit()
        
        response = client.get(f"/api/camas/{cama.id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["estado"] == "en_limpieza"
    
    def test_cama_traslado_entrante(self, client, session, hospital_con_camas):
        """Test cama esperando paciente (traslado entrante)."""
        cama = hospital_con_camas["camas"][0]
        
        cama.estado = EstadoCamaEnum.TRASLADO_ENTRANTE
        cama.mensaje_estado = "Esperando paciente"
        session.add(cama)
        session.commit()
        
        response = client.get(f"/api/camas/{cama.id}")
        data = response.json()
        
        assert data["estado"] == "traslado_entrante"
        assert data["mensaje_estado"] == "Esperando paciente"
