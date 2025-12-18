import React, { useState, useCallback } from 'react';
import { Save, X, AlertTriangle } from 'lucide-react';
import type {
  Paciente,
  PacienteCreate,
  PacienteUpdate,
  PacienteFormData,
  Hospital,
  TipoPacienteEnum
} from '../types/Index';
import { SexoEnum, TipoEnfermedadEnum, TipoAislamientoEnum } from '../types/Index';
import * as api from '../services/api';

interface PacienteFormProps {
  paciente?: Paciente;
  hospitalId: string;
  hospitales: Hospital[];
  isReevaluacion?: boolean;
  onSubmit: () => void;
  onError: (mensaje: string) => void;
  onCancel: () => void;
}

// Función para convertir el formulario al formato del backend
function convertFormToApiData(formData: PacienteFormData, isReevaluacion: boolean): PacienteCreate | PacienteUpdate {
  // Construir listas de requerimientos
  const requerimientos_no_definen: string[] = [];
  if (formData.req_kinesioterapia) requerimientos_no_definen.push('kinesioterapia');
  if (formData.req_control_sangre_1x) requerimientos_no_definen.push('control_sangre_1x');
  if (formData.req_curaciones) requerimientos_no_definen.push('curaciones');
  if (formData.req_tratamiento_ev_2x) requerimientos_no_definen.push('tratamiento_ev_2x');

  const requerimientos_baja: string[] = [];
  if (formData.req_tratamiento_ev_3x) requerimientos_baja.push('tratamiento_ev_3x');
  if (formData.req_control_sangre_2x) requerimientos_baja.push('control_sangre_2x');
  if (formData.req_o2_naricera) requerimientos_baja.push('o2_naricera');
  if (formData.req_dolor_eva_7) requerimientos_baja.push('dolor_eva_7');
  if (formData.req_o2_multiventuri) requerimientos_baja.push('o2_multiventuri');
  if (formData.req_curaciones_complejas) requerimientos_baja.push('curaciones_complejas');
  if (formData.req_aspiracion) requerimientos_baja.push('aspiracion');
  if (formData.req_observacion) requerimientos_baja.push('observacion');
  if (formData.req_irrigacion_vesical) requerimientos_baja.push('irrigacion_vesical');
  if (formData.req_procedimiento_invasivo) requerimientos_baja.push('procedimiento_invasivo');

  const requerimientos_uti: string[] = [];
  if (formData.req_drogas_vasoactivas) requerimientos_uti.push('drogas_vasoactivas');
  if (formData.req_sedacion) requerimientos_uti.push('sedacion');
  if (formData.req_monitorizacion) requerimientos_uti.push('monitorizacion');
  if (formData.req_o2_reservorio) requerimientos_uti.push('o2_reservorio');
  if (formData.req_dialisis) requerimientos_uti.push('dialisis');
  if (formData.req_cnaf) requerimientos_uti.push('cnaf');
  if (formData.req_bic_insulina) requerimientos_uti.push('bic_insulina');
  if (formData.req_vmni) requerimientos_uti.push('vmni');

  const requerimientos_uci: string[] = [];
  if (formData.req_vmi) requerimientos_uci.push('vmi');
  if (formData.req_procuramiento_o2) requerimientos_uci.push('procuramiento_o2');

  const casos_especiales: string[] = [];
  if (formData.caso_socio_sanitario) casos_especiales.push('socio_sanitario');
  if (formData.caso_socio_judicial) casos_especiales.push('socio_judicial');
  if (formData.caso_espera_cardiocirugia) casos_especiales.push('espera_cardiocirugia');

  if (isReevaluacion) {
    // Para reevaluación, solo enviamos los campos actualizables
    const updateData: PacienteUpdate = {
      diagnostico: formData.diagnostico,
      tipo_enfermedad: formData.tipo_enfermedad,
      tipo_aislamiento: formData.tipo_aislamiento,
      notas_adicionales: formData.notas_adicionales || undefined,
      es_embarazada: formData.es_embarazada,
      requerimientos_no_definen,
      requerimientos_baja,
      requerimientos_uti,
      requerimientos_uci,
      casos_especiales,
      motivo_observacion: formData.req_observacion ? formData.req_observacion_motivo : undefined,
      procedimiento_invasivo: formData.req_procedimiento_invasivo ? formData.req_procedimiento_invasivo_detalle : undefined,
      justificacion_observacion: formData.req_monitorizacion ? formData.req_monitorizacion_motivo : undefined,
    };

    // Agregar derivación si está solicitada
    if (formData.derivacion_solicitada && formData.derivacion_hospital_destino_id) {
      updateData.derivacion_hospital_destino_id = formData.derivacion_hospital_destino_id;
      updateData.derivacion_motivo = formData.derivacion_motivo;
    }

    // Agregar alta si está solicitada
    if (formData.alta_solicitada) {
      updateData.alta_solicitada = true;
      updateData.alta_motivo = formData.alta_motivo;
    }

    return updateData;
  } else {
    // Para nuevo paciente
    const createData: PacienteCreate = {
      nombre: formData.nombre.trim(),
      run: formData.run.trim(),
      sexo: formData.sexo,
      edad: formData.edad,
      es_embarazada: formData.es_embarazada,
      diagnostico: formData.diagnostico.trim(),
      tipo_enfermedad: formData.tipo_enfermedad,
      tipo_aislamiento: formData.tipo_aislamiento,
      notas_adicionales: formData.notas_adicionales || undefined,
      tipo_paciente: formData.tipo_paciente,
      hospital_id: formData.hospital_id,
      requerimientos_no_definen,
      requerimientos_baja,
      requerimientos_uti,
      requerimientos_uci,
      casos_especiales,
      motivo_observacion: formData.req_observacion ? formData.req_observacion_motivo : undefined,
      procedimiento_invasivo: formData.req_procedimiento_invasivo ? formData.req_procedimiento_invasivo_detalle : undefined,
      justificacion_observacion: formData.req_monitorizacion ? formData.req_monitorizacion_motivo : undefined,
    };

    return createData;
  }
}

