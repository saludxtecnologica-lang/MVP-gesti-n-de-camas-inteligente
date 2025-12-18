import React from 'react';
import { 
  Eye, Check, X, Search, FileText, ArrowRight, LogOut, 
  Lock, Unlock, Clock, ArrowLeftRight, UserPlus, ArrowLeft,
  Heart, Gavel, FileStack, SkipForward
} from 'lucide-react';
import type { Cama, Paciente } from '../types/Index';
import { EstadoCamaEnum } from '../types/Index';

interface CamaCardProps {
  cama: Cama;
  modoManual: boolean;
  onVerPaciente: (paciente: Paciente) => void;
  onReevaluar: (paciente: Paciente) => void;
  onCompletarTraslado: (pacienteId: string) => void;
  onCancelarTraslado: (pacienteId: string) => void;
  onBuscarNuevaCama: (pacienteId: string) => void;
  onIniciarAlta: (pacienteId: string) => void;
  onDarAlta: (pacienteId: string) => void;
  onCancelarAlta: (pacienteId: string) => void;
  onConfirmarEgreso: (pacienteId: string) => void;
  onBloquear: (camaId: string, bloquear: boolean) => void;
  // Handlers específicos para cancelación
  onCancelarDerivacionOrigen?: (pacienteId: string) => void;
  // Handlers para modo manual
  onAsignarManual?: (pacienteId: string) => void;
  onIntercambiar?: (pacienteId: string) => void;
  onEgresarManual?: (pacienteId: string) => void;
  // Handler para omitir pausa de oxígeno
  onOmitirPausaOxigeno?: (pacienteId: string) => void;
}

