import React, { useMemo } from 'react';
import { User, ArrowDownCircle, ArrowUpCircle } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { useAuth } from '../../context/AuthContext';
import { useModal } from '../../context/ModalContext';
import type { Cama, Paciente } from '../../types';
import { formatEstado, formatComplejidad } from '../../utils';

// Roles globales que pueden ver todos los servicios
const ROLES_GLOBALES = [
  'programador',
  'directivo_red',
  'directivo_hospital',
  'gestor_camas'
];

interface PacienteTraslado extends Paciente {
  cama_identificador?: string;
  servicio_nombre?: string;
  tipo_traslado: 'entrante' | 'saliente';
  estado_cama?: string;
}

interface ResumenTrasladosProps {
  filtroServicio: string;
}

export function ResumenTraslados({ filtroServicio }: ResumenTrasladosProps) {
  const { camas, listaEspera, dataVersion } = useApp();
  const { user } = useAuth();
  const { openModal } = useModal();

  // Determinar si el usuario tiene acceso global
  const esRolGlobal = user?.rol && ROLES_GLOBALES.includes(user.rol);
  const servicioUsuario = user?.servicio_id;

  // ============================================
  // OBTENER PACIENTES EN TRASLADO
  // ============================================
  const pacientesEnTraslado = useMemo(() => {
    const salientes: PacienteTraslado[] = [];
    const entrantesMap = new Map<string, PacienteTraslado>(); // Map solo para entrantes

    // Estados de traslado entrante (SIN cama_en_espera)
    const estadosEntrantes = ['traslado_entrante'];

    // Estados de traslado saliente (incluye fallecidos)
    const estadosSalientes = [
      'traslado_saliente',
      'traslado_confirmado',
      'espera_derivacion',
      'derivacion_confirmada',
      'fallecido'  // Pacientes fallecidos también son salientes
    ];

    // PASO 1: Agregar pacientes SALIENTES (sin eliminar duplicados)
    // Un paciente puede estar saliendo de un servicio simultáneamente
    camas.forEach(cama => {
      // Aplicar filtro de servicio del Dashboard
      if (filtroServicio !== 'todos' && cama.servicio_nombre !== filtroServicio) {
        return;
      }

      if (estadosSalientes.includes(cama.estado)) {
        const paciente = cama.paciente;
        if (paciente && paciente.id) {
          salientes.push({
            ...paciente,
            cama_identificador: cama.identificador,
            servicio_nombre: cama.servicio_nombre,
            tipo_traslado: 'saliente',
            estado_cama: cama.estado
          });
        }
      }
    });

    // PASO 2: Agregar pacientes ENTRANTES de camas (usar Map para evitar duplicados DENTRO de entrantes)
    camas.forEach(cama => {
      // Aplicar filtro de servicio del Dashboard
      if (filtroServicio !== 'todos' && cama.servicio_nombre !== filtroServicio) {
        return;
      }

      if (estadosEntrantes.includes(cama.estado)) {
        const paciente = cama.paciente_entrante || cama.paciente;
        if (paciente && paciente.id && !entrantesMap.has(paciente.id)) {
          entrantesMap.set(paciente.id, {
            ...paciente,
            cama_identificador: cama.identificador,
            servicio_nombre: cama.servicio_nombre,
            tipo_traslado: 'entrante'
          });
        }
      }
    });

    // PASO 3: Agregar pacientes de lista de espera SOLO si no están ya en entrantes
    // También aplicar filtro de servicio si no es "todos"
    listaEspera.forEach(paciente => {
      if (paciente.id && !entrantesMap.has(paciente.id)) {
        // Si hay filtro de servicio, solo agregar si NO aplicamos filtro
        // (la lista de espera no tiene servicio_nombre directamente)
        // Por ahora solo agregamos si el filtro es "todos"
        if (filtroServicio === 'todos') {
          entrantesMap.set(paciente.id, {
            ...paciente,
            tipo_traslado: 'entrante'
          });
        }
      }
    });

    // Combinar salientes y entrantes
    const entrantes = Array.from(entrantesMap.values());
    const todos = [...salientes, ...entrantes];

    // Ordenar por prioridad
    return todos.sort((a, b) => {
      const prioridadA = a.prioridad_calculada || 0;
      const prioridadB = b.prioridad_calculada || 0;
      return prioridadB - prioridadA;
    });
  }, [camas, listaEspera, filtroServicio, dataVersion]);

  // Separar por tipo de traslado
  const pacientesEntrantes = pacientesEnTraslado.filter(p => p.tipo_traslado === 'entrante');
  const pacientesSalientes = pacientesEnTraslado.filter(p => p.tipo_traslado === 'saliente');

  // ============================================
  // HANDLERS
  // ============================================
  const handleClickPaciente = (paciente: PacienteTraslado) => {
    openModal('verPaciente', { paciente });
  };

  // ============================================
  // COMPONENTE DE ITEM DE PACIENTE
  // ============================================
  const PacienteItem = ({ paciente, index }: { paciente: PacienteTraslado; index: number }) => {
    const sexo = paciente.sexo || 'hombre';
    const colorSexo = sexo === 'hombre' ? 'bg-blue-500' : 'bg-pink-500';
    const colorSexoLight = sexo === 'hombre' ? 'bg-blue-50 border-blue-200' : 'bg-pink-50 border-pink-200';

    // Determinar estado del paciente basado en si tiene cama asignada o está fallecido
    let estadoTexto = 'En espera de cama';
    if (paciente.estado_cama === 'fallecido') {
      estadoTexto = 'Fallecido';
    } else if (paciente.cama_identificador) {
      estadoTexto = 'Cama asignada';
    }

    return (
      <button
        onClick={() => handleClickPaciente(paciente)}
        className={`w-full p-3 ${colorSexoLight} border rounded-lg hover:shadow-md transition-all duration-200 text-left group`}
      >
        <div className="flex items-start gap-3">
          {/* Número */}
          <div className="flex-shrink-0 w-6 h-6 flex items-center justify-center bg-white rounded-full text-xs font-bold text-gray-700 border">
            {index + 1}
          </div>

          {/* Logo de persona */}
          <div className={`flex-shrink-0 ${colorSexo} rounded-full p-2 group-hover:scale-110 transition-transform`}>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="w-5 h-5"
            >
              {/* Cabeza */}
              <circle cx="12" cy="8" r="4" />
              {/* Torso */}
              <path d="M6 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2" />
            </svg>
          </div>

          {/* Información */}
          <div className="flex-grow min-w-0">
            <p className="font-semibold text-sm text-gray-800 truncate">
              {paciente.nombre}
            </p>
            <p className="text-xs text-gray-600 mt-0.5">
              {estadoTexto}
            </p>
            <div className="flex flex-wrap gap-1 mt-1">
              <span className="text-xs bg-white px-2 py-0.5 rounded-full">
                {formatComplejidad(paciente.complejidad_requerida || paciente.complejidad || 'ninguna')}
              </span>
              {paciente.cama_identificador && (
                <span className="text-xs bg-white px-2 py-0.5 rounded-full">
                  {paciente.cama_identificador}
                </span>
              )}
              {paciente.servicio_nombre && (
                <span className="text-xs bg-white px-2 py-0.5 rounded-full">
                  {paciente.servicio_nombre}
                </span>
              )}
            </div>
          </div>
        </div>
      </button>
    );
  };

  // ============================================
  // RENDER
  // ============================================
  return (
    <div className="bg-white rounded-lg shadow-lg border border-gray-200 max-h-full flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b bg-gradient-to-r from-blue-50 to-purple-50 flex-shrink-0">
        <h3 className="font-bold text-gray-800 flex items-center gap-2">
          <ArrowUpCircle className="w-5 h-5 text-blue-600" />
          Resumen de Traslados
        </h3>
        <p className="text-xs text-gray-500 mt-1">
          {filtroServicio === 'todos' ? 'Todos los servicios' : `Servicio: ${filtroServicio}`}
        </p>
      </div>

      {/* Contenido */}
      <div className="flex-grow overflow-y-auto">
        {/* Pacientes Entrantes */}
        <div className="p-4 border-b bg-green-50">
          <div className="flex items-center gap-2 mb-3">
            <ArrowDownCircle className="w-4 h-4 text-green-600" />
            <h4 className="font-semibold text-sm text-gray-800">
              Entrantes ({pacientesEntrantes.length})
            </h4>
          </div>
          <div className="space-y-2">
            {pacientesEntrantes.length > 0 ? (
              pacientesEntrantes.map((paciente, index) => (
                <PacienteItem key={paciente.id} paciente={paciente} index={index} />
              ))
            ) : (
              <p className="text-xs text-gray-500 text-center py-4">
                No hay pacientes entrantes
              </p>
            )}
          </div>
        </div>

        {/* Pacientes Salientes */}
        <div className="p-4 bg-orange-50">
          <div className="flex items-center gap-2 mb-3">
            <ArrowUpCircle className="w-4 h-4 text-orange-600" />
            <h4 className="font-semibold text-sm text-gray-800">
              Salientes ({pacientesSalientes.length})
            </h4>
          </div>
          <div className="space-y-2">
            {pacientesSalientes.length > 0 ? (
              pacientesSalientes.map((paciente, index) => (
                <PacienteItem key={paciente.id} paciente={paciente} index={index} />
              ))
            ) : (
              <p className="text-xs text-gray-500 text-center py-4">
                No hay pacientes salientes
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
