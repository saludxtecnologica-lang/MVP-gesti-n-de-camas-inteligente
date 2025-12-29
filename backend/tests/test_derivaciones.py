"""
Tests para endpoints de derivaciones.
"""
import pytest
from fastapi import status

from app.models.enums import EstadoCamaEnum


class TestDerivaciones:
    """Tests para operaciones de derivaciones."""
    
    def test_solicitar_derivacion(self, client, session, hospital_con_camas, crear_hospital, crear_paciente):
        """Test solicitar derivación a otro hospital."""
        hospital_origen = hospital_con_camas["hospital"]
        hospital_destino = crear_hospital(nombre="Hospital Destino", codigo="HD")
        cama = hospital_con_camas["camas"][0]
        
        paciente = crear_paciente(hospital_origen.id)
        paciente.cama_id = cama.id
        session.add(paciente)
        
        cama.estado = EstadoCamaEnum.OCUPADA
        session.add(cama)
        session.commit()
        
        response = client.post(
            f"/api/derivaciones/{paciente.id}/solicitar",
            json={
                "hospital_destino_id": hospital_destino.id,
                "motivo": "Requiere UCI no disponible"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        
        # Verificar estado de derivación
        session.refresh(paciente)
        assert paciente.derivacion_estado == "pendiente"
        assert paciente.derivacion_hospital_destino_id == hospital_destino.id
        
        # Verificar estado de cama
        session.refresh(cama)
        assert cama.estado == EstadoCamaEnum.ESPERA_DERIVACION
    
    def test_obtener_derivados_pendientes(self, client, session, hospital_con_camas, crear_hospital, crear_paciente):
        """Test obtener lista de pacientes derivados pendientes."""
        hospital_origen = hospital_con_camas["hospital"]
        hospital_destino = crear_hospital(nombre="Hospital Destino", codigo="HD")
        
        # Crear paciente derivado
        paciente = crear_paciente(hospital_origen.id)
        paciente.derivacion_hospital_destino_id = hospital_destino.id
        paciente.derivacion_estado = "pendiente"
        paciente.derivacion_motivo = "Motivo de prueba"
        session.add(paciente)
        session.commit()
        
        response = client.get(f"/api/derivaciones/hospital/{hospital_destino.id}")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data) == 1
        assert data[0]["paciente_id"] == paciente.id
    
    def test_aceptar_derivacion(self, client, session, hospital_con_camas, crear_hospital, crear_paciente):
        """Test aceptar una derivación."""
        hospital_origen = hospital_con_camas["hospital"]
        hospital_destino = crear_hospital(nombre="Hospital Destino", codigo="HD")
        
        paciente = crear_paciente(hospital_origen.id)
        paciente.derivacion_hospital_destino_id = hospital_destino.id
        paciente.derivacion_estado = "pendiente"
        session.add(paciente)
        session.commit()
        
        response = client.post(
            f"/api/derivaciones/{paciente.id}/accion",
            json={"accion": "aceptar"}
        )
        assert response.status_code == status.HTTP_200_OK
        
        session.refresh(paciente)
        assert paciente.derivacion_estado == "aceptada"
        assert paciente.tipo_paciente.value == "derivado"
        assert paciente.en_lista_espera == True
    
    def test_rechazar_derivacion(self, client, session, hospital_con_camas, crear_hospital, crear_paciente):
        """Test rechazar una derivación."""
        hospital_origen = hospital_con_camas["hospital"]
        hospital_destino = crear_hospital(nombre="Hospital Destino", codigo="HD")
        cama = hospital_con_camas["camas"][0]
        
        paciente = crear_paciente(hospital_origen.id)
        paciente.cama_id = cama.id
        paciente.derivacion_hospital_destino_id = hospital_destino.id
        paciente.derivacion_estado = "pendiente"
        session.add(paciente)
        
        cama.estado = EstadoCamaEnum.ESPERA_DERIVACION
        session.add(cama)
        session.commit()
        
        response = client.post(
            f"/api/derivaciones/{paciente.id}/accion",
            json={
                "accion": "rechazar",
                "motivo_rechazo": "No hay camas disponibles"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        
        session.refresh(paciente)
        assert paciente.derivacion_estado == "rechazada"
        assert paciente.derivacion_motivo_rechazo == "No hay camas disponibles"
        
        # Verificar que cama volvió a ocupada
        session.refresh(cama)
        assert cama.estado == EstadoCamaEnum.OCUPADA
    
    def test_rechazar_sin_motivo_falla(self, client, session, crear_hospital, crear_paciente):
        """Test que rechazar sin motivo falla."""
        hospital = crear_hospital()
        paciente = crear_paciente(hospital.id)
        paciente.derivacion_estado = "pendiente"
        session.add(paciente)
        session.commit()
        
        response = client.post(
            f"/api/derivaciones/{paciente.id}/accion",
            json={"accion": "rechazar"}  # Sin motivo_rechazo
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_confirmar_egreso(self, client, session, hospital_con_camas, crear_hospital, crear_paciente):
        """Test confirmar egreso de derivación."""
        hospital_origen = hospital_con_camas["hospital"]
        hospital_destino = crear_hospital(nombre="Hospital Destino", codigo="HD")
        cama = hospital_con_camas["camas"][0]
        
        paciente = crear_paciente(hospital_origen.id)
        paciente.cama_origen_derivacion_id = cama.id
        paciente.derivacion_estado = "aceptada"
        session.add(paciente)
        
        cama.estado = EstadoCamaEnum.OCUPADA
        session.add(cama)
        session.commit()
        
        response = client.post(f"/api/derivaciones/{paciente.id}/confirmar-egreso")
        assert response.status_code == status.HTTP_200_OK
        
        # Verificar que cama está en limpieza
        session.refresh(cama)
        assert cama.estado == EstadoCamaEnum.EN_LIMPIEZA
