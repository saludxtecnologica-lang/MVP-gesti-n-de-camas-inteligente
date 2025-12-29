import { useState, useEffect, useMemo, useRef } from 'react';
import { User, Stethoscope, FileText, AlertTriangle, ClipboardList, Paperclip, X, Upload } from 'lucide-react';
import { Modal, Button, Badge } from '../common';
import { useApp } from '../../context/AppContext';
import * as api from '../../services/api';
import type { 
  SexoEnum, 
  TipoEnfermedadEnum, 
  TipoAislamientoEnum, 
  TipoPacienteEnum,
  PacienteCreate 
} from '../../types';

interface ModalRegistroPacienteProps {
  isOpen: boolean;
  onClose: () => void;
}

// Estado inicial del formulario
const initialFormState = {
  // Datos básicos
  nombre: '',
  run: '',
  sexo: 'hombre' as SexoEnum,
  edad: '',
  es_embarazada: false,
  diagnostico: '',
  tipo_enfermedad: 'medica' as TipoEnfermedadEnum,
  tipo_aislamiento: 'ninguno' as TipoAislamientoEnum,
  tipo_paciente: 'urgencia' as TipoPacienteEnum, // Solo urgencia o ambulatorio
  
  // Requerimientos que NO definen complejidad
  req_kinesioterapia_respiratoria: false,
  req_examen_sangre_ocasional: false,
  req_curaciones_simples_complejas: false,
  req_tratamiento_ev_ocasional: false,
  req_rehabilitacion_funcional: false,
  
  // Requerimientos BAJA complejidad
  req_tratamiento_ev_frecuente: false,
  req_tratamiento_infusion_continua: false,
  req_examen_sangre_frecuente: false,
  req_o2_naricera: false,
  req_dolor_eva_7: false,
  req_o2_multiventuri: false,
  req_curaciones_alta_complejidad: false,
  req_aspiracion_secreciones: false,
  req_observacion_clinica: false,
  req_observacion_motivo: '',
  req_observacion_justificacion: '',
  req_irrigacion_vesical_continua: false,
  req_procedimiento_invasivo_quirurgico: false,
  req_procedimiento_invasivo_detalle: '',
  
  // Requerimientos UTI
  req_droga_vasoactiva: false,
  req_sedacion: false,
  req_monitorizacion: false,
  req_monitorizacion_motivo: '',
  req_monitorizacion_justificacion: '',
  req_o2_reservorio: false,
  req_dialisis_aguda: false,
  req_cnaf: false,
  req_bic_insulina: false,
  req_vmni: false,
  
  // Requerimientos UCI
  req_vmi: false,
  req_procuramiento_organos: false,
  
  // Casos especiales
  caso_socio_sanitario: false,
  caso_socio_judicial: false,
  caso_espera_cardiocirugia: false,
  
  // Observaciones y notas clínicas
  notas_adicionales: '',
  
  // Documento adjunto
  documento_adjunto: null as File | null,
  documento_nombre: '',
};

