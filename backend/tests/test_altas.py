"""
Tests para endpoints de altas.
"""
import pytest
from fastapi import status

from app.models.enums import EstadoCamaEnum


class TestAltas:
    """Tests para operaciones de altas."""
    
    def test_iniciar_alta(self, client, session, hospital_con_camas, crear_paciente):
        """Test iniciar proceso de alta."""
        hospital = hospital_con_camas["hospital"]
        cama = hospital_con_camas["camas"][0]
        
        # Crear paciente con cama asignada
        paciente = crear_paciente(hospital.id)
        paciente.cama_id = cama.id
        session.add(paciente)
        
        cama.estado = EstadoCamaEnum.OCUPADA
        session.add(cama)
        session.commit()
        
        response = client.post(f"/api/altas/{paciente.id}/iniciar")
        assert response.status_code == status.HTTP_200_OK
        
        # Verificar estado de cama
        session.refresh(cama)
        assert cama.estado == EstadoCamaEnum.CAMA_ALTA
    
    def test_iniciar_alta_paciente_sin_cama(self, client, crear_hospital, crear_paciente):
        """Test iniciar alta de paciente sin cama."""
        hospital = crear_hospital()
        paciente = crear_paciente(hospital.id)
        
        response = client.post(f"/api/altas/{paciente.id}/iniciar")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_ejecutar_alta(self, client, session, hospital_con_camas, crear_paciente):
        """Test ejecutar alta y liberar cama."""
        hospital = hospital_con_camas["hospital"]
        cama = hospital_con_camas["camas"][0]
        
        # Crear paciente en proceso de alta
        paciente = crear_paciente(hospital.id)
        paciente.cama_id = cama.id
        paciente.alta_solicitada = True
        session.add(paciente)
        
        cama.estado = EstadoCamaEnum.CAMA_ALTA
        session.add(cama)
        session.commit()
        
        response = client.post(f"/api/altas/{paciente.id}/ejecutar")
        assert response.status_code == status.HTTP_200_OK
        
        # Verificar que cama está en limpieza
        session.refresh(cama)
        assert cama.estado == EstadoCamaEnum.EN_LIMPIEZA
        
        # Verificar que paciente no tiene cama
        session.refresh(paciente)
        assert paciente.cama_id is None
    
    def test_ejecutar_alta_sin_iniciar(self, client, session, hospital_con_camas, crear_paciente):
        """Test ejecutar alta sin haberla iniciado."""
        hospital = hospital_con_camas["hospital"]
        cama = hospital_con_camas["camas"][0]
        
        paciente = crear_paciente(hospital.id)
        paciente.cama_id = cama.id
        session.add(paciente)
        
        cama.estado = EstadoCamaEnum.OCUPADA  # No está en CAMA_ALTA
        session.add(cama)
        session.commit()
        
        response = client.post(f"/api/altas/{paciente.id}/ejecutar")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_cancelar_alta(self, client, session, hospital_con_camas, crear_paciente):
        """Test cancelar proceso de alta."""
        hospital = hospital_con_camas["hospital"]
        cama = hospital_con_camas["camas"][0]
        
        paciente = crear_paciente(hospital.id)
        paciente.cama_id = cama.id
        paciente.alta_solicitada = True
        session.add(paciente)
        
        cama.estado = EstadoCamaEnum.CAMA_ALTA
        session.add(cama)
        session.commit()
        
        response = client.post(f"/api/altas/{paciente.id}/cancelar")
        assert response.status_code == status.HTTP_200_OK
        
        # Verificar que cama volvió a ocupada
        session.refresh(cama)
        assert cama.estado == EstadoCamaEnum.OCUPADA
        
        # Verificar que alta_solicitada es False
        session.refresh(paciente)
        assert paciente.alta_solicitada == False
    
    def test_omitir_pausa_oxigeno(self, client, session, hospital_con_camas, crear_paciente):
        """Test omitir pausa de espera por oxígeno."""
        from datetime import datetime
        
        hospital = hospital_con_camas["hospital"]
        cama = hospital_con_camas["camas"][0]
        
        paciente = crear_paciente(hospital.id)
        paciente.cama_id = cama.id
        paciente.oxigeno_desactivado_at = datetime.utcnow()
        paciente.esperando_evaluacion_oxigeno = True
        session.add(paciente)
        
        cama.estado = EstadoCamaEnum.OCUPADA
        session.add(cama)
        session.commit()
        
        response = client.post(f"/api/altas/{paciente.id}/omitir-pausa-oxigeno")
        assert response.status_code == status.HTTP_200_OK
        
        session.refresh(paciente)
        assert paciente.esperando_evaluacion_oxigeno == False
        assert paciente.oxigeno_desactivado_at is None
