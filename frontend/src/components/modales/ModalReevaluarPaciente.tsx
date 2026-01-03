import { useState, useEffect, useMemo, useRef } from 'react';
import { Stethoscope, Cross, FileText, AlertTriangle, User, RefreshCw, ClipboardList, Paperclip, X, Upload, Eye, Send, Clock, Heart, Gavel, Files } from 'lucide-react';
import { Modal, Badge, Button } from '../common';
import { Tooltip } from '../common/Tooltip';
import { useApp } from '../../context/AppContext';
import * as api from '../../services/api';
import { ModalDerivacionDirecta } from './ModalDerivacionDirecta';
import type { 
  Paciente,
  TipoEnfermedadEnum, 
  TipoAislamientoEnum, 
  PacienteUpdate 
} from '../../types';
import { 
  TOOLTIPS, 
  OPCIONES_TIEMPO_HORAS 
} from '../constants/requerimientosConstants';

interface ModalReevaluarPacienteProps {
  isOpen: boolean;
  onClose: () => void;
  paciente: Paciente | null;
}

// Función auxiliar para parsear JSON de forma segura
function safeJsonParse(value: unknown): string[] {
  if (!value) return [];
  if (Array.isArray(value)) return value;
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }
  return [];
}

// Estado inicial del formulario de reevaluación
const getInitialFormState = (paciente: Paciente | null) => {
  if (!paciente) {
    return {
      diagnostico: '',
      tipo_enfermedad: 'medica' as TipoEnfermedadEnum,
      tipo_aislamiento: 'ninguno' as TipoAislamientoEnum,
      notas_adicionales: '',
      es_embarazada: false,
      
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
      req_observacion_tiempo_horas: null as number | null,
      req_irrigacion_vesical_continua: false,
      req_procedimiento_invasivo_quirurgico: false,
      req_procedimiento_invasivo_detalle: '',
      req_preparacion_quirurgica: false,
      req_preparacion_quirurgica_detalle: '',  // NUEVO
      req_nutricion_parenteral: false,
      
      // Requerimientos UTI
      req_droga_vasoactiva: false,
      req_sedacion: false,
      req_monitorizacion: false,
      req_monitorizacion_motivo: '',
      req_monitorizacion_justificacion: '',
      req_monitorizacion_tiempo_horas: null as number | null,
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
      
      // Documento adjunto
      documento_adjunto: null as File | null,
      documento_nombre: '',
      documento_existente: '',

      // Fallecimiento
      paciente_fallecido: false,
      causa_fallecimiento: '',
    };
  }

  // Parsear requerimientos existentes
  const reqNoDefinen = safeJsonParse(paciente.requerimientos_no_definen);
  const reqBaja = safeJsonParse(paciente.requerimientos_baja);
  const reqUti = safeJsonParse(paciente.requerimientos_uti);
  const reqUci = safeJsonParse(paciente.requerimientos_uci);
  const casosEsp = safeJsonParse(paciente.casos_especiales);

  return {
    diagnostico: paciente.diagnostico || '',
    tipo_enfermedad: paciente.tipo_enfermedad || 'medica',
    tipo_aislamiento: paciente.tipo_aislamiento || 'ninguno',
    notas_adicionales: paciente.notas_adicionales || '',
    es_embarazada: paciente.es_embarazada || false,
    
    // No definen
    req_kinesioterapia_respiratoria: reqNoDefinen.includes('Kinesioterapia respiratoria'),
    req_examen_sangre_ocasional: reqNoDefinen.includes('Exámenes de sangre ocasionales'),
    req_curaciones_simples_complejas: reqNoDefinen.includes('Curaciones simples o complejas'),
    req_tratamiento_ev_ocasional: reqNoDefinen.includes('Tratamiento EV ocasional'),
    req_rehabilitacion_funcional: reqNoDefinen.includes('Rehabilitación funcional'),
    
    // Baja
    req_tratamiento_ev_frecuente: reqBaja.includes('Tratamiento EV frecuente'),
    req_tratamiento_infusion_continua: reqBaja.includes('Tratamiento infusión continua'),
    req_examen_sangre_frecuente: reqBaja.includes('Exámenes de sangre frecuentes'),
    req_o2_naricera: reqBaja.includes('O2 por naricera'),
    req_dolor_eva_7: reqBaja.includes('Dolor EVA ≥ 7'),
    req_o2_multiventuri: reqBaja.includes('O2 por Multiventuri'),
    req_curaciones_alta_complejidad: reqBaja.includes('Curaciones de alta complejidad'),
    req_aspiracion_secreciones: reqBaja.includes('Aspiración de secreciones'),
    req_observacion_clinica: reqBaja.includes('Observación clínica'),
    req_observacion_motivo: paciente.motivo_observacion || '',
    req_observacion_justificacion: paciente.justificacion_observacion || '',
    req_observacion_tiempo_horas: paciente.observacion_tiempo_horas || null,
    req_irrigacion_vesical_continua: reqBaja.includes('Irrigación vesical continua'),
    req_procedimiento_invasivo_quirurgico: reqBaja.includes('Procedimiento invasivo quirúrgico'),
    req_procedimiento_invasivo_detalle: paciente.procedimiento_invasivo || '',
    req_preparacion_quirurgica: reqBaja.includes('Preparación quirúrgica'),
    req_preparacion_quirurgica_detalle: (paciente as any).preparacion_quirurgica_detalle || '',  // NUEVO
    req_nutricion_parenteral: reqBaja.includes('Nutrición parenteral'),
    
    // UTI
    req_droga_vasoactiva: reqUti.includes('Droga vasoactiva'),
    req_sedacion: reqUti.includes('Sedación'),
    req_monitorizacion: reqUti.includes('Monitorización continua'),
    req_monitorizacion_motivo: paciente.motivo_monitorizacion || '',
    req_monitorizacion_justificacion: paciente.justificacion_monitorizacion || '',
    req_monitorizacion_tiempo_horas: paciente.monitorizacion_tiempo_horas || null,
    req_o2_reservorio: reqUti.includes('O2 con reservorio'),
    req_dialisis_aguda: reqUti.includes('Diálisis aguda'),
    req_cnaf: reqUti.includes('CNAF'),
    req_bic_insulina: reqUti.includes('BIC insulina'),
    req_vmni: reqUti.includes('VMNI'),
    
    // UCI
    req_vmi: reqUci.includes('VMI'),
    req_procuramiento_organos: reqUci.includes('Procuramiento de órganos'),
    
    // Casos especiales
    caso_socio_sanitario: casosEsp.includes('Socio-sanitario'),
    caso_socio_judicial: casosEsp.includes('Socio-judicial'),
    caso_espera_cardiocirugia: casosEsp.includes('Espera cardiocirugía'),
    
    // Documento
    documento_adjunto: null as File | null,
    documento_nombre: '',
    documento_existente: paciente.documento_adjunto || '',

    // Fallecimiento - prellenar causa con diagnóstico
    paciente_fallecido: paciente.fallecido || false,
    causa_fallecimiento: paciente.fallecido 
      ? (paciente.causa_fallecimiento || paciente.diagnostico || '')
      : (paciente.diagnostico || ''),
  };
};