export function ModalRegistroPaciente({ isOpen, onClose }: ModalRegistroPacienteProps) {
  const { hospitalSeleccionado, showAlert, recargarTodo } = useApp();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState(initialFormState);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Resetear formulario al abrir
  useEffect(() => {
    if (isOpen) {
      setFormData(initialFormState);
    }
  }, [isOpen]);

  // Handlers genéricos
  const handleChange = (field: string, value: string | boolean | number) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleCheckbox = (field: string) => {
    setFormData(prev => ({ ...prev, [field]: !prev[field as keyof typeof prev] }));
  };

  // Manejo de archivos
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        showAlert('error', 'Solo se permiten archivos PDF');
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        showAlert('error', 'El archivo no debe superar 10MB');
        return;
      }
      setFormData(prev => ({
        ...prev,
        documento_adjunto: file,
        documento_nombre: file.name
      }));
    }
  };

  const handleRemoveFile = () => {
    setFormData(prev => ({
      ...prev,
      documento_adjunto: null,
      documento_nombre: ''
    }));
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Construir arrays de requerimientos
  const buildRequerimientos = () => {
    const noDefinen: string[] = [];
    const baja: string[] = [];
    const uti: string[] = [];
    const uci: string[] = [];
    const casosEspeciales: string[] = [];

    // No definen complejidad
    if (formData.req_kinesioterapia_respiratoria) noDefinen.push('Kinesioterapia respiratoria');
    if (formData.req_examen_sangre_ocasional) noDefinen.push('Exámenes de sangre ocasionales');
    if (formData.req_curaciones_simples_complejas) noDefinen.push('Curaciones simples o complejas');
    if (formData.req_tratamiento_ev_ocasional) noDefinen.push('Tratamiento EV ocasional');
    if (formData.req_rehabilitacion_funcional) noDefinen.push('Rehabilitación funcional');

    // Baja complejidad
    if (formData.req_tratamiento_ev_frecuente) baja.push('Tratamiento EV frecuente');
    if (formData.req_tratamiento_infusion_continua) baja.push('Tratamiento infusión continua');
    if (formData.req_examen_sangre_frecuente) baja.push('Exámenes de sangre frecuentes');
    if (formData.req_o2_naricera) baja.push('O2 por naricera');
    if (formData.req_dolor_eva_7) baja.push('Dolor EVA ≥ 7');
    if (formData.req_o2_multiventuri) baja.push('O2 por Multiventuri');
    if (formData.req_curaciones_alta_complejidad) baja.push('Curaciones de alta complejidad');
    if (formData.req_aspiracion_secreciones) baja.push('Aspiración de secreciones');
    if (formData.req_observacion_clinica) baja.push('Observación clínica');
    if (formData.req_irrigacion_vesical_continua) baja.push('Irrigación vesical continua');
    if (formData.req_procedimiento_invasivo_quirurgico) baja.push('Procedimiento invasivo quirúrgico');

    // UTI
    if (formData.req_droga_vasoactiva) uti.push('Droga vasoactiva');
    if (formData.req_sedacion) uti.push('Sedación');
    if (formData.req_monitorizacion) uti.push('Monitorización continua');
    if (formData.req_o2_reservorio) uti.push('O2 con reservorio');
    if (formData.req_dialisis_aguda) uti.push('Diálisis aguda');
    if (formData.req_cnaf) uti.push('CNAF');
    if (formData.req_bic_insulina) uti.push('BIC insulina');
    if (formData.req_vmni) uti.push('VMNI');

    // UCI
    if (formData.req_vmi) uci.push('VMI');
    if (formData.req_procuramiento_organos) uci.push('Procuramiento de órganos');

    // Casos especiales
    if (formData.caso_socio_sanitario) casosEspeciales.push('Socio-sanitario');
    if (formData.caso_socio_judicial) casosEspeciales.push('Socio-judicial');
    if (formData.caso_espera_cardiocirugia) casosEspeciales.push('Espera cardiocirugía');

    return { noDefinen, baja, uti, uci, casosEspeciales };
  };

  // Calcular complejidad estimada para mostrar al usuario
  const complejidadEstimada = useMemo(() => {
    const reqs = buildRequerimientos();
    if (reqs.uci.length > 0) return { nivel: 'UCI', color: 'bg-red-100 text-red-800', valor: 'alta' };
    if (reqs.uti.length > 0) return { nivel: 'UTI', color: 'bg-orange-100 text-orange-800', valor: 'media' };
    if (reqs.baja.length > 0) return { nivel: 'Baja', color: 'bg-yellow-100 text-yellow-800', valor: 'baja' };
    return { nivel: 'Sin definir', color: 'bg-gray-100 text-gray-800', valor: 'ninguna' };
  }, [formData]);

  // Contar requerimientos de baja complejidad (excepto observación)
  const countOtrosReqBaja = useMemo(() => {
    let count = 0;
    if (formData.req_tratamiento_ev_frecuente) count++;
    if (formData.req_tratamiento_infusion_continua) count++;
    if (formData.req_examen_sangre_frecuente) count++;
    if (formData.req_o2_naricera) count++;
    if (formData.req_dolor_eva_7) count++;
    if (formData.req_o2_multiventuri) count++;
    if (formData.req_curaciones_alta_complejidad) count++;
    if (formData.req_aspiracion_secreciones) count++;
    if (formData.req_irrigacion_vesical_continua) count++;
    if (formData.req_procedimiento_invasivo_quirurgico) count++;
    return count;
  }, [formData]);

  // Contar requerimientos UTI/UCI (excepto monitorización)
  const countOtrosReqUtiUci = useMemo(() => {
    let count = 0;
    if (formData.req_droga_vasoactiva) count++;
    if (formData.req_sedacion) count++;
    if (formData.req_o2_reservorio) count++;
    if (formData.req_dialisis_aguda) count++;
    if (formData.req_cnaf) count++;
    if (formData.req_bic_insulina) count++;
    if (formData.req_vmni) count++;
    // UCI
    if (formData.req_vmi) count++;
    if (formData.req_procuramiento_organos) count++;
    return count;
  }, [formData]);

  // Mostrar motivo de observación solo si es el único req de baja complejidad
  const mostrarMotivoObservacion = formData.req_observacion_clinica && countOtrosReqBaja === 0;
  
  // Mostrar motivo de monitorización solo si es el único req UTI/UCI
  const mostrarMotivoMonitorizacion = formData.req_monitorizacion && countOtrosReqUtiUci === 0;

  // Enviar formulario
  const handleSubmit = async () => {
    // Validaciones básicas
    if (!formData.nombre.trim()) {
      showAlert('error', 'El nombre es requerido');
      return;
    }
    if (!formData.run.trim()) {
      showAlert('error', 'El RUN es requerido');
      return;
    }
    if (!formData.edad || parseInt(formData.edad) <= 0) {
      showAlert('error', 'La edad debe ser mayor a 0');
      return;
    }
    if (!formData.diagnostico.trim()) {
      showAlert('error', 'El diagnóstico es requerido');
      return;
    }
    if (!hospitalSeleccionado) {
      showAlert('error', 'Debe seleccionar un hospital');
      return;
    }

    // Validar campos condicionales solo si deben mostrarse
    if (mostrarMotivoObservacion && formData.req_observacion_clinica && !formData.req_observacion_motivo) {
      showAlert('error', 'Debe indicar el motivo de observación');
      return;
    }
    if (mostrarMotivoMonitorizacion && formData.req_monitorizacion && !formData.req_monitorizacion_motivo) {
      showAlert('error', 'Debe indicar el motivo de monitorización');
      return;
    }

    const reqs = buildRequerimientos();

    const pacienteData: PacienteCreate = {
      nombre: formData.nombre.trim(),
      run: formData.run.trim(),
      sexo: formData.sexo,
      edad: parseInt(formData.edad),
      es_embarazada: formData.es_embarazada,
      diagnostico: formData.diagnostico.trim(),
      tipo_enfermedad: formData.tipo_enfermedad,
      tipo_aislamiento: formData.tipo_aislamiento,
      notas_adicionales: formData.notas_adicionales.trim() || undefined,
      tipo_paciente: formData.tipo_paciente,
      hospital_id: hospitalSeleccionado.id,
      requerimientos_no_definen: reqs.noDefinen.length > 0 ? reqs.noDefinen : undefined,
      requerimientos_baja: reqs.baja.length > 0 ? reqs.baja : undefined,
      requerimientos_uti: reqs.uti.length > 0 ? reqs.uti : undefined,
      requerimientos_uci: reqs.uci.length > 0 ? reqs.uci : undefined,
      casos_especiales: reqs.casosEspeciales.length > 0 ? reqs.casosEspeciales : undefined,
      motivo_observacion: mostrarMotivoObservacion ? formData.req_observacion_motivo || undefined : undefined,
      justificacion_observacion: mostrarMotivoObservacion ? formData.req_observacion_justificacion || undefined : undefined,
      motivo_monitorizacion: mostrarMotivoMonitorizacion ? formData.req_monitorizacion_motivo || undefined : undefined,
      justificacion_monitorizacion: mostrarMotivoMonitorizacion ? formData.req_monitorizacion_justificacion || undefined : undefined,
      procedimiento_invasivo: formData.req_procedimiento_invasivo_detalle || undefined,
    };

    try {
      setLoading(true);
      const pacienteCreado = await api.crearPaciente(pacienteData);
      
      // Subir documento si existe
      if (formData.documento_adjunto && pacienteCreado.id) {
        try {
          const formDataFile = new FormData();
          formDataFile.append('file', formData.documento_adjunto);
          
          const response = await fetch(`${api.getApiBase()}/api/pacientes/${pacienteCreado.id}/documento`, {
            method: 'POST',
            body: formDataFile,
          });
          
          if (!response.ok) {
            console.error('Error al subir documento');
          }
        } catch (docError) {
          console.error('Error al subir documento:', docError);
        }
      }
      
      showAlert('success', 'Paciente registrado y agregado a lista de espera');
      await recargarTodo();
      onClose();
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al registrar paciente');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Registrar Nuevo Paciente" size="xl">
      <div className="space-y-6">
        
        {/* ============================================ */}
        {/* DATOS BÁSICOS DEL PACIENTE */}
        {/* ============================================ */}
        <section className="space-y-4">
          <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-2 border-b pb-2">
            <User className="w-4 h-4 text-blue-600" />
            Datos del Paciente
          </h3>
          
          <div className="grid grid-cols-2 gap-4">
            {/* Nombre */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nombre completo <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formData.nombre}
                onChange={(e) => handleChange('nombre', e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
                placeholder="Nombre del paciente"
              />
            </div>

            {/* RUN */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                RUN <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formData.run}
                onChange={(e) => handleChange('run', e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
                placeholder="12.345.678-9"
              />
            </div>

            {/* Sexo */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Sexo <span className="text-red-500">*</span>
              </label>
              <select
                value={formData.sexo}
                onChange={(e) => handleChange('sexo', e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
              >
                <option value="hombre">Masculino</option>
                <option value="mujer">Femenino</option>
              </select>
            </div>

            {/* Edad */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Edad <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                value={formData.edad}
                onChange={(e) => handleChange('edad', e.target.value)}
                min="0"
                max="120"
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
                placeholder="Años"
              />
            </div>

            {/* Tipo paciente */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Tipo de Paciente <span className="text-red-500">*</span>
              </label>
              <select
                value={formData.tipo_paciente}
                onChange={(e) => handleChange('tipo_paciente', e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
              >
                <option value="urgencia">Urgencia</option>
                <option value="ambulatorio">Ambulatorio</option>
              </select>
            </div>

            {/* Complejidad estimada (solo lectura) */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Complejidad Estimada
              </label>
              <div className="w-full border rounded-lg px-3 py-2 text-sm bg-gray-50">
                <Badge className={complejidadEstimada.color}>
                  {complejidadEstimada.nivel}
                </Badge>
              </div>
            </div>
          </div>

          {/* Embarazo (solo mujeres) */}
          {formData.sexo === 'mujer' && (
            <CheckboxItem
              checked={formData.es_embarazada}
              onChange={() => handleCheckbox('es_embarazada')}
              label="Paciente embarazada"
            />
          )}
        </section>

        {/* ============================================ */}
        {/* SECCIÓN: INFORMACIÓN CLÍNICA */}
        {/* ============================================ */}
        <section className="space-y-4">
          <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-2 border-b pb-2">
            <FileText className="w-4 h-4 text-green-600" />
            Información Clínica
          </h3>

          {/* Diagnóstico */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Diagnóstico <span className="text-red-500">*</span>
            </label>
            <textarea
              value={formData.diagnostico}
              onChange={(e) => handleChange('diagnostico', e.target.value)}
              rows={2}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
              placeholder="Descripción del diagnóstico"
            />
          </div>

          {/* Tipo de enfermedad y Aislamiento */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Tipo de Enfermedad
              </label>
              <select
                value={formData.tipo_enfermedad}
                onChange={(e) => handleChange('tipo_enfermedad', e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
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

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Tipo de Aislamiento
              </label>
              <select
                value={formData.tipo_aislamiento}
                onChange={(e) => handleChange('tipo_aislamiento', e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
              >
                <option value="ninguno">Sin aislamiento</option>
                <option value="contacto">Contacto</option>
                <option value="gotitas">Gotitas</option>
                <option value="aereo">Aéreo</option>
                <option value="ambiente_protegido">Ambiente protegido</option>
                <option value="especial">Especial</option>
              </select>
            </div>
          </div>
        </section>

        {/* ============================================ */}
        {/* SECCIÓN: REQUERIMIENTOS - NO DEFINEN COMPLEJIDAD */}
        {/* ============================================ */}
        <section className="space-y-4">
          <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-2 border-b pb-2">
            <ClipboardList className="w-4 h-4 text-gray-600" />
            Requerimientos (No definen complejidad)
          </h3>
          <div className="grid grid-cols-2 gap-2">
            <CheckboxItem
              checked={formData.req_kinesioterapia_respiratoria}
              onChange={() => handleCheckbox('req_kinesioterapia_respiratoria')}
              label="Kinesioterapia respiratoria"
            />
            <CheckboxItem
              checked={formData.req_examen_sangre_ocasional}
              onChange={() => handleCheckbox('req_examen_sangre_ocasional')}
              label="Exámenes de sangre ocasionales"
            />
            <CheckboxItem
              checked={formData.req_curaciones_simples_complejas}
              onChange={() => handleCheckbox('req_curaciones_simples_complejas')}
              label="Curaciones simples o complejas"
            />
            <CheckboxItem
              checked={formData.req_tratamiento_ev_ocasional}
              onChange={() => handleCheckbox('req_tratamiento_ev_ocasional')}
              label="Tratamiento EV ocasional"
            />
            <CheckboxItem
              checked={formData.req_rehabilitacion_funcional}
              onChange={() => handleCheckbox('req_rehabilitacion_funcional')}
              label="Rehabilitación funcional"
            />
          </div>
        </section>

        {/* ============================================ */}
        {/* SECCIÓN: REQUERIMIENTOS BAJA COMPLEJIDAD */}
        {/* ============================================ */}
        <section className="space-y-4 p-4 bg-yellow-50 rounded-lg">
          <h3 className="text-sm font-semibold text-yellow-800 flex items-center gap-2">
            <Stethoscope className="w-4 h-4" />
            Requerimientos BAJA Complejidad
          </h3>
          <div className="grid grid-cols-2 gap-2">
            <CheckboxItem
              checked={formData.req_tratamiento_ev_frecuente}
              onChange={() => handleCheckbox('req_tratamiento_ev_frecuente')}
              label="Tratamiento EV frecuente"
            />
            <CheckboxItem
              checked={formData.req_tratamiento_infusion_continua}
              onChange={() => handleCheckbox('req_tratamiento_infusion_continua')}
              label="Tratamiento infusión continua"
            />
            <CheckboxItem
              checked={formData.req_examen_sangre_frecuente}
              onChange={() => handleCheckbox('req_examen_sangre_frecuente')}
              label="Exámenes de sangre frecuentes"
            />
            <CheckboxItem
              checked={formData.req_o2_naricera}
              onChange={() => handleCheckbox('req_o2_naricera')}
              label="O2 por naricera"
            />
            <CheckboxItem
              checked={formData.req_dolor_eva_7}
              onChange={() => handleCheckbox('req_dolor_eva_7')}
              label="Dolor EVA ≥ 7"
            />
            <CheckboxItem
              checked={formData.req_o2_multiventuri}
              onChange={() => handleCheckbox('req_o2_multiventuri')}
              label="O2 por Multiventuri"
            />
            <CheckboxItem
              checked={formData.req_curaciones_alta_complejidad}
              onChange={() => handleCheckbox('req_curaciones_alta_complejidad')}
              label="Curaciones de alta complejidad"
            />
            <CheckboxItem
              checked={formData.req_aspiracion_secreciones}
              onChange={() => handleCheckbox('req_aspiracion_secreciones')}
              label="Aspiración de secreciones"
            />
            <CheckboxItem
              checked={formData.req_irrigacion_vesical_continua}
              onChange={() => handleCheckbox('req_irrigacion_vesical_continua')}
              label="Irrigación vesical continua"
            />
            <CheckboxItem
              checked={formData.req_procedimiento_invasivo_quirurgico}
              onChange={() => handleCheckbox('req_procedimiento_invasivo_quirurgico')}
              label="Procedimiento invasivo quirúrgico"
            />
          </div>

          {/* Procedimiento invasivo detalle */}
          {formData.req_procedimiento_invasivo_quirurgico && (
            <div className="mt-2 pl-6 border-l-2 border-yellow-300">
              <label className="block text-sm text-yellow-700 mb-1">
                Detalles del procedimiento invasivo
              </label>
              <input
                type="text"
                value={formData.req_procedimiento_invasivo_detalle}
                onChange={(e) => handleChange('req_procedimiento_invasivo_detalle', e.target.value)}
                className="w-full border rounded px-3 py-1.5 text-sm"
                placeholder="Ej: Drenaje pleural, etc."
              />
            </div>
          )}

          {/* Observación clínica */}
          <CheckboxItem
            checked={formData.req_observacion_clinica}
            onChange={() => handleCheckbox('req_observacion_clinica')}
            label="Observación clínica"
          />
          
          {/* Mostrar campos solo si observación es el único req de baja complejidad */}
          {mostrarMotivoObservacion && (
            <div className="mt-2 pl-6 border-l-2 border-yellow-300 space-y-2">
              <div>
                <label className="block text-sm text-yellow-700 mb-1">
                  Motivo de observación <span className="text-red-500">*</span>
                </label>
                <select
                  value={formData.req_observacion_motivo}
                  onChange={(e) => handleChange('req_observacion_motivo', e.target.value)}
                  className="w-full border rounded px-3 py-1.5 text-sm"
                >
                  <option value="">Seleccionar...</option>
                  <option value="post_operatorio">Post operatorio</option>
                  <option value="sospecha_diagnostica">Sospecha diagnóstica</option>
                  <option value="estudio">En estudio</option>
                  <option value="otro">Otro</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-yellow-700 mb-1">
                  Justificación
                </label>
                <textarea
                  value={formData.req_observacion_justificacion}
                  onChange={(e) => handleChange('req_observacion_justificacion', e.target.value)}
                  rows={2}
                  className="w-full border rounded px-3 py-1.5 text-sm"
                  placeholder="Justifique brevemente..."
                />
              </div>
            </div>
          )}
        </section>

        {/* ============================================ */}
        {/* SECCIÓN: REQUERIMIENTOS UTI */}
        {/* ============================================ */}
        <section className="space-y-4 p-4 bg-orange-50 rounded-lg">
          <h3 className="text-sm font-semibold text-orange-800 flex items-center gap-2">
            <Stethoscope className="w-4 h-4" />
            Requerimientos UTI (Mediana Complejidad)
          </h3>
          <div className="grid grid-cols-2 gap-2">
            <CheckboxItem
              checked={formData.req_droga_vasoactiva}
              onChange={() => handleCheckbox('req_droga_vasoactiva')}
              label="Droga vasoactiva"
            />
            <CheckboxItem
              checked={formData.req_sedacion}
              onChange={() => handleCheckbox('req_sedacion')}
              label="Sedación"
            />
            <CheckboxItem
              checked={formData.req_o2_reservorio}
              onChange={() => handleCheckbox('req_o2_reservorio')}
              label="O2 con reservorio"
            />
            <CheckboxItem
              checked={formData.req_dialisis_aguda}
              onChange={() => handleCheckbox('req_dialisis_aguda')}
              label="Diálisis aguda"
            />
            <CheckboxItem
              checked={formData.req_cnaf}
              onChange={() => handleCheckbox('req_cnaf')}
              label="CNAF"
            />
            <CheckboxItem
              checked={formData.req_bic_insulina}
              onChange={() => handleCheckbox('req_bic_insulina')}
              label="BIC insulina"
            />
            <CheckboxItem
              checked={formData.req_vmni}
              onChange={() => handleCheckbox('req_vmni')}
              label="VMNI"
            />
          </div>

          {/* Monitorización */}
          <CheckboxItem
            checked={formData.req_monitorizacion}
            onChange={() => handleCheckbox('req_monitorizacion')}
            label="Monitorización continua"
          />
          
          {/* Mostrar campos solo si monitorización es el único req UTI/UCI */}
          {mostrarMotivoMonitorizacion && (
            <div className="mt-2 pl-6 border-l-2 border-orange-300 space-y-2">
              <div>
                <label className="block text-sm text-orange-700 mb-1">
                  Motivo de monitorización <span className="text-red-500">*</span>
                </label>
                <select
                  value={formData.req_monitorizacion_motivo}
                  onChange={(e) => handleChange('req_monitorizacion_motivo', e.target.value)}
                  className="w-full border rounded px-3 py-1.5 text-sm"
                >
                  <option value="">Seleccionar...</option>
                  <option value="arritmia">Arritmia</option>
                  <option value="inestabilidad_hemodinamica">Inestabilidad hemodinámica</option>
                  <option value="post_procedimiento">Post procedimiento</option>
                  <option value="otro">Otro</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-orange-700 mb-1">
                  Justificación
                </label>
                <textarea
                  value={formData.req_monitorizacion_justificacion}
                  onChange={(e) => handleChange('req_monitorizacion_justificacion', e.target.value)}
                  rows={2}
                  className="w-full border rounded px-3 py-1.5 text-sm"
                  placeholder="Justifique brevemente..."
                />
              </div>
            </div>
          )}
        </section>

        {/* ============================================ */}
        {/* SECCIÓN: REQUERIMIENTOS UCI */}
        {/* ============================================ */}
        <section className="space-y-4 p-4 bg-red-50 rounded-lg">
          <h3 className="text-sm font-semibold text-red-800 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            Requerimientos UCI (Alta Complejidad)
          </h3>
          <div className="grid grid-cols-2 gap-2">
            <CheckboxItem
              checked={formData.req_vmi}
              onChange={() => handleCheckbox('req_vmi')}
              label="VMI (Ventilación Mecánica Invasiva)"
            />
            <CheckboxItem
              checked={formData.req_procuramiento_organos}
              onChange={() => handleCheckbox('req_procuramiento_organos')}
              label="Procuramiento de órganos"
            />
          </div>
        </section>

        {/* ============================================ */}
        {/* SECCIÓN: CASOS ESPECIALES */}
        {/* ============================================ */}
        <section className="space-y-4">
          <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-2 border-b pb-2">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            Casos Especiales
          </h3>
          <div className="grid grid-cols-3 gap-2">
            <CheckboxItem
              checked={formData.caso_socio_sanitario}
              onChange={() => handleCheckbox('caso_socio_sanitario')}
              label="Caso socio-sanitario"
            />
            <CheckboxItem
              checked={formData.caso_socio_judicial}
              onChange={() => handleCheckbox('caso_socio_judicial')}
              label="Caso socio-judicial"
            />
            <CheckboxItem
              checked={formData.caso_espera_cardiocirugia}
              onChange={() => handleCheckbox('caso_espera_cardiocirugia')}
              label="En espera de cardiocirugía"
            />
          </div>
        </section>

        {/* ============================================ */}
        {/* SECCIÓN: OBSERVACIONES Y NOTAS CLÍNICAS */}
        {/* ============================================ */}
        <section className="space-y-4">
          <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-2 border-b pb-2">
            <FileText className="w-4 h-4 text-gray-600" />
            Observaciones y Notas Clínicas
          </h3>
          <textarea
            value={formData.notas_adicionales}
            onChange={(e) => handleChange('notas_adicionales', e.target.value)}
            rows={3}
            className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
            placeholder="Observaciones clínicas importantes, notas adicionales o información relevante para la asignación de cama..."
          />
        </section>

        {/* ============================================ */}
        {/* SECCIÓN: DOCUMENTOS ADJUNTOS */}
        {/* ============================================ */}
        <section className="space-y-4">
          <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-2 border-b pb-2">
            <Paperclip className="w-4 h-4 text-gray-600" />
            Documentos Adjuntos
          </h3>
          
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-4">
            {!formData.documento_adjunto ? (
              <div className="text-center">
                <Upload className="mx-auto h-8 w-8 text-gray-400" />
                <p className="mt-2 text-sm text-gray-600">
                  Adjuntar documento (solo PDF, máx. 10MB)
                </p>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf"
                  onChange={handleFileSelect}
                  className="hidden"
                  id="file-upload"
                />
                <label
                  htmlFor="file-upload"
                  className="mt-2 inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg cursor-pointer hover:bg-blue-100"
                >
                  <Paperclip className="w-4 h-4" />
                  Seleccionar archivo
                </label>
              </div>
            ) : (
              <div className="flex items-center justify-between bg-gray-50 p-3 rounded-lg">
                <div className="flex items-center gap-3">
                  <FileText className="w-8 h-8 text-red-500" />
                  <div>
                    <p className="text-sm font-medium text-gray-800">{formData.documento_nombre}</p>
                    <p className="text-xs text-gray-500">PDF</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleRemoveFile}
                    className="p-1 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded"
                    title="Eliminar archivo"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
              </div>
            )}
          </div>
        </section>

        {/* ============================================ */}
        {/* BOTONES DE ACCIÓN */}
        {/* ============================================ */}
        <div className="flex justify-between items-center pt-4 border-t sticky bottom-0 bg-white">
          <div className="text-sm text-gray-500">
            Hospital: <span className="font-medium">{hospitalSeleccionado?.nombre}</span>
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={onClose}>
              Cancelar
            </Button>
            <Button variant="primary" onClick={handleSubmit} loading={loading}>
              Registrar Paciente
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}

// Componente auxiliar para checkboxes
function CheckboxItem({ 
  checked, 
  onChange, 
  label 
}: { 
  checked: boolean; 
  onChange: () => void; 
  label: string;
}) {
  return (
    <label className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1 rounded">
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
      />
      <span className="text-sm text-gray-700">{label}</span>
    </label>
  );
}