// Función para inicializar el formulario desde un paciente existente
function initFormFromPaciente(paciente: Paciente | undefined, hospitalId: string): PacienteFormData {
  const defaultForm: PacienteFormData = {
    nombre: '',
    run: '',
    sexo: SexoEnum.HOMBRE,
    edad: 0,
    es_embarazada: false,
    diagnostico: '',
    tipo_enfermedad: TipoEnfermedadEnum.MEDICA,
    tipo_aislamiento: TipoAislamientoEnum.NINGUNO,
    notas_adicionales: '',
    // CORRECCIÓN Problema 10: Por defecto es URGENCIA para nuevos pacientes
    tipo_paciente: 'urgencia' as TipoPacienteEnum,
    hospital_id: hospitalId,
    
    req_kinesioterapia: false,
    req_control_sangre_1x: false,
    req_curaciones: false,
    req_tratamiento_ev_2x: false,
    req_tratamiento_ev_3x: false,
    req_control_sangre_2x: false,
    req_o2_naricera: false,
    req_dolor_eva_7: false,
    req_o2_multiventuri: false,
    req_curaciones_complejas: false,
    req_aspiracion: false,
    req_observacion: false,
    req_observacion_motivo: '',
    req_irrigacion_vesical: false,
    req_procedimiento_invasivo: false,
    req_procedimiento_invasivo_detalle: '',
    req_drogas_vasoactivas: false,
    req_sedacion: false,
    req_monitorizacion: false,
    req_monitorizacion_motivo: '',
    req_o2_reservorio: false,
    req_dialisis: false,
    req_cnaf: false,
    req_bic_insulina: false,
    req_vmni: false,
    req_vmi: false,
    req_procuramiento_o2: false,
    caso_socio_sanitario: false,
    caso_socio_judicial: false,
    caso_espera_cardiocirugia: false,
    derivacion_solicitada: false,
    derivacion_hospital_destino_id: '',
    derivacion_motivo: '',
    alta_solicitada: false,
    alta_motivo: ''
  };

  if (!paciente) return defaultForm;

  // Usar es_embarazada o embarazada (compatibilidad backend/frontend)
  const esEmbarazada = paciente.es_embarazada ?? paciente.embarazada ?? false;
  
  // Detectar si los requerimientos vienen como listas (formato backend)
  const reqNoDefinen = paciente.requerimientos_no_definen || [];
  const reqBaja = paciente.requerimientos_baja || [];
  const reqUti = paciente.requerimientos_uti || [];
  const reqUci = paciente.requerimientos_uci || [];
  const casosEspeciales = paciente.casos_especiales || [];
  
  return {
    ...defaultForm,
    nombre: paciente.nombre,
    run: paciente.run,
    sexo: paciente.sexo,
    edad: paciente.edad,
    es_embarazada: esEmbarazada,
    diagnostico: paciente.diagnostico,
    tipo_enfermedad: paciente.tipo_enfermedad,
    tipo_aislamiento: paciente.tipo_aislamiento,
    notas_adicionales: paciente.notas_adicionales || '',
    tipo_paciente: paciente.tipo_paciente,
    hospital_id: paciente.hospital_id,
    
    // Requerimientos - verificar tanto listas como booleanos
    req_kinesioterapia: reqNoDefinen.includes('kinesioterapia') || paciente.req_kinesioterapia || false,
    req_control_sangre_1x: reqNoDefinen.includes('control_sangre_1x') || paciente.req_control_sangre_1x || false,
    req_curaciones: reqNoDefinen.includes('curaciones') || paciente.req_curaciones || false,
    req_tratamiento_ev_2x: reqNoDefinen.includes('tratamiento_ev_2x') || paciente.req_tratamiento_ev_2x || false,
    
    req_tratamiento_ev_3x: reqBaja.includes('tratamiento_ev_3x') || paciente.req_tratamiento_ev_3x || false,
    req_control_sangre_2x: reqBaja.includes('control_sangre_2x') || paciente.req_control_sangre_2x || false,
    req_o2_naricera: reqBaja.includes('o2_naricera') || paciente.req_o2_naricera || false,
    req_dolor_eva_7: reqBaja.includes('dolor_eva_7') || paciente.req_dolor_eva_7 || false,
    req_o2_multiventuri: reqBaja.includes('o2_multiventuri') || paciente.req_o2_multiventuri || false,
    req_curaciones_complejas: reqBaja.includes('curaciones_complejas') || paciente.req_curaciones_complejas || false,
    req_aspiracion: reqBaja.includes('aspiracion') || paciente.req_aspiracion || false,
    req_observacion: reqBaja.includes('observacion') || paciente.req_observacion || false,
    req_observacion_motivo: paciente.motivo_observacion || paciente.req_observacion_motivo || '',
    req_irrigacion_vesical: reqBaja.includes('irrigacion_vesical') || paciente.req_irrigacion_vesical || false,
    req_procedimiento_invasivo: reqBaja.includes('procedimiento_invasivo') || paciente.req_procedimiento_invasivo || false,
    req_procedimiento_invasivo_detalle: paciente.procedimiento_invasivo || paciente.req_procedimiento_invasivo_detalle || '',
    
    req_drogas_vasoactivas: reqUti.includes('drogas_vasoactivas') || paciente.req_drogas_vasoactivas || false,
    req_sedacion: reqUti.includes('sedacion') || paciente.req_sedacion || false,
    req_monitorizacion: reqUti.includes('monitorizacion') || paciente.req_monitorizacion || false,
    req_monitorizacion_motivo: paciente.justificacion_observacion || paciente.req_monitorizacion_motivo || '',
    req_o2_reservorio: reqUti.includes('o2_reservorio') || paciente.req_o2_reservorio || false,
    req_dialisis: reqUti.includes('dialisis') || paciente.req_dialisis || false,
    req_cnaf: reqUti.includes('cnaf') || paciente.req_cnaf || false,
    req_bic_insulina: reqUti.includes('bic_insulina') || paciente.req_bic_insulina || false,
    req_vmni: reqUti.includes('vmni') || paciente.req_vmni || false,
    
    req_vmi: reqUci.includes('vmi') || paciente.req_vmi || false,
    req_procuramiento_o2: reqUci.includes('procuramiento_o2') || paciente.req_procuramiento_o2 || false,
    
    caso_socio_sanitario: casosEspeciales.includes('socio_sanitario') || paciente.caso_socio_sanitario || false,
    caso_socio_judicial: casosEspeciales.includes('socio_judicial') || paciente.caso_socio_judicial || false,
    caso_espera_cardiocirugia: casosEspeciales.includes('espera_cardiocirugia') || paciente.caso_espera_cardiocirugia || false,
    
    derivacion_solicitada: paciente.derivacion_solicitada || false,
    derivacion_hospital_destino_id: paciente.derivacion_hospital_destino_id || '',
    derivacion_motivo: paciente.derivacion_motivo || '',
    alta_solicitada: paciente.alta_solicitada || false,
    alta_motivo: paciente.alta_motivo || ''
  };
}

