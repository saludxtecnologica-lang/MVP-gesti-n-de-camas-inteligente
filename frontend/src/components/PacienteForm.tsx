import React, { useState, useCallback } from 'react';
import { Save, X, AlertTriangle } from 'lucide-react';
import type {
  Paciente,
  PacienteCreate,
  PacienteUpdate,
  Hospital,
  SexoEnum,
  TipoEnfermedadEnum,
  TipoAislamientoEnum
} from '../types/Index';
import * as api from '../services/api';

interface PacienteFormProps {
  paciente?: Paciente;
  hospitalId: number;
  hospitales: Hospital[];
  isReevaluacion?: boolean;
  onSubmit: () => void;
  onError: (mensaje: string) => void;
  onCancel: () => void;
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
  const [formData, setFormData] = useState<PacienteCreate>({
    nombre: paciente?.nombre || '',
    run: paciente?.run || '',
    sexo: paciente?.sexo || 'hombre' as SexoEnum,
    edad: paciente?.edad || 0,
    diagnostico: paciente?.diagnostico || '',
    tipo_enfermedad: paciente?.tipo_enfermedad || 'medica' as TipoEnfermedadEnum,
    tipo_aislamiento: paciente?.tipo_aislamiento || 'ninguno' as TipoAislamientoEnum,
    embarazada: paciente?.embarazada || false,
    hospital_id: paciente?.hospital_id || hospitalId,
    
    // Requerimientos que no definen complejidad
    req_kinesioterapia: paciente?.req_kinesioterapia || false,
    req_control_sangre_1x: paciente?.req_control_sangre_1x || false,
    req_curaciones: paciente?.req_curaciones || false,
    req_tratamiento_ev_2x: paciente?.req_tratamiento_ev_2x || false,
    
    // Requerimientos baja complejidad
    req_tratamiento_ev_3x: paciente?.req_tratamiento_ev_3x || false,
    req_control_sangre_2x: paciente?.req_control_sangre_2x || false,
    req_o2_naricera: paciente?.req_o2_naricera || false,
    req_dolor_eva_7: paciente?.req_dolor_eva_7 || false,
    req_o2_multiventuri: paciente?.req_o2_multiventuri || false,
    req_curaciones_complejas: paciente?.req_curaciones_complejas || false,
    req_aspiracion: paciente?.req_aspiracion || false,
    req_observacion: paciente?.req_observacion || false,
    req_observacion_motivo: paciente?.req_observacion_motivo || '',
    req_irrigacion_vesical: paciente?.req_irrigacion_vesical || false,
    req_procedimiento_invasivo: paciente?.req_procedimiento_invasivo || false,
    req_procedimiento_invasivo_detalle: paciente?.req_procedimiento_invasivo_detalle || '',
    
    // Requerimientos UTI
    req_drogas_vasoactivas: paciente?.req_drogas_vasoactivas || false,
    req_sedacion: paciente?.req_sedacion || false,
    req_monitorizacion: paciente?.req_monitorizacion || false,
    req_monitorizacion_motivo: paciente?.req_monitorizacion_motivo || '',
    req_o2_reservorio: paciente?.req_o2_reservorio || false,
    req_dialisis: paciente?.req_dialisis || false,
    req_cnaf: paciente?.req_cnaf || false,
    req_bic_insulina: paciente?.req_bic_insulina || false,
    req_vmni: paciente?.req_vmni || false,
    
    // Requerimientos UCI
    req_vmi: paciente?.req_vmi || false,
    req_procuramiento_o2: paciente?.req_procuramiento_o2 || false,
    
    // Casos especiales
    caso_socio_sanitario: paciente?.caso_socio_sanitario || false,
    caso_socio_judicial: paciente?.caso_socio_judicial || false,
    caso_espera_cardiocirugia: paciente?.caso_espera_cardiocirugia || false,
    
    notas_adicionales: paciente?.notas_adicionales || '',
    
    // Derivación
    derivacion_solicitada: false,
    derivacion_hospital_destino_id: undefined,
    derivacion_motivo: '',
    
    // Alta
    alta_solicitada: false,
    alta_motivo: ''
  });

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
    if (!formData.run.trim()) {
      onError('El RUN es requerido');
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

    // Validar alta con requerimientos
    if (formData.alta_solicitada) {
      const tieneRequerimientosAltos = formData.req_vmi || formData.req_procuramiento_o2 ||
        formData.req_drogas_vasoactivas || formData.req_sedacion || formData.req_monitorizacion ||
        formData.req_dialisis || formData.req_cnaf || formData.req_bic_insulina || formData.req_vmni ||
        formData.req_tratamiento_ev_3x || formData.req_dolor_eva_7 || formData.req_curaciones_complejas ||
        formData.tipo_aislamiento === 'aereo';
      
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
      if (isReevaluacion && paciente) {
        await api.actualizarPaciente(paciente.id, formData as PacienteUpdate);
      } else {
        await api.crearPaciente(formData);
      }
      onSubmit();
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Error al guardar paciente');
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
              <option value="hombre">Hombre</option>
              <option value="mujer">Mujer</option>
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="edad">Edad (años) *</label>
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
          {formData.sexo === 'mujer' && (
            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  name="embarazada"
                  checked={formData.embarazada}
                  onChange={handleChange}
                />
                Embarazada
              </label>
            </div>
          )}
        </div>
      </section>

      {/* Diagnóstico */}
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
              rows={3}
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
            <label htmlFor="tipo_aislamiento">Tipo de aislamiento</label>
            <select
              id="tipo_aislamiento"
              name="tipo_aislamiento"
              value={formData.tipo_aislamiento}
              onChange={handleChange}
            >
              <option value="ninguno">Ninguno</option>
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
            <label><input type="checkbox" name="req_curaciones" checked={formData.req_curaciones} onChange={handleChange} /> Curaciones simples</label>
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
                value={formData.req_observacion_motivo || ''}
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
                value={formData.req_procedimiento_invasivo_detalle || ''}
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
                value={formData.req_monitorizacion_motivo || ''}
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
            value={formData.notas_adicionales || ''}
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
                  value={formData.derivacion_hospital_destino_id || ''}
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
                  value={formData.derivacion_motivo || ''}
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
                value={formData.alta_motivo || ''}
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