export function CamaCard({
  cama,
  modoManual,
  onVerPaciente,
  onReevaluar,
  onCompletarTraslado,
  onCancelarTraslado,
  onBuscarNuevaCama,
  onIniciarAlta,
  onDarAlta,
  onCancelarAlta,
  onConfirmarEgreso,
  onBloquear,
  onCancelarDerivacionOrigen,
  onAsignarManual,
  onIntercambiar,
  onEgresarManual,
  onOmitirPausaOxigeno
}: CamaCardProps) {
  const paciente = cama.paciente || cama.paciente_entrante;
  
  // Verificar si está evaluando desescalaje de oxígeno
  const esEvaluandoOxigeno = cama.mensaje_estado?.toLowerCase().includes('oxígeno') || 
                            cama.mensaje_estado?.toLowerCase().includes('oxigeno') ||
                            cama.mensaje_estado?.toLowerCase().includes('desescalaje');

  // Verificar si es un paciente derivado
  const esDerivado = paciente?.derivacion_estado === 'aceptado' || paciente?.tipo_paciente === 'derivado';

  // Parsear casos especiales del paciente
  const getCasosEspeciales = () => {
    if (!paciente) return { cardiocirugia: false, socioJudicial: false, socioSanitario: false };
    
    // Los casos especiales pueden venir como array de strings o como JSON string
    let casos: string[] = [];
    
    if (paciente.casos_especiales) {
      if (Array.isArray(paciente.casos_especiales)) {
        casos = paciente.casos_especiales;
      } else if (typeof paciente.casos_especiales === 'string') {
        try {
          casos = JSON.parse(paciente.casos_especiales);
        } catch {
          casos = [];
        }
      }
    }
    
    // También verificar campos booleanos individuales
    const cardiocirugia = paciente.caso_espera_cardiocirugia || 
                          casos.some(c => c.toLowerCase().includes('cardiocirug') || c.toLowerCase().includes('cardiocirugía'));
    const socioJudicial = paciente.caso_socio_judicial || 
                          casos.some(c => c.toLowerCase().includes('judicial'));
    const socioSanitario = paciente.caso_socio_sanitario || 
                           casos.some(c => c.toLowerCase().includes('sanitario'));
    
    return { cardiocirugia, socioJudicial, socioSanitario };
  };

  const casosEspeciales = getCasosEspeciales();
  const tieneCasosEspeciales = casosEspeciales.cardiocirugia || 
                               casosEspeciales.socioJudicial || 
                               casosEspeciales.socioSanitario;

  const getEstadoTexto = () => {
    // Si hay un mensaje de estado personalizado del backend, mostrarlo
    if (cama.mensaje_estado) {
      return cama.mensaje_estado;
    }
    
    switch (cama.estado) {
      case EstadoCamaEnum.LIBRE:
        return 'Disponible';
      case EstadoCamaEnum.OCUPADA:
        return 'Ocupada';
      case EstadoCamaEnum.TRASLADO_ENTRANTE:
        return 'Paciente asignado - Pendiente llegada';
      case EstadoCamaEnum.CAMA_EN_ESPERA:
        return 'Listo para buscar nueva cama';
      case EstadoCamaEnum.TRASLADO_SALIENTE:
        return 'Buscando nueva cama';
      case EstadoCamaEnum.TRASLADO_CONFIRMADO:
        return 'Nueva cama asignada - Listo para traslado';
      case EstadoCamaEnum.ALTA_SUGERIDA:
        return 'Alta sugerida';
      case EstadoCamaEnum.CAMA_ALTA:
        return 'Alta pendiente';
      case EstadoCamaEnum.EN_LIMPIEZA:
        return 'En limpieza';
      case EstadoCamaEnum.BLOQUEADA:
        return cama.bloqueada_motivo ? `Bloqueada: ${cama.bloqueada_motivo}` : 'Bloqueada';
      case EstadoCamaEnum.ESPERA_DERIVACION:
        return 'Derivación solicitada';
      case EstadoCamaEnum.DERIVACION_CONFIRMADA:
        return 'Derivación aceptada - Confirmar egreso';
      default:
        return cama.estado;
    }
  };

  /**
   * Handler para cancelar traslado
   * Muestra confirmación para pacientes nuevos
   */
  const handleCancelarTraslado = (pacienteId: string) => {
    const esPacienteNuevo = !paciente?.cama_id && 
      (paciente?.tipo_paciente === 'urgencia' || paciente?.tipo_paciente === 'ambulatorio');
    
    if (esPacienteNuevo) {
      if (window.confirm(`¿Está seguro de cancelar y eliminar al paciente ${paciente?.nombre}? Esta acción no se puede deshacer.`)) {
        onCancelarTraslado(pacienteId);
      }
    } else {
      onCancelarTraslado(pacienteId);
    }
  };

  /**
   * Handler para cancelar derivación desde origen
   * Cancela completamente el flujo de derivación
   */
  const handleCancelarDerivacionOrigen = (pacienteId: string) => {
    if (window.confirm('¿Está seguro de cancelar la derivación? El paciente permanecerá en esta cama.')) {
      if (onCancelarDerivacionOrigen) {
        onCancelarDerivacionOrigen(pacienteId);
      } else {
        // Fallback al handler genérico
        onCancelarTraslado(pacienteId);
      }
    }
  };

  const renderBotones = () => {
    const botones: React.ReactNode[] = [];

    // En modo manual, mostrar botones especiales
    if (modoManual) {
      return renderBotonesModoManual();
    }

    // Modo automático - botones normales
    switch (cama.estado) {
      case EstadoCamaEnum.LIBRE:
        botones.push(
          <button
            key="bloquear"
            className="btn btn-sm btn-secondary"
            onClick={() => onBloquear(cama.id, true)}
          >
            <Lock size={14} /> Bloquear
          </button>
        );
        break;

      case EstadoCamaEnum.OCUPADA:
        if (paciente) {
          botones.push(
            <button
              key="ver"
              className="btn btn-sm btn-secondary"
              onClick={() => onVerPaciente(paciente)}
            >
              <Eye size={14} /> Ver
            </button>,
            <button
              key="reevaluar"
              className="btn btn-sm btn-primary"
              onClick={() => onReevaluar(paciente)}
            >
              <FileText size={14} /> Reevaluar
            </button>
          );
          
          // Mostrar botón "Omitir pausa" si está evaluando oxígeno
          if (esEvaluandoOxigeno && onOmitirPausaOxigeno) {
            botones.push(
              <button
                key="omitir-oxigeno"
                className="btn btn-sm btn-warning"
                onClick={() => onOmitirPausaOxigeno(paciente.id)}
                title="Omitir periodo de espera y evaluar inmediatamente"
              >
                <SkipForward size={14} /> Omitir pausa
              </button>
            );
          }
        }
        break;

      case EstadoCamaEnum.TRASLADO_ENTRANTE:
        if (cama.paciente_entrante) {
          const pacienteEntrante = cama.paciente_entrante;
          const esDerivadoEntrante = pacienteEntrante.derivacion_estado === 'aceptado';
          
          botones.push(
            <button
              key="completar"
              className="btn btn-sm btn-success"
              onClick={() => onCompletarTraslado(pacienteEntrante.id)}
            >
              <Check size={14} /> Completar
            </button>,
            <button
              key="cancelar"
              className="btn btn-sm btn-danger"
              onClick={() => handleCancelarTraslado(pacienteEntrante.id)}
              title={esDerivadoEntrante ? "Devolver a lista de derivación" : "Cancelar asignación - vuelve a lista de espera"}
            >
              {esDerivadoEntrante ? <ArrowLeft size={14} /> : <X size={14} />}
              {esDerivadoEntrante ? " Devolver" : " Cancelar"}
            </button>,
            <button
              key="ver"
              className="btn btn-sm btn-secondary"
              onClick={() => onVerPaciente(pacienteEntrante)}
            >
              <Eye size={14} /> Ver
            </button>
          );
        }
        break;

      case EstadoCamaEnum.CAMA_EN_ESPERA:
        // Estado CAMA_EN_ESPERA: Botón "Buscar cama" disponible
        if (paciente) {
          botones.push(
            <button
              key="buscar"
              className="btn btn-sm btn-primary"
              onClick={() => onBuscarNuevaCama(paciente.id)}
            >
              <Search size={14} /> Buscar cama
            </button>,
            <button
              key="ver"
              className="btn btn-sm btn-secondary"
              onClick={() => onVerPaciente(paciente)}
            >
              <Eye size={14} /> Ver
            </button>,
            <button
              key="reevaluar"
              className="btn btn-sm btn-secondary"
              onClick={() => onReevaluar(paciente)}
            >
              <FileText size={14} /> Reevaluar
            </button>
          );
        }
        break;

      case EstadoCamaEnum.TRASLADO_SALIENTE:
        // Estado TRASLADO_SALIENTE: Paciente buscando nueva cama
        // CASO 1: Cancelar aquí vuelve a CAMA_EN_ESPERA y sale de lista
        if (paciente) {
          botones.push(
            <button
              key="cancelar"
              className="btn btn-sm btn-danger"
              onClick={() => onCancelarTraslado(paciente.id)}
              title="Cancelar búsqueda - paciente permanece en esta cama"
            >
              <X size={14} /> Cancelar búsqueda
            </button>,
            <button
              key="ver"
              className="btn btn-sm btn-secondary"
              onClick={() => onVerPaciente(paciente)}
            >
              <Eye size={14} /> Ver
            </button>
          );
        }
        break;

      case EstadoCamaEnum.TRASLADO_CONFIRMADO:
        // Estado TRASLADO_CONFIRMADO: Nueva cama asignada, listo para trasladar
        // CASO 1: Cancelar aquí vuelve a CAMA_EN_ESPERA y sale de lista
        if (paciente) {
          botones.push(
            <button
              key="ver"
              className="btn btn-sm btn-secondary"
              onClick={() => onVerPaciente(paciente)}
            >
              <Eye size={14} /> Ver
            </button>,
            <button
              key="cancelar"
              className="btn btn-sm btn-danger"
              onClick={() => onCancelarTraslado(paciente.id)}
              title="Cancelar traslado - paciente permanece en esta cama"
            >
              <X size={14} /> Cancelar
            </button>
          );
        }
        break;

      case EstadoCamaEnum.ALTA_SUGERIDA:
        if (paciente) {
          botones.push(
            <button
              key="iniciar-alta"
              className="btn btn-sm btn-primary"
              onClick={() => onIniciarAlta(paciente.id)}
            >
              <ArrowRight size={14} /> Iniciar alta
            </button>,
            <button
              key="ver"
              className="btn btn-sm btn-secondary"
              onClick={() => onVerPaciente(paciente)}
            >
              <Eye size={14} /> Ver
            </button>,
            <button
              key="reevaluar"
              className="btn btn-sm btn-secondary"
              onClick={() => onReevaluar(paciente)}
            >
              <FileText size={14} /> Reevaluar
            </button>
          );
        }
        break;

      case EstadoCamaEnum.CAMA_ALTA:
        if (paciente) {
          botones.push(
            <button
              key="dar-alta"
              className="btn btn-sm btn-success"
              onClick={() => onDarAlta(paciente.id)}
            >
              <LogOut size={14} /> Dar alta
            </button>,
            <button
              key="cancelar"
              className="btn btn-sm btn-danger"
              onClick={() => onCancelarAlta(paciente.id)}
            >
              <X size={14} /> Cancelar
            </button>
          );
        }
        break;

      case EstadoCamaEnum.BLOQUEADA:
        botones.push(
          <button
            key="desbloquear"
            className="btn btn-sm btn-secondary"
            onClick={() => onBloquear(cama.id, false)}
          >
            <Unlock size={14} /> Desbloquear
          </button>
        );
        break;

      case EstadoCamaEnum.ESPERA_DERIVACION:
        // Estado ESPERA_DERIVACION: Derivación solicitada, esperando respuesta
        // CASO 4: Cancelar aquí cancela todo el flujo de derivación
        if (paciente) {
          botones.push(
            <button
              key="ver"
              className="btn btn-sm btn-secondary"
              onClick={() => onVerPaciente(paciente)}
            >
              <Eye size={14} /> Ver
            </button>,
            <button
              key="cancelar"
              className="btn btn-sm btn-danger"
              onClick={() => handleCancelarDerivacionOrigen(paciente.id)}
              title="Cancelar derivación - paciente permanece en esta cama"
            >
              <X size={14} /> Cancelar derivación
            </button>
          );
        }
        break;

      case EstadoCamaEnum.DERIVACION_CONFIRMADA:
        // Estado DERIVACION_CONFIRMADA: Derivación aceptada, paciente tiene cama en destino
        // CASO 4: Cancelar aquí cancela todo el flujo de derivación
        if (paciente) {
          botones.push(
            <button
              key="confirmar-egreso"
              className="btn btn-sm btn-success"
              onClick={() => onConfirmarEgreso(paciente.id)}
            >
              <Check size={14} /> Confirmar egreso
            </button>,
            <button
              key="ver"
              className="btn btn-sm btn-secondary"
              onClick={() => onVerPaciente(paciente)}
            >
              <Eye size={14} /> Ver
            </button>,
            <button
              key="cancelar"
              className="btn btn-sm btn-danger"
              onClick={() => handleCancelarDerivacionOrigen(paciente.id)}
              title="Cancelar derivación - paciente permanece en esta cama"
            >
              <X size={14} /> Cancelar
            </button>
          );
        }
        break;

      case EstadoCamaEnum.EN_LIMPIEZA:
        // Sin botones durante limpieza
        break;
    }

    return botones;
  };

  /**
   * Renderiza botones específicos para modo manual
   */
  const renderBotonesModoManual = () => {
    const botones: React.ReactNode[] = [];

    switch (cama.estado) {
      case EstadoCamaEnum.LIBRE:
        botones.push(
          <button
            key="bloquear"
            className="btn btn-sm btn-secondary"
            onClick={() => onBloquear(cama.id, true)}
          >
            <Lock size={14} /> Bloquear
          </button>
        );
        break;

      case EstadoCamaEnum.OCUPADA:
      case EstadoCamaEnum.CAMA_EN_ESPERA:
      case EstadoCamaEnum.TRASLADO_SALIENTE:
      case EstadoCamaEnum.ALTA_SUGERIDA:
        if (paciente) {
          botones.push(
            <button
              key="asignar"
              className="btn btn-sm btn-primary"
              onClick={() => onAsignarManual?.(paciente.id)}
              title="Asignar nueva cama"
            >
              <UserPlus size={14} /> Asignar
            </button>,
            <button
              key="intercambiar"
              className="btn btn-sm btn-warning"
              onClick={() => onIntercambiar?.(paciente.id)}
              title="Intercambiar con otro paciente"
            >
              <ArrowLeftRight size={14} /> Intercambiar
            </button>,
            <button
              key="egresar"
              className="btn btn-sm btn-danger"
              onClick={() => onEgresarManual?.(paciente.id)}
              title="Egresar paciente"
            >
              <LogOut size={14} /> Egresar
            </button>,
            <button
              key="ver"
              className="btn btn-sm btn-secondary"
              onClick={() => onVerPaciente(paciente)}
              title="Ver información del paciente"
            >
              <Eye size={14} /> Ver
            </button>
          );
        }
        break;

      case EstadoCamaEnum.TRASLADO_CONFIRMADO:
        if (paciente) {
          botones.push(
            <button
              key="asignar"
              className="btn btn-sm btn-primary"
              onClick={() => onAsignarManual?.(paciente.id)}
              title="Asignar nueva cama"
            >
              <UserPlus size={14} /> Asignar
            </button>,
            <button
              key="intercambiar"
              className="btn btn-sm btn-warning"
              onClick={() => onIntercambiar?.(paciente.id)}
              title="Intercambiar con otro paciente"
            >
              <ArrowLeftRight size={14} /> Intercambiar
            </button>,
            <button
              key="egresar"
              className="btn btn-sm btn-danger"
              onClick={() => onEgresarManual?.(paciente.id)}
              title="Egresar paciente"
            >
              <LogOut size={14} /> Egresar
            </button>,
            <button
              key="ver"
              className="btn btn-sm btn-secondary"
              onClick={() => onVerPaciente(paciente)}
            >
              <Eye size={14} /> Ver
            </button>
          );
        }
        break;

      case EstadoCamaEnum.TRASLADO_ENTRANTE:
        if (cama.paciente_entrante) {
          botones.push(
            <button
              key="completar"
              className="btn btn-sm btn-success"
              onClick={() => onCompletarTraslado(cama.paciente_entrante!.id)}
            >
              <Check size={14} /> Completar
            </button>,
            <button
              key="cancelar"
              className="btn btn-sm btn-danger"
              onClick={() => handleCancelarTraslado(cama.paciente_entrante!.id)}
            >
              <X size={14} /> Cancelar
            </button>,
            <button
              key="ver"
              className="btn btn-sm btn-secondary"
              onClick={() => onVerPaciente(cama.paciente_entrante!)}
            >
              <Eye size={14} /> Ver
            </button>
          );
        }
        break;

      case EstadoCamaEnum.CAMA_ALTA:
        if (paciente) {
          botones.push(
            <button
              key="dar-alta"
              className="btn btn-sm btn-success"
              onClick={() => onDarAlta(paciente.id)}
            >
              <LogOut size={14} /> Dar alta
            </button>,
            <button
              key="cancelar"
              className="btn btn-sm btn-danger"
              onClick={() => onCancelarAlta(paciente.id)}
            >
              <X size={14} /> Cancelar
            </button>
          );
        }
        break;

      case EstadoCamaEnum.BLOQUEADA:
        botones.push(
          <button
            key="desbloquear"
            className="btn btn-sm btn-secondary"
            onClick={() => onBloquear(cama.id, false)}
          >
            <Unlock size={14} /> Desbloquear
          </button>
        );
        break;

      case EstadoCamaEnum.ESPERA_DERIVACION:
      case EstadoCamaEnum.DERIVACION_CONFIRMADA:
        if (paciente) {
          botones.push(
            <button
              key="ver"
              className="btn btn-sm btn-secondary"
              onClick={() => onVerPaciente(paciente)}
            >
              <Eye size={14} /> Ver
            </button>,
            <button
              key="cancelar"
              className="btn btn-sm btn-danger"
              onClick={() => handleCancelarDerivacionOrigen(paciente.id)}
            >
              <X size={14} /> Cancelar derivación
            </button>
          );
        }
        break;

      case EstadoCamaEnum.EN_LIMPIEZA:
        break;
    }

    return botones;
  };

  return (
    <div className={`cama-card cama-card-${cama.estado}${modoManual ? ' modo-manual' : ''}${esEvaluandoOxigeno ? ' evaluando-oxigeno' : ''}${esDerivado ? ' es-derivado' : ''}`}>
      <div className="cama-card-id">{cama.identificador}</div>
      
      {paciente && (
        <div className="cama-card-paciente">
          <span className="paciente-nombre">{paciente.nombre}</span>
          <div className="paciente-badges">
            {esDerivado && <span className="derivado-badge">Derivado</span>}
            {/* Iconos de casos especiales */}
            {tieneCasosEspeciales && (
              <span className="casos-especiales-icons">
                {casosEspeciales.cardiocirugia && (
                  <span className="caso-icon caso-cardiocirugia" title="Espera Cardiocirugía">
                    <Heart size={14} />
                  </span>
                )}
                {casosEspeciales.socioJudicial && (
                  <span className="caso-icon caso-judicial" title="Caso Socio-Judicial">
                    <Gavel size={14} />
                  </span>
                )}
                {casosEspeciales.socioSanitario && (
                  <span className="caso-icon caso-sanitario" title="Caso Socio-Sanitario">
                    <FileStack size={14} />
                  </span>
                )}
              </span>
            )}
          </div>
        </div>
      )}
      
      <div className="cama-card-estado">
        {/* Mostrar ícono de reloj si está evaluando desescalaje de oxígeno */}
        {esEvaluandoOxigeno && (
          <span className="estado-icono evaluando-oxigeno-icono">
            <Clock size={14} className="spin" />
          </span>
        )}
        {getEstadoTexto()}
        {cama.estado === EstadoCamaEnum.TRASLADO_CONFIRMADO && paciente?.cama_asignada && (
          <span style={{ display: 'block', marginTop: '4px', fontWeight: 500 }}>
            → {paciente.cama_asignada.identificador}
          </span>
        )}
        {cama.estado === EstadoCamaEnum.TRASLADO_CONFIRMADO && cama.cama_asignada_destino && !paciente?.cama_asignada && (
          <span style={{ display: 'block', marginTop: '4px', fontWeight: 500 }}>
            → {cama.cama_asignada_destino}
          </span>
        )}
      </div>
      
      <div className="cama-card-actions">
        {renderBotones()}
      </div>
      
      {/* Indicador visual de modo manual */}
      {modoManual && (
        <div className="modo-manual-indicator">
          MODO MANUAL
        </div>
      )}
    </div>
  );
}