export function PacienteForm({
  paciente,
  hospitalId,
  hospitales,
  isReevaluacion = false,
  onSubmit,
  onError,
  onCancel
}: PacienteFormProps) {
  const [formData, setFormData] = useState<PacienteFormData>(() => 
    initFormFromPaciente(paciente, hospitalId)
  );
  const [loading, setLoading] = useState(false);
  const [showAltaWarning, setShowAltaWarning] = useState(false);

  const handleChange = useCallback((
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value, type } = e.target;
    const checked = (e.target as HTMLInputElement).checked;
    
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : (type === 'number' ? Number(value) : value)
    }));
  }, []);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validaciones básicas
    if (!formData.nombre.trim()) {
      onError('El nombre es requerido');
      return;
    }
    
    // Validar formato de RUN: 12345678-9 o 1234567-K
    const runPattern = /^\d{7,8}-[\dkK]$/;
    if (!runPattern.test(formData.run.trim())) {
      onError('El RUN debe tener el formato correcto (ej: 12345678-9)');
      return;
    }
    
    if (formData.edad < 0 || formData.edad > 120) {
      onError('La edad debe estar entre 0 y 120 años');
      return;
    }
    if (!formData.diagnostico.trim()) {
      onError('El diagnóstico es requerido');
      return;
    }

    // Validar que haya hospital seleccionado
    if (!formData.hospital_id) {
      onError('Debe seleccionar un hospital');
      return;
    }

    // CORRECCIÓN Problema 10: Validar tipo de paciente para nuevos registros
    if (!isReevaluacion) {
      if (formData.tipo_paciente !== 'urgencia' && formData.tipo_paciente !== 'ambulatorio') {
        onError('Solo se permite registrar pacientes de tipo Urgencia o Ambulatorio');
        return;
      }
    }

    // Validar alta con requerimientos
    if (formData.alta_solicitada) {
      const tieneRequerimientosAltos = formData.req_vmi || formData.req_procuramiento_o2 ||
        formData.req_drogas_vasoactivas || formData.req_sedacion || formData.req_monitorizacion ||
        formData.req_dialisis || formData.req_cnaf || formData.req_bic_insulina || formData.req_vmni ||
        formData.req_tratamiento_ev_3x || formData.req_dolor_eva_7 || formData.req_curaciones_complejas ||
        formData.tipo_aislamiento === TipoAislamientoEnum.AEREO;
      
      if (tieneRequerimientosAltos && !formData.alta_motivo) {
        setShowAltaWarning(true);
        return;
      }
    }

    // Validar derivación
    if (formData.derivacion_solicitada) {
      if (!formData.derivacion_hospital_destino_id) {
        onError('Debe seleccionar un hospital de destino para la derivación');
        return;
      }
      if (!formData.derivacion_motivo?.trim()) {
        onError('Debe indicar el motivo de la derivación');
        return;
      }
    }

    setLoading(true);
    try {
      const apiData = convertFormToApiData(formData, isReevaluacion);
      
      if (isReevaluacion && paciente) {
        await api.actualizarPaciente(paciente.id, apiData as PacienteUpdate);
      } else {
        await api.crearPaciente(apiData as PacienteCreate);
      }
      onSubmit();
    } catch (err) {
      // Manejar error correctamente
      if (err instanceof Error) {
        onError(err.message);
      } else if (typeof err === 'object' && err !== null) {
        // Si es un objeto de error del API
        const errorObj = err as { detail?: string; message?: string };
        onError(errorObj.detail || errorObj.message || 'Error desconocido al guardar');
      } else {
        onError('Error al guardar paciente');
      }
    } finally {
      setLoading(false);
    }
  }, [formData, isReevaluacion, paciente, onSubmit, onError]);

  const hospitalesDerivacion = hospitales.filter(h => h.id !== formData.hospital_id);

  return (
    <form onSubmit={handleSubmit} className="paciente-form">
      {/* Datos personales */}
      <section className="form-section">
        <h3>Datos Personales</h3>
        <div className="form-grid">
          <div className="form-group">
            <label htmlFor="nombre">Nombre completo *</label>
            <input
              type="text"
              id="nombre"
              name="nombre"
              value={formData.nombre}
              onChange={handleChange}
              required
              disabled={isReevaluacion}
            />
          </div>
          <div className="form-group">
            <label htmlFor="run">RUN *</label>
            <input
              type="text"
              id="run"
              name="run"
              value={formData.run}
              onChange={handleChange}
              placeholder="12345678-9"
              required
              disabled={isReevaluacion}
            />
          </div>
          <div className="form-group">
            <label htmlFor="sexo">Sexo *</label>
            <select
              id="sexo"
              name="sexo"
              value={formData.sexo}
              onChange={handleChange}
              disabled={isReevaluacion}
            >
              <option value="hombre">Masculino</option>
              <option value="mujer">Femenino</option>
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="edad">Edad *</label>
            <input
              type="number"
              id="edad"
              name="edad"
              value={formData.edad}
              onChange={handleChange}
              min={0}
              max={120}
              required
            />
          </div>
          <div className="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                name="es_embarazada"
                checked={formData.es_embarazada}
                onChange={handleChange}
                disabled={formData.sexo === 'hombre'}
              />
              Embarazada
            </label>
          </div>
          <div className="form-group">
            <label htmlFor="tipo_paciente">Tipo de paciente *</label>
            <select
              id="tipo_paciente"
              name="tipo_paciente"
              value={formData.tipo_paciente}
              onChange={handleChange}
              disabled={isReevaluacion}
            >
              {/* CORRECCIÓN Problema 10: Solo mostrar opciones válidas para nuevos pacientes */}
              {isReevaluacion ? (
                // En reevaluación, mostrar el tipo actual (readonly)
                <>
                  <option value="hospitalizado">Hospitalizado</option>
                  <option value="urgencia">Urgencia</option>
                  <option value="derivado">Derivado</option>
                  <option value="ambulatorio">Ambulatorio</option>
                </>
              ) : (
                // Para nuevos pacientes, solo URGENCIA o AMBULATORIO
                <>
                  <option value="urgencia">Urgencia</option>
                  <option value="ambulatorio">Ambulatorio</option>
                </>
              )}
            </select>
            {!isReevaluacion && (
              <small className="form-hint">
                El sistema asignará automáticamente "Hospitalizado" o "Derivado" según corresponda.
              </small>
            )}
          </div>
        </div>
      </section>

      {/* Información clínica */}
      <section className="form-section">
        <h3>Información Clínica</h3>
        <div className="form-grid">
          <div className="form-group full-width">
            <label htmlFor="diagnostico">Diagnóstico *</label>
            <textarea
              id="diagnostico"
              name="diagnostico"
              value={formData.diagnostico}
              onChange={handleChange}
              rows={2}
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="tipo_enfermedad">Tipo de enfermedad *</label>
            <select
              id="tipo_enfermedad"
              name="tipo_enfermedad"
              value={formData.tipo_enfermedad}
              onChange={handleChange}
            >
              <option value="medica">Médica</option>
              <option value="quirurgica">Quirúrgica</option>
              <option value="traumatologica">Traumatológica</option>
              <option value="neurologica">Neurológica</option>
              <option value="urologica">Urológica</option>
              <option value="geriatrica">Geriátrica</option>
              <option value="ginecologica">Ginecológica</option>
              <option value="obstetrica">Obstétrica</option>
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="tipo_aislamiento">Aislamiento</label>
            <select
              id="tipo_aislamiento"
              name="tipo_aislamiento"
              value={formData.tipo_aislamiento}
              onChange={handleChange}
            >
              <option value="ninguno">No requiere</option>
              <option value="contacto">Contacto</option>
              <option value="gotitas">Gotitas</option>
              <option value="aereo">Aéreo</option>
              <option value="ambiente_protegido">Ambiente protegido</option>
              <option value="especial">Especial</option>
            </select>
          </div>
        </div>
      </section>

      {/* Requerimientos clínicos */}
      <section className="form-section">
        <h3>Requerimientos Clínicos</h3>
        
        <div className="requerimientos-group">
          <h4>No definen complejidad</h4>
          <div className="checkbox-grid">
            <label><input type="checkbox" name="req_kinesioterapia" checked={formData.req_kinesioterapia} onChange={handleChange} /> Kinesioterapia</label>
            <label><input type="checkbox" name="req_control_sangre_1x" checked={formData.req_control_sangre_1x} onChange={handleChange} /> Control sangre 1x/día</label>
            <label><input type="checkbox" name="req_curaciones" checked={formData.req_curaciones} onChange={handleChange} /> Curaciones</label>
            <label><input type="checkbox" name="req_tratamiento_ev_2x" checked={formData.req_tratamiento_ev_2x} onChange={handleChange} /> Tratamiento EV ≤2x/día</label>
          </div>
        </div>

        <div className="requerimientos-group">
          <h4>Baja complejidad</h4>
          <div className="checkbox-grid">
            <label><input type="checkbox" name="req_tratamiento_ev_3x" checked={formData.req_tratamiento_ev_3x} onChange={handleChange} /> Tratamiento EV 3+x/día</label>
            <label><input type="checkbox" name="req_control_sangre_2x" checked={formData.req_control_sangre_2x} onChange={handleChange} /> Control sangre 2+x/día</label>
            <label><input type="checkbox" name="req_o2_naricera" checked={formData.req_o2_naricera} onChange={handleChange} /> O2 naricera</label>
            <label><input type="checkbox" name="req_dolor_eva_7" checked={formData.req_dolor_eva_7} onChange={handleChange} /> Dolor EVA ≥7</label>
            <label><input type="checkbox" name="req_o2_multiventuri" checked={formData.req_o2_multiventuri} onChange={handleChange} /> O2 multiventuri</label>
            <label><input type="checkbox" name="req_curaciones_complejas" checked={formData.req_curaciones_complejas} onChange={handleChange} /> Curaciones complejas</label>
            <label><input type="checkbox" name="req_aspiracion" checked={formData.req_aspiracion} onChange={handleChange} /> Aspiración</label>
            <label><input type="checkbox" name="req_irrigacion_vesical" checked={formData.req_irrigacion_vesical} onChange={handleChange} /> Irrigación vesical</label>
          </div>
          <div className="form-group">
            <label>
              <input type="checkbox" name="req_observacion" checked={formData.req_observacion} onChange={handleChange} /> Observación
            </label>
            {formData.req_observacion && (
              <input
                type="text"
                name="req_observacion_motivo"
                value={formData.req_observacion_motivo}
                onChange={handleChange}
                placeholder="Motivo de observación"
                className="sub-input"
              />
            )}
          </div>
          <div className="form-group">
            <label>
              <input type="checkbox" name="req_procedimiento_invasivo" checked={formData.req_procedimiento_invasivo} onChange={handleChange} /> Procedimiento invasivo
            </label>
            {formData.req_procedimiento_invasivo && (
              <input
                type="text"
                name="req_procedimiento_invasivo_detalle"
                value={formData.req_procedimiento_invasivo_detalle}
                onChange={handleChange}
                placeholder="Detalle del procedimiento"
                className="sub-input"
              />
            )}
          </div>
        </div>

        <div className="requerimientos-group">
          <h4>UTI (mediana complejidad)</h4>
          <div className="checkbox-grid">
            <label><input type="checkbox" name="req_drogas_vasoactivas" checked={formData.req_drogas_vasoactivas} onChange={handleChange} /> Drogas vasoactivas</label>
            <label><input type="checkbox" name="req_sedacion" checked={formData.req_sedacion} onChange={handleChange} /> Sedación</label>
            <label><input type="checkbox" name="req_o2_reservorio" checked={formData.req_o2_reservorio} onChange={handleChange} /> O2 reservorio</label>
            <label><input type="checkbox" name="req_dialisis" checked={formData.req_dialisis} onChange={handleChange} /> Diálisis</label>
            <label><input type="checkbox" name="req_cnaf" checked={formData.req_cnaf} onChange={handleChange} /> CNAF</label>
            <label><input type="checkbox" name="req_bic_insulina" checked={formData.req_bic_insulina} onChange={handleChange} /> BIC insulina</label>
            <label><input type="checkbox" name="req_vmni" checked={formData.req_vmni} onChange={handleChange} /> VMNI</label>
          </div>
          <div className="form-group">
            <label>
              <input type="checkbox" name="req_monitorizacion" checked={formData.req_monitorizacion} onChange={handleChange} /> Monitorización
            </label>
            {formData.req_monitorizacion && (
              <input
                type="text"
                name="req_monitorizacion_motivo"
                value={formData.req_monitorizacion_motivo}
                onChange={handleChange}
                placeholder="Motivo de monitorización"
                className="sub-input"
              />
            )}
          </div>
        </div>

        <div className="requerimientos-group">
          <h4>UCI (alta complejidad)</h4>
          <div className="checkbox-grid">
            <label><input type="checkbox" name="req_vmi" checked={formData.req_vmi} onChange={handleChange} /> VMI</label>
            <label><input type="checkbox" name="req_procuramiento_o2" checked={formData.req_procuramiento_o2} onChange={handleChange} /> Procuramiento O2</label>
          </div>
        </div>
      </section>

      {/* Casos especiales */}
      <section className="form-section">
        <h3>Casos Especiales</h3>
        <div className="checkbox-grid">
          <label><input type="checkbox" name="caso_socio_sanitario" checked={formData.caso_socio_sanitario} onChange={handleChange} /> Caso socio-sanitario</label>
          <label><input type="checkbox" name="caso_socio_judicial" checked={formData.caso_socio_judicial} onChange={handleChange} /> Caso socio-judicial</label>
          <label><input type="checkbox" name="caso_espera_cardiocirugia" checked={formData.caso_espera_cardiocirugia} onChange={handleChange} /> Espera cardiocirugía</label>
        </div>
      </section>

      {/* Notas adicionales */}
      <section className="form-section">
        <h3>Notas Adicionales</h3>
        <div className="form-group full-width">
          <textarea
            name="notas_adicionales"
            value={formData.notas_adicionales}
            onChange={handleChange}
            rows={3}
            placeholder="Información adicional relevante..."
          />
        </div>
      </section>

      {/* Derivación (solo en reevaluación) */}
      {isReevaluacion && (
        <section className="form-section">
          <h3>Derivación</h3>
          <div className="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                name="derivacion_solicitada"
                checked={formData.derivacion_solicitada}
                onChange={handleChange}
              />
              Solicitar derivación
            </label>
          </div>
          {formData.derivacion_solicitada && (
            <div className="form-grid">
              <div className="form-group">
                <label>Hospital destino *</label>
                <select
                  name="derivacion_hospital_destino_id"
                  value={formData.derivacion_hospital_destino_id}
                  onChange={handleChange}
                >
                  <option value="">Seleccionar hospital</option>
                  {hospitalesDerivacion.map(h => (
                    <option key={h.id} value={h.id}>{h.nombre}</option>
                  ))}
                </select>
              </div>
              <div className="form-group full-width">
                <label>Motivo de derivación *</label>
                <textarea
                  name="derivacion_motivo"
                  value={formData.derivacion_motivo}
                  onChange={handleChange}
                  rows={2}
                  placeholder="Motivo de la derivación..."
                />
              </div>
            </div>
          )}
        </section>
      )}

      {/* Alta (solo en reevaluación) */}
      {isReevaluacion && (
        <section className="form-section">
          <h3>Alta Médica</h3>
          <div className="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                name="alta_solicitada"
                checked={formData.alta_solicitada}
                onChange={handleChange}
              />
              Dar de alta
            </label>
          </div>
          {formData.alta_solicitada && (
            <div className="form-group full-width">
              <label>Motivo del alta (requerido si tiene requerimientos activos)</label>
              <textarea
                name="alta_motivo"
                value={formData.alta_motivo}
                onChange={handleChange}
                rows={2}
                placeholder="Motivo del alta..."
              />
            </div>
          )}
          {showAltaWarning && (
            <div className="alert alert-warning">
              <AlertTriangle size={18} />
              <span>El paciente tiene requerimientos clínicos activos. Por favor, indique el motivo del alta.</span>
            </div>
          )}
        </section>
      )}

      {/* Botones */}
      <div className="form-actions">
        <button type="button" className="btn btn-secondary" onClick={onCancel}>
          <X size={18} /> Cancelar
        </button>
        <button type="submit" className="btn btn-primary" disabled={loading}>
          <Save size={18} /> {loading ? 'Guardando...' : (isReevaluacion ? 'Guardar cambios' : 'Registrar paciente')}
        </button>
      </div>
    </form>
  );
}
