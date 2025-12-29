"""
Tests para endpoints de pacientes.
"""
import pytest
from fastapi import status


class TestPacientes:
    """Tests para operaciones de pacientes."""
    
    def test_crear_paciente_urgencia(self, client, crear_hospital):
        """Test crear paciente de urgencia."""
        hospital = crear_hospital()
        
        data = {
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
            "hospital_id": hospital.id
        }
        
        response = client.post("/api/pacientes", json=data)
        assert response.status_code == status.HTTP_200_OK
        
        result = response.json()
        assert result["nombre"] == "Juan Pérez"
        assert result["run"] == "12345678-5"
        assert result["tipo_paciente"] == "urgencia"
        assert result["en_lista_espera"] == True
    
    def test_crear_paciente_ambulatorio(self, client, crear_hospital):
        """Test crear paciente ambulatorio."""
        hospital = crear_hospital()
        
        data = {
            "nombre": "María García",
            "run": "11111111-1",
            "sexo": "mujer",
            "edad": 30,
            "es_embarazada": True,
            "diagnostico": "Control prenatal",
            "tipo_enfermedad": "obstetrica",
            "tipo_aislamiento": "ninguno",
            "requerimientos_no_definen": [],
            "requerimientos_baja": [],
            "requerimientos_uti": [],
            "requerimientos_uci": [],
            "casos_especiales": [],
            "tipo_paciente": "ambulatorio",
            "hospital_id": hospital.id
        }
        
        response = client.post("/api/pacientes", json=data)
        assert response.status_code == status.HTTP_200_OK
        
        result = response.json()
        assert result["tipo_paciente"] == "ambulatorio"
        assert result["es_embarazada"] == True
    
    def test_crear_paciente_tipo_invalido(self, client, crear_hospital):
        """Test que no permite crear paciente hospitalizado directamente."""
        hospital = crear_hospital()
        
        data = {
            "nombre": "Test",
            "run": "12345678-5",
            "sexo": "hombre",
            "edad": 40,
            "es_embarazada": False,
            "diagnostico": "Test",
            "tipo_enfermedad": "medica",
            "tipo_aislamiento": "ninguno",
            "requerimientos_no_definen": [],
            "requerimientos_baja": [],
            "requerimientos_uti": [],
            "requerimientos_uci": [],
            "casos_especiales": [],
            "tipo_paciente": "hospitalizado",
            "hospital_id": hospital.id
        }
        
        response = client.post("/api/pacientes", json=data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_obtener_paciente(self, client, crear_hospital, crear_paciente):
        """Test obtener paciente por ID."""
        hospital = crear_hospital()
        paciente = crear_paciente(hospital.id, nombre="Test Paciente")
        
        response = client.get(f"/api/pacientes/{paciente.id}")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["nombre"] == "Test Paciente"
    
    def test_obtener_paciente_no_existe(self, client):
        """Test obtener paciente que no existe."""
        response = client.get("/api/pacientes/no-existe")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_actualizar_paciente(self, client, crear_hospital, crear_paciente):
        """Test actualizar paciente (reevaluación)."""
        hospital = crear_hospital()
        paciente = crear_paciente(hospital.id)
        
        update_data = {
            "diagnostico": "Nuevo diagnóstico",
            "notas_adicionales": "Notas actualizadas"
        }
        
        response = client.put(f"/api/pacientes/{paciente.id}", json=update_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["diagnostico"] == "Nuevo diagnóstico"
        assert data["notas_adicionales"] == "Notas actualizadas"
    
    def test_calcular_complejidad_uci(self, client, crear_hospital):
        """Test que paciente con requerimientos UCI tiene complejidad alta."""
        hospital = crear_hospital()
        
        data = {
            "nombre": "Paciente UCI",
            "run": "12345678-5",
            "sexo": "hombre",
            "edad": 60,
            "es_embarazada": False,
            "diagnostico": "Insuficiencia respiratoria",
            "tipo_enfermedad": "medica",
            "tipo_aislamiento": "ninguno",
            "requerimientos_no_definen": [],
            "requerimientos_baja": [],
            "requerimientos_uti": [],
            "requerimientos_uci": ["vmi"],
            "casos_especiales": [],
            "tipo_paciente": "urgencia",
            "hospital_id": hospital.id
        }
        
        response = client.post("/api/pacientes", json=data)
        assert response.status_code == status.HTTP_200_OK
        
        result = response.json()
        assert result["complejidad_requerida"] == "alta"
    
    def test_calcular_complejidad_uti(self, client, crear_hospital):
        """Test que paciente con requerimientos UTI tiene complejidad media."""
        hospital = crear_hospital()
        
        data = {
            "nombre": "Paciente UTI",
            "run": "12345678-5",
            "sexo": "hombre",
            "edad": 50,
            "es_embarazada": False,
            "diagnostico": "Shock séptico",
            "tipo_enfermedad": "medica",
            "tipo_aislamiento": "ninguno",
            "requerimientos_no_definen": [],
            "requerimientos_baja": [],
            "requerimientos_uti": ["droga_vasoactiva"],
            "requerimientos_uci": [],
            "casos_especiales": [],
            "tipo_paciente": "urgencia",
            "hospital_id": hospital.id
        }
        
        response = client.post("/api/pacientes", json=data)
        assert response.status_code == status.HTTP_200_OK
        
        result = response.json()
        assert result["complejidad_requerida"] == "media"


class TestPrioridad:
    """Tests para cálculo de prioridad."""
    
    def test_obtener_prioridad_paciente(self, client, crear_hospital, crear_paciente):
        """Test obtener prioridad con desglose."""
        hospital = crear_hospital()
        paciente = crear_paciente(hospital.id)
        
        response = client.get(f"/api/pacientes/{paciente.id}/prioridad")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "prioridad_total" in data
        assert "desglose" in data
        assert "detalles" in data