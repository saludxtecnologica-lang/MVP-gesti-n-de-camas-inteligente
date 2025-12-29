"""
Tests para endpoints de hospitales.
"""
import pytest
from fastapi import status


class TestHospitales:
    """Tests para operaciones de hospitales."""
    
    def test_obtener_hospitales_vacio(self, client):
        """Test obtener hospitales cuando no hay ninguno."""
        response = client.get("/api/hospitales")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []
    
    def test_obtener_hospitales(self, client, crear_hospital):
        """Test obtener lista de hospitales."""
        # Crear hospitales
        crear_hospital(nombre="Hospital A", codigo="HA")
        crear_hospital(nombre="Hospital B", codigo="HB")
        
        response = client.get("/api/hospitales")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data) == 2
        assert data[0]["codigo"] in ["HA", "HB"]
    
    def test_obtener_hospital_especifico(self, client, crear_hospital):
        """Test obtener un hospital por ID."""
        hospital = crear_hospital(nombre="Hospital Test", codigo="HT")
        
        response = client.get(f"/api/hospitales/{hospital.id}")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["nombre"] == "Hospital Test"
        assert data["codigo"] == "HT"
    
    def test_obtener_hospital_no_existe(self, client):
        """Test obtener hospital que no existe."""
        response = client.get("/api/hospitales/no-existe")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_hospital_con_estadisticas(self, client, hospital_con_camas):
        """Test que hospital incluye estadísticas de camas."""
        hospital = hospital_con_camas["hospital"]
        
        response = client.get(f"/api/hospitales/{hospital.id}")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["total_camas"] == 4
        assert data["camas_libres"] == 4
        assert data["camas_ocupadas"] == 0
    
    def test_obtener_servicios_hospital(self, client, hospital_con_camas):
        """Test obtener servicios de un hospital."""
        hospital = hospital_con_camas["hospital"]
        
        response = client.get(f"/api/hospitales/{hospital.id}/servicios")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data) == 1
        assert data[0]["codigo"] == "MED"
    
    def test_obtener_camas_hospital(self, client, hospital_con_camas):
        """Test obtener camas de un hospital."""
        hospital = hospital_con_camas["hospital"]
        
        response = client.get(f"/api/hospitales/{hospital.id}/camas")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data) == 4
        for cama in data:
            assert cama["estado"] == "libre"