export function ModalReevaluarPaciente({ isOpen, onClose, paciente }: ModalReevaluarPacienteProps) {
  const { showAlert, recargarTodo } = useApp();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState(getInitialFormState(paciente));
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Estado para modal de derivación
  const [modalDerivacionAbierto, setModalDerivacionAbierto] = useState(false);
  const [pacienteGuardado, setPacienteGuardado] = useState<Paciente | null>(null);

  // Resetear formulario cuando cambia el paciente
  useEffect(() => {
    if (isOpen && paciente) {
      setFormData(getInitialFormState(paciente));
      setPacienteGuardado(null);
    }
  }, [isOpen, paciente]);

  // Handlers genéricos
  const handleChange = (field: string, value: string | boolean | number | null) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleCheckbox = (field: string) => {
    setFormData(prev => ({ ...prev, [field as keyof typeof prev]: !prev[field as keyof typeof prev] }));
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
    if (formData.req_preparacion_quirurgica) baja.push('Preparación quirúrgica');
    if (formData.req_nutricion_parenteral) baja.push('Nutrición parenteral');

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
    if (reqs.uci.length > 0) return { nivel: 'UCI', color: 'bg-red-100 text-red-800' };
    if (reqs.uti.length > 0) return { nivel: 'UTI', color: 'bg-orange-100 text-orange-800' };
    if (reqs.baja.length > 0) return { nivel: 'Baja', color: 'bg-yellow-100 text-yellow-800' };
    return { nivel: 'Sin definir', color: 'bg-gray-100 text-gray-800' };
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
    if (formData.req_preparacion_quirurgica) count++;
    if (formData.req_nutricion_parenteral) count++;
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

  // Función para guardar y continuar (usada por guardar y derivar)
  const guardarReevaluacion = async (): Promise<Paciente | null> => {
    if (!paciente) return null;

    // Validaciones
    if (!formData.diagnostico.trim()) {
      showAlert('error', 'El diagnóstico es requerido');
      return null;
    }

    // Validar campos condicionales solo si deben mostrarse
    if (mostrarMotivoObservacion && formData.req_observacion_clinica && !formData.req_observacion_motivo) {
      showAlert('error', 'Debe indicar el motivo de observación');
      return null;
    }
    if (mostrarMotivoMonitorizacion && formData.req_monitorizacion && !formData.req_monitorizacion_motivo) {
      showAlert('error', 'Debe indicar el motivo de monitorización');
      return null;
    }

     // Validar causa de fallecimiento si está marcado como fallecido
    if (formData.paciente_fallecido && !formData.causa_fallecimiento.trim()) {
      showAlert('error', 'Debe indicar la causa de fallecimiento');
      return null;
    }

    // CONFIRMACIÓN DE SEGURIDAD PARA FALLECIMIENTO
    if (formData.paciente_fallecido && !paciente.fallecido) {
      const confirmado = window.confirm(
        '⚠️ ATENCIÓN: Está a punto de registrar el fallecimiento del paciente.\n\n' +
        `Paciente: ${paciente.nombre}\n` +
        `Causa: ${formData.causa_fallecimiento}\n\n` +
        '¿Está seguro de que desea continuar?'
      );
      
      if (!confirmado) {
        return null;
      }
    }

    const reqs = buildRequerimientos();

    // Determinar si el requerimiento está marcado
    const tieneObservacionClinica = reqs.baja.includes('Observación clínica');
    const tieneMonitorizacion = reqs.uti.includes('Monitorización continua');

    const updateData: PacienteUpdate = {
      diagnostico: formData.diagnostico.trim(),
      tipo_enfermedad: formData.tipo_enfermedad,
      tipo_aislamiento: formData.tipo_aislamiento,
      notas_adicionales: formData.notas_adicionales.trim() || undefined,
      es_embarazada: formData.es_embarazada,
      requerimientos_no_definen: reqs.noDefinen,
      requerimientos_baja: reqs.baja,
      requerimientos_uti: reqs.uti,
      requerimientos_uci: reqs.uci,
      casos_especiales: reqs.casosEspeciales,
      motivo_observacion: mostrarMotivoObservacion ? formData.req_observacion_motivo || undefined : undefined,
      justificacion_observacion: mostrarMotivoObservacion ? formData.req_observacion_justificacion || undefined : undefined,
      motivo_monitorizacion: mostrarMotivoMonitorizacion ? formData.req_monitorizacion_motivo || undefined : undefined,
      justificacion_monitorizacion: mostrarMotivoMonitorizacion ? formData.req_monitorizacion_justificacion || undefined : undefined,
      procedimiento_invasivo: formData.req_procedimiento_invasivo_detalle || undefined,
      preparacion_quirurgica_detalle: formData.req_preparacion_quirurgica_detalle || undefined,
      observacion_tiempo_horas: tieneObservacionClinica 
        ? (formData.req_observacion_tiempo_horas ?? undefined) 
        : 0, // Enviar 0 para indicar que se desmarcó
      
      monitorizacion_tiempo_horas: tieneMonitorizacion 
        ? (formData.req_monitorizacion_tiempo_horas ?? undefined)
        : 0,
      // Fallecimiento
      fallecido: formData.paciente_fallecido,
      causa_fallecimiento: formData.paciente_fallecido ? formData.causa_fallecimiento.trim() : undefined,
    };

    try {
      setLoading(true);
      const pacienteActualizado = await api.actualizarPaciente(paciente.id, updateData);
      
      // Subir documento si hay uno nuevo
      if (formData.documento_adjunto) {
        try {
          const formDataFile = new FormData();
          formDataFile.append('file', formData.documento_adjunto);
          
          const response = await fetch(`${api.getApiBase()}/api/pacientes/${paciente.id}/documento`, {
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
      
      await recargarTodo();
      return pacienteActualizado;
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al reevaluar paciente');
      return null;
    } finally {
      setLoading(false);
    }
  };

  // Enviar formulario normal
  const handleSubmit = async () => {
    const resultado = await guardarReevaluacion();
    if (resultado) {
      showAlert('success', 'Paciente reevaluado exitosamente');
      onClose();
    }
  };

  // Guardar y abrir derivación
  const handleGuardarYDerivar = async () => {
    const resultado = await guardarReevaluacion();
    if (resultado) {
      showAlert('success', 'Reevaluación guardada. Iniciando derivación...');
      setPacienteGuardado(resultado);
      setModalDerivacionAbierto(true);
    }
  };

  // Callback cuando se completa la derivación
  const handleDerivacionCompletada = () => {
    setModalDerivacionAbierto(false);
    setPacienteGuardado(null);
    onClose();
  };

  // Verificar si el paciente ya tiene una derivación activa
  const tieneDerivacionActiva = paciente?.derivacion_solicitada && 
    (paciente?.derivacion_estado === 'pendiente' || paciente?.derivacion_estado === 'aceptada');

  // Componente auxiliar para checkboxes con tooltip
  const CheckboxItemWithTooltip = ({ 
    checked, 
    onChange, 
    label,
    tooltip
  }: { 
    checked: boolean; 
    onChange: () => void; 
    label: string;
    tooltip?: string;
  }) => {
    return (
      <label className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1 rounded">
        <input
          type="checkbox"
          checked={checked}
          onChange={onChange}
          className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
        />
        <span className="text-sm text-gray-700">{label}</span>
        {tooltip && (
          <Tooltip content={tooltip} position="top" iconSize="sm" />
        )}
      </label>
    );
  };

  // Componente checkbox con selector de tiempo
  const CheckboxWithTime = ({ 
    checked, 
    onChange, 
    label,
    tooltip,
    tiempoHoras,
    onTiempoChange,
    tiempoInicio,
    tiempoRestante
  }: { 
    checked: boolean; 
    onChange: () => void; 
    label: string;
    tooltip?: string;
    tiempoHoras: number | null;
    onTiempoChange: (horas: number | null) => void;
    tiempoInicio?: string | null;
    tiempoRestante?: number | null;
  }) => {
    // Formatear tiempo restante
    const formatTiempoRestante = (segundos: number): string => {
      if (segundos <= 0) return 'Completado';
      const horas = Math.floor(segundos / 3600);
      const minutos = Math.floor((segundos % 3600) / 60);
      if (horas > 0) return `${horas}h ${minutos}m restantes`;
      return `${minutos} min restantes`;
    };

    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 flex-wrap">
          <label className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1 rounded">
            <input
              type="checkbox"
              checked={checked}
              onChange={onChange}
              className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">{label}</span>
          </label>
          {tooltip && (
            <Tooltip content={tooltip} position="top" iconSize="sm" />
          )}
          
          {/* Selector de tiempo cuando está marcado */}
          {checked && (
            <div className="flex items-center gap-2 ml-2">
              <Clock className="w-4 h-4 text-gray-500" />
              <select
                value={tiempoHoras || ''}
                onChange={(e) => onTiempoChange(e.target.value ? parseInt(e.target.value) : null)}
                className="text-xs border rounded px-2 py-1 focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Tiempo (opcional)</option>
                {OPCIONES_TIEMPO_HORAS.map(opt => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
        
        {/* Mostrar tiempo restante si hay timer activo */}
        {checked && tiempoHoras && tiempoInicio && tiempoRestante !== undefined && tiempoRestante !== null && (
          <div className="ml-6 flex items-center gap-2 text-xs">
            <Clock className="w-3 h-3 text-blue-500" />
            <span className="text-blue-600">
              {formatTiempoRestante(tiempoRestante)}
            </span>
          </div>
        )}
      </div>
    );
  };

  if (!paciente) return null;

  return (
    <>
      <Modal isOpen={isOpen} onClose={onClose} title="Reevaluar Paciente" size="xl">
        <div className="space-y-6">
          
          {/* ============================================ */}
          {/* CABECERA: INFORMACIÓN DEL PACIENTE */}
          {/* ============================================ */}
          <section className="bg-blue-50 p-4 rounded-lg">
            <h3 className="text-sm font-semibold text-blue-800 flex items-center gap-2 mb-3">
              <User className="w-4 h-4" />
              Paciente
            </h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500">Nombre:</span>
                <span className="ml-2 font-medium">{paciente.nombre}</span>
              </div>
              <div>
                <span className="text-gray-500">RUN:</span>
                <span className="ml-2 font-medium">{paciente.run}</span>
              </div>
              <div>
                <span className="text-gray-500">Edad:</span>
                <span className="ml-2 font-medium">{paciente.edad} años</span>
              </div>
              <div>
                <span className="text-gray-500">Sexo:</span>
                <span className="ml-2 font-medium capitalize">{paciente.sexo === 'mujer' ? 'Femenino' : 'Masculino'}</span>
              </div>
              <div className="col-span-2">
                <span className="text-gray-500">Complejidad estimada:</span>
                <Badge className={`ml-2 ${complejidadEstimada.color}`}>
                  {complejidadEstimada.nivel}
                </Badge>
              </div>
            </div>
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
                <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-1">
                  Tipo de Aislamiento
                  {formData.tipo_aislamiento === 'especial' && (
                    <Tooltip content={TOOLTIPS.aislamiento_especial} position="top" />
                  )}
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
                  <option value="especial">Especial (KPC, C. difficile, COVID-19, Hanta, otros)</option>
                </select>
              </div>
            </div>

            {/* Embarazo (solo mujeres) */}
            {paciente.sexo === 'mujer' && (
              <CheckboxItemWithTooltip
                checked={formData.es_embarazada}
                onChange={() => handleCheckbox('es_embarazada')}
                label="Paciente embarazada"
              />
            )}
          </section>

          {/* ============================================ */}
          {/* SECCIÓN: REQUERIMIENTOS - NO DEFINEN COMPLEJIDAD */}
          {/* ============================================ */}
          <section className="space-y-4">
            <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-2 border-b pb-2">
              <ClipboardList className="w-4 h-4 text-gray-600" />
              Requerimientos (No definen complejidad)
              <Tooltip content={TOOLTIPS.seccion_no_definen} position="top" />
            </h3>
            <div className="grid grid-cols-2 gap-2">
              <CheckboxItemWithTooltip
                checked={formData.req_kinesioterapia_respiratoria}
                onChange={() => handleCheckbox('req_kinesioterapia_respiratoria')}
                label="Kinesioterapia respiratoria"
              />
              <CheckboxItemWithTooltip
                checked={formData.req_examen_sangre_ocasional}
                onChange={() => handleCheckbox('req_examen_sangre_ocasional')}
                label="Exámen de sangre ocasional"
                tooltip={TOOLTIPS.req_examen_sangre_ocasional}
              />
              <CheckboxItemWithTooltip
                checked={formData.req_curaciones_simples_complejas}
                onChange={() => handleCheckbox('req_curaciones_simples_complejas')}
                label="Curaciones simples o complejas"
              />
              <CheckboxItemWithTooltip
                checked={formData.req_tratamiento_ev_ocasional}
                onChange={() => handleCheckbox('req_tratamiento_ev_ocasional')}
                label="Tratamiento endovenoso ocasional"
                tooltip={TOOLTIPS.req_tratamiento_ev_ocasional}
              />
              <CheckboxItemWithTooltip
                checked={formData.req_rehabilitacion_funcional}
                onChange={() => handleCheckbox('req_rehabilitacion_funcional')}
                label="Rehabilitación funcional/motora"
                tooltip={TOOLTIPS.req_rehabilitacion_funcional}
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
              <CheckboxItemWithTooltip
                checked={formData.req_tratamiento_ev_frecuente}
                onChange={() => handleCheckbox('req_tratamiento_ev_frecuente')}
                label="Tratamiento endovenoso frecuente"
                tooltip={TOOLTIPS.req_tratamiento_ev_frecuente}
              />
              <CheckboxItemWithTooltip
                checked={formData.req_tratamiento_infusion_continua}
                onChange={() => handleCheckbox('req_tratamiento_infusion_continua')}
                label="Tratamiento con infusión continua"
                tooltip={TOOLTIPS.req_tratamiento_infusion_continua}
              />
              <CheckboxItemWithTooltip
                checked={formData.req_examen_sangre_frecuente}
                onChange={() => handleCheckbox('req_examen_sangre_frecuente')}
                label="Exámen de sangre frecuente"
                tooltip={TOOLTIPS.req_examen_sangre_frecuente}
              />
              <CheckboxItemWithTooltip
                checked={formData.req_o2_naricera}
                onChange={() => handleCheckbox('req_o2_naricera')}
                label="Oxígeno por naricera"
              />
              <CheckboxItemWithTooltip
                checked={formData.req_dolor_eva_7}
                onChange={() => handleCheckbox('req_dolor_eva_7')}
                label="Dolor ENA ≥ 7"
              />
              <CheckboxItemWithTooltip
                checked={formData.req_o2_multiventuri}
                onChange={() => handleCheckbox('req_o2_multiventuri')}
                label="Oxígeno por mascarilla multiventuri"
              />
              <CheckboxItemWithTooltip
                checked={formData.req_curaciones_alta_complejidad}
                onChange={() => handleCheckbox('req_curaciones_alta_complejidad')}
                label="Curaciones de alta complejidad"
                tooltip={TOOLTIPS.req_curaciones_alta_complejidad}
              />
              <CheckboxItemWithTooltip
                checked={formData.req_aspiracion_secreciones}
                onChange={() => handleCheckbox('req_aspiracion_secreciones')}
                label="Aspiración invasiva de secreciones"
              />
              <CheckboxItemWithTooltip
                checked={formData.req_irrigacion_vesical_continua}
                onChange={() => handleCheckbox('req_irrigacion_vesical_continua')}
                label="Irrigación vesical continua"
              />
              <CheckboxItemWithTooltip
                checked={formData.req_procedimiento_invasivo_quirurgico}
                onChange={() => handleCheckbox('req_procedimiento_invasivo_quirurgico')}
                label="Procedimiento invasivo o quirúrgico en las últimas 24 horas"
              />
              <CheckboxItemWithTooltip
                checked={formData.req_preparacion_quirurgica}
                onChange={() => handleCheckbox('req_preparacion_quirurgica')}
                label="Preparación quirúrgica"
                tooltip={TOOLTIPS.req_preparacion_quirurgica}
              />
              <CheckboxItemWithTooltip
                checked={formData.req_nutricion_parenteral}
                onChange={() => handleCheckbox('req_nutricion_parenteral')}
                label="Nutrición parenteral"
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

            {/* NUEVO: Preparación quirúrgica detalle */}
            {formData.req_preparacion_quirurgica && (
              <div className="mt-2 pl-6 border-l-2 border-yellow-300">
                <label className="block text-sm text-yellow-700 mb-1">
                  Tipo de intervención quirúrgica
                </label>
                <input
                  type="text"
                  value={formData.req_preparacion_quirurgica_detalle}
                  onChange={(e) => handleChange('req_preparacion_quirurgica_detalle', e.target.value)}
                  className="w-full border rounded px-3 py-1.5 text-sm"
                  placeholder="Ej: Colecistectomía, Apendicectomía, etc."
                />
              </div>
            )}

            {/* Observación clínica con tiempo */}
            <CheckboxWithTime
              checked={formData.req_observacion_clinica}
              onChange={() => handleCheckbox('req_observacion_clinica')}
              label="Observación clínica"
              tiempoHoras={formData.req_observacion_tiempo_horas}
              onTiempoChange={(horas) => handleChange('req_observacion_tiempo_horas', horas)}
              tiempoInicio={paciente.observacion_inicio}
              tiempoRestante={paciente.observacion_tiempo_restante}
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
              <CheckboxItemWithTooltip
                checked={formData.req_droga_vasoactiva}
                onChange={() => handleCheckbox('req_droga_vasoactiva')}
                label="Droga vasoactiva"
              />
              <CheckboxItemWithTooltip
                checked={formData.req_sedacion}
                onChange={() => handleCheckbox('req_sedacion')}
                label="Sedación"
              />
              <CheckboxItemWithTooltip
                checked={formData.req_o2_reservorio}
                onChange={() => handleCheckbox('req_o2_reservorio')}
                label="Oxígeno por mascarilla de reservorio"
              />
              <CheckboxItemWithTooltip
                checked={formData.req_dialisis_aguda}
                onChange={() => handleCheckbox('req_dialisis_aguda')}
                label="Diálisis aguda"
              />
              <CheckboxItemWithTooltip
                checked={formData.req_cnaf}
                onChange={() => handleCheckbox('req_cnaf')}
                label="CNAF (Cánula Nasal de Alto Flujo)"
              />
              <CheckboxItemWithTooltip
                checked={formData.req_bic_insulina}
                onChange={() => handleCheckbox('req_bic_insulina')}
                label="BIC insulina"
              />
              <CheckboxItemWithTooltip
                checked={formData.req_vmni}
                onChange={() => handleCheckbox('req_vmni')}
                label="VMNI (Ventilación Mecánica No Invasiva)"
              />
            </div>

            {/* Monitorización con tiempo */}
            <CheckboxWithTime
              checked={formData.req_monitorizacion}
              onChange={() => handleCheckbox('req_monitorizacion')}
              label="Monitorización"
              tooltip={TOOLTIPS.req_monitorizacion}
              tiempoHoras={formData.req_monitorizacion_tiempo_horas}
              onTiempoChange={(horas) => handleChange('req_monitorizacion_tiempo_horas', horas)}
              tiempoInicio={paciente.monitorizacion_inicio}
              tiempoRestante={paciente.monitorizacion_tiempo_restante}
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
              <CheckboxItemWithTooltip
                checked={formData.req_vmi}
                onChange={() => handleCheckbox('req_vmi')}
                label="VMI (Ventilación Mecánica Invasiva)"
              />
              <CheckboxItemWithTooltip
                checked={formData.req_procuramiento_organos}
                onChange={() => handleCheckbox('req_procuramiento_organos')}
                label="Procuramiento de órganos y tejidos"
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
              {/* Caso socio-sanitario con ícono */}
              <label 
                className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-all ${
                  formData.caso_socio_sanitario 
                    ? 'bg-blue-50 border-2 border-blue-300' 
                    : 'bg-gray-50 border border-gray-200 hover:bg-gray-100'
                }`}
              >
                <input
                  type="checkbox"
                  checked={formData.caso_socio_sanitario}
                  onChange={() => handleCheckbox('caso_socio_sanitario')}
                  className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <Files className={`w-4 h-4 ${formData.caso_socio_sanitario ? 'text-blue-500' : 'text-gray-400'}`} />
                <span className={`text-sm ${formData.caso_socio_sanitario ? 'font-medium text-gray-900' : 'text-gray-700'}`}>
                  Caso socio-sanitario
                </span>
              </label>

              {/* Caso socio-judicial con ícono */}
              <label 
                className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-all ${
                  formData.caso_socio_judicial 
                    ? 'bg-amber-50 border-2 border-amber-300' 
                    : 'bg-gray-50 border border-gray-200 hover:bg-gray-100'
                }`}
              >
                <input
                  type="checkbox"
                  checked={formData.caso_socio_judicial}
                  onChange={() => handleCheckbox('caso_socio_judicial')}
                  className="w-4 h-4 rounded border-gray-300 text-amber-600 focus:ring-amber-500"
                />
                <Gavel className={`w-4 h-4 ${formData.caso_socio_judicial ? 'text-amber-600' : 'text-gray-400'}`} />
                <span className={`text-sm ${formData.caso_socio_judicial ? 'font-medium text-gray-900' : 'text-gray-700'}`}>
                  Caso socio-judicial
                </span>
              </label>

              {/* Espera cardiocirugía con ícono */}
              <label 
                className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-all ${
                  formData.caso_espera_cardiocirugia 
                    ? 'bg-red-50 border-2 border-red-300' 
                    : 'bg-gray-50 border border-gray-200 hover:bg-gray-100'
                }`}
              >
                <input
                  type="checkbox"
                  checked={formData.caso_espera_cardiocirugia}
                  onChange={() => handleCheckbox('caso_espera_cardiocirugia')}
                  className="w-4 h-4 rounded border-gray-300 text-red-600 focus:ring-red-500"
                />
                <Heart className={`w-4 h-4 ${formData.caso_espera_cardiocirugia ? 'text-red-500' : 'text-gray-400'}`} />
                <span className={`text-sm ${formData.caso_espera_cardiocirugia ? 'font-medium text-gray-900' : 'text-gray-700'}`}>
                  En espera de cardiocirugía
                </span>
              </label>
            </div>
          </section>
          
          {/* ============================================ */}
          {/* SECCIÓN: REGISTRO DE FALLECIMIENTO */}
          {/* ============================================ */}
          <section className="space-y-4">
            <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-2 border-b pb-2">
              <Cross className="w-4 h-4 text-gray-600" />
              Registro de Fallecimiento
            </h3>
            
            <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
              {/* Checkbox de paciente fallecido */}
              <label 
                className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all ${
                  formData.paciente_fallecido 
                    ? 'bg-gray-700 border-2 border-gray-600' 
                    : 'bg-white border border-gray-300 hover:bg-gray-100'
                }`}
              >
                <input
                  type="checkbox"
                  checked={formData.paciente_fallecido}
                  onChange={() => {
                    const nuevoValor = !formData.paciente_fallecido;
                    setFormData(prev => ({
                      ...prev,
                      paciente_fallecido: nuevoValor,
                      // Prellenar con diagnóstico si se activa
                      causa_fallecimiento: nuevoValor && !prev.causa_fallecimiento 
                        ? (paciente?.diagnostico || '') 
                        : prev.causa_fallecimiento
                    }));
                  }}
                  className="w-5 h-5 rounded border-gray-300 text-gray-700 focus:ring-gray-500"
                />
                <Cross className={`w-5 h-5 ${formData.paciente_fallecido ? 'text-white' : 'text-gray-400'}`} />
                <span className={`text-sm font-medium ${formData.paciente_fallecido ? 'text-white' : 'text-gray-700'}`}>
                  Paciente Fallecido
                </span>
              </label>

              {/* Campo de causa de fallecimiento - solo visible si está marcado */}
              {formData.paciente_fallecido && (
                <div className="mt-4 space-y-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Causa de Fallecimiento <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    value={formData.causa_fallecimiento}
                    onChange={(e) => handleChange('causa_fallecimiento', e.target.value)}
                    rows={3}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-gray-500 focus:border-gray-500"
                    placeholder="Describa la causa del fallecimiento..."
                  />
                  <p className="text-xs text-gray-500">
                    Este campo se ha prellenado con el diagnóstico del paciente. Modifique si es necesario.
                  </p>
                </div>
              )}

              {/* Advertencia visual */}
              {formData.paciente_fallecido && (
                <div className="mt-4 p-3 bg-yellow-50 border border-yellow-300 rounded-lg">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                    <div className="text-sm text-yellow-800">
                      <p className="font-medium">Atención</p>
                      <p className="mt-1">
                        Al guardar con esta opción marcada, la cama pasará a estado de cuidados postmortem.
                        Se le pedirá confirmación antes de guardar.
                      </p>
                    </div>
                  </div>
                </div>
              )}
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
              placeholder="Observaciones clínicas importantes, notas adicionales o información relevante..."
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
            
            {/* Documento existente */}
            {formData.documento_existente && !formData.documento_adjunto && (
              <div className="flex items-center justify-between bg-green-50 p-3 rounded-lg border border-green-200">
                <div className="flex items-center gap-3">
                  <FileText className="w-8 h-8 text-green-600" />
                  <div>
                    <p className="text-sm font-medium text-green-800">Documento actual</p>
                    <p className="text-xs text-green-600">{formData.documento_existente}</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    const pdfUrl = api.getDocumentoUrl(formData.documento_existente);
                    window.open(pdfUrl, '_blank', 'noopener,noreferrer');
                  }}
                  className="flex items-center gap-1 px-3 py-1 text-sm text-green-700 bg-green-100 rounded hover:bg-green-200"
                >
                  <Eye className="w-4 h-4" />
                  Ver
                </button>
              </div>
            )}
            
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-4">
              {!formData.documento_adjunto ? (
                <div className="text-center">
                  <Upload className="mx-auto h-8 w-8 text-gray-400" />
                  <p className="mt-2 text-sm text-gray-600">
                    {formData.documento_existente ? 'Subir nuevo documento (reemplazará el actual)' : 'Adjuntar documento (solo PDF, máx. 10MB)'}
                  </p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf"
                    onChange={handleFileSelect}
                    className="hidden"
                    id="file-upload-reevaluacion"
                  />
                  <label
                    htmlFor="file-upload-reevaluacion"
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
                      <p className="text-xs text-gray-500">Nuevo documento (PDF)</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={handleRemoveFile}
                    className="p-1 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded"
                    title="Eliminar archivo"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
              )}
            </div>
          </section>

          {/* ============================================ */}
          {/* BOTONES DE ACCIÓN */}
          {/* ============================================ */}
          <div className="flex justify-end gap-2 pt-4 border-t sticky bottom-0 bg-white">
            <Button variant="secondary" onClick={onClose}>
              Cancelar
            </Button>
            <Button 
              variant="warning" 
              onClick={handleGuardarYDerivar}
              loading={loading}
              disabled={tieneDerivacionActiva}
              icon={<Send className="w-4 h-4" />}
              title={tieneDerivacionActiva ? 'Ya existe una derivación en proceso' : 'Guardar y solicitar derivación'}
            >
              Guardar y Derivar
            </Button>
            <Button 
              variant="primary" 
              onClick={handleSubmit} 
              loading={loading}
              icon={<RefreshCw className="w-4 h-4" />}
            >
              Guardar Reevaluación
            </Button>
          </div>
        </div>
      </Modal>

      {/* ============================================ */}
      {/* MODAL DE DERIVACIÓN */}
      {/* ============================================ */}
      <ModalDerivacionDirecta
        isOpen={modalDerivacionAbierto}
        onClose={() => {
          setModalDerivacionAbierto(false);
          setPacienteGuardado(null);
        }}
        paciente={pacienteGuardado || paciente}
        onDerivacionCompletada={handleDerivacionCompletada}
      />
    </>
  );
}

export default ModalReevaluarPaciente;