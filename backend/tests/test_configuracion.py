"""
Tests para endpoints de configuración y estadísticas.
"""
import pytest
from fastapi import status


class TestConfiguracion:
    """Tests para operaciones de configuración."""
    
    def test_obtener_configuracion_inicial(self, client, session):
        """Test obtener configuración cuando no existe."""
        response = client.get("/api/configuracion")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "modo_manual" in data
        assert "tiempo_limpieza_segundos" in data
    
    def test_actualizar_configuracion(self, client, session):
        """Test actualizar configuración."""
        # Primero obtener configuración inicial
        client.get("/api/configuracion")
        
        response = client.put(
            "/api/configuracion",
            json={
                "modo_manual": True,
                "tiempo_limpieza_segundos": 120
            }
        )
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["modo_manual"] == True
        assert data["tiempo_limpieza_segundos"] == 120
    
    def test_toggle_modo_manual(self, client, session):
        """Test alternar modo manual."""
        # Obtener estado inicial
        response = client.get("/api/configuracion")
        modo_inicial = response.json()["modo_manual"]
        
        # Toggle
        response = client.post("/api/configuracion/toggle-modo")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["data"]["modo_manual"] == (not modo_inicial)


class TestEstadisticas:
    """Tests para endpoints de estadísticas."""
    
    def test_obtener_estadisticas_globales(self, client, hospital_con_camas):
        """Test obtener estadísticas globales."""
        response = client.get("/api/estadisticas")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "hospitales" in data
        assert "total_camas_sistema" in data
        assert "ocupacion_promedio" in data
    
    def test_obtener_estadisticas_hospital(self, client, hospital_con_camas):
        """Test obtener estadísticas de hospital específico."""
        hospital = hospital_con_camas["hospital"]
        
        response = client.get(f"/api/estadisticas/hospital/{hospital.id}")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["hospital_id"] == hospital.id
        assert data["total_camas"] == 4
        assert data["camas_libres"] == 4
    
    def test_obtener_lista_espera(self, client, session, hospital_con_camas, crear_paciente):
        """Test obtener lista de espera de hospital."""
        from datetime import datetime
        
        hospital = hospital_con_camas["hospital"]
        
        # Crear pacientes en lista de espera
        for i in range(3):
            paciente = crear_paciente(
                hospital.id,
                nombre=f"Paciente {i}",
                run=f"1111111{i}-{i}"
            )
            paciente.en_lista_espera = True
            paciente.timestamp_lista_espera = datetime.utcnow()
            paciente.prioridad_calculada = 100 - i * 10
            session.add(paciente)
        session.commit()
        
        response = client.get(f"/api/estadisticas/lista-espera/{hospital.id}")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["hospital_id"] == hospital.id
        assert data["total_pacientes"] == 3
        assert len(data["pacientes"]) == 3
    
    def test_estadisticas_hospital_no_existe(self, client):
        """Test estadísticas de hospital inexistente."""
        response = client.get("/api/estadisticas/hospital/no-existe")
        assert response.status_code == status.HTTP_404_NOT_FOUND
