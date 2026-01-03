import React, { useState, useMemo, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { CamaCard } from '../components/cama';
import { Spinner } from '../components/common';
import { Volume2, VolumeX } from 'lucide-react';

export function Dashboard() {
  const { 
    hospitales, 
    hospitalSeleccionado, 
    camas,
    listaEspera,
    derivados,
    configuracion,
    loading,
    wsConnected,
    dataVersion,
    setHospitalSeleccionado,
    recargarTodo,
    showAlert,
    // TTS
    servicioSeleccionadoId,
    setServicioSeleccionadoId,
    ttsHabilitado,
    setTtsHabilitado,
    ttsDisponible,
    testTts
  } = useApp();

  const [filtroServicio, setFiltroServicio] = useState<string>('todos');

  // ============================================
  // SINCRONIZAR FILTRO CON TTS
  // ============================================
  useEffect(() => {
    // Cuando cambia el filtro de servicio, actualizar el contexto TTS
    // - "todos" o vacío = vista global (no reproducir TTS)
    // - un nombre de servicio = vista específica (reproducir TTS)
    
    if (!filtroServicio || filtroServicio === 'todos' || filtroServicio === '') {
      setServicioSeleccionadoId(null);
    } else {
      // Usamos el nombre del servicio como identificador
      setServicioSeleccionadoId(filtroServicio);
    }
  }, [filtroServicio, setServicioSeleccionadoId]);

  // ============================================
  // COMPONENTE INDICADOR TTS
  // ============================================
  const TTSIndicator = () => {
    const enVistaGlobal = !servicioSeleccionadoId;
    
    return (
      <div className="flex items-center gap-2">
        {/* Botón de activar/desactivar */}
        <button
          onClick={() => setTtsHabilitado(!ttsHabilitado)}
          className={`
            flex items-center gap-1.5 px-2 py-1 rounded-md text-sm
            transition-colors duration-200
            ${ttsHabilitado 
              ? 'bg-green-100 text-green-700 hover:bg-green-200' 
              : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
            }
          `}
          title={ttsHabilitado ? 'Desactivar notificaciones de voz' : 'Activar notificaciones de voz'}
        >
          {ttsHabilitado ? (
            <Volume2 className="w-4 h-4" />
          ) : (
            <VolumeX className="w-4 h-4" />
          )}
          <span className="hidden sm:inline">
            {ttsHabilitado ? 'Voz activa' : 'Voz inactiva'}
          </span>
        </button>
        
        {/* Indicador de vista global */}
        {enVistaGlobal && ttsHabilitado && (
          <span className="text-xs text-amber-600">
            (seleccione servicio)
          </span>
        )}
        
        {/* Botón de prueba - solo visible si está habilitado y hay servicio */}
        {ttsHabilitado && ttsDisponible && !enVistaGlobal && (
          <button
            onClick={testTts}
            className="p-1 rounded text-gray-500 hover:text-gray-700 hover:bg-gray-100"
            title="Probar notificación de voz"
          >
            🔊
          </button>
        )}
      </div>
    );
  };

  // Obtener servicios únicos
  const servicios = useMemo(() => {
    const serviciosSet = new Set<string>();
    camas.forEach(cama => {
      if (cama.servicio_nombre) {
        serviciosSet.add(cama.servicio_nombre);
      }
    });
    return Array.from(serviciosSet).sort();
  }, [camas, dataVersion]);

  // Filtrar camas
  const camasFiltradas = useMemo(() => {
    if (filtroServicio === 'todos') return camas;
    return camas.filter(cama => cama.servicio_nombre === filtroServicio);
  }, [camas, filtroServicio, dataVersion]);

  // Agrupar por servicio Y LUEGO por sala
  const camasPorServicioYSala = useMemo(() => {
    const grupos: Record<string, Record<string, typeof camas>> = {};
    
    camasFiltradas.forEach(cama => {
      const servicio = cama.servicio_nombre || 'Sin Servicio';
      const sala = cama.sala_nombre || 'Sin Sala';
      
      if (!grupos[servicio]) {
        grupos[servicio] = {};
      }
      if (!grupos[servicio][sala]) {
        grupos[servicio][sala] = [];
      }
      grupos[servicio][sala].push(cama);
    });
    
    return grupos;
  }, [camasFiltradas, dataVersion]);

  // Estadísticas rápidas
  const stats = useMemo(() => {
    const total = camas.length;
    const libres = camas.filter(c => c.estado === 'libre').length;
    const ocupadas = camas.filter(c => c.estado === 'ocupada').length;
    const traslado = camas.filter(c => 
      c.estado === 'traslado_entrante' || 
      c.estado === 'traslado_saliente' ||
      c.estado === 'traslado_confirmado'
    ).length;
    const bloqueadas = camas.filter(c => c.estado === 'bloqueada').length;
    
    return { total, libres, ocupadas, traslado, bloqueadas };
  }, [camas, dataVersion]);

  // Función para determinar si una sala es individual
  const esSalaIndividualCheck = (servicio: string, camasSala: typeof camas): boolean => {
    return camasSala.length === 1 || 
      camasSala[0]?.sala_es_individual || 
      servicio.toLowerCase().includes('uci') ||
      servicio.toLowerCase().includes('uti') ||
      servicio.toLowerCase().includes('aislamiento');
  };

  // Función para agrupar salas individuales en grupos de 3
  const agruparSalasIndividuales = (
    salasCamas: Record<string, typeof camas>,
    servicio: string
  ): { individualesAgrupadas: Array<Array<[string, typeof camas]>>; compartidas: Array<[string, typeof camas]> } => {
    const individuales: Array<[string, typeof camas]> = [];
    const compartidas: Array<[string, typeof camas]> = [];

    Object.entries(salasCamas).forEach(([sala, camasSala]) => {
      if (esSalaIndividualCheck(servicio, camasSala)) {
        individuales.push([sala, camasSala]);
      } else {
        compartidas.push([sala, camasSala]);
      }
    });

    // Agrupar salas individuales en grupos de hasta 3
    const individualesAgrupadas: Array<Array<[string, typeof camas]>> = [];
    for (let i = 0; i < individuales.length; i += 3) {
      individualesAgrupadas.push(individuales.slice(i, i + 3));
    }

    return { individualesAgrupadas, compartidas };
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Stats y filtros */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center justify-between flex-wrap gap-4">
          {/* Estadísticas */}
          <div className="flex gap-6">
            <div className="text-center">
              <p className="text-2xl font-bold text-gray-800">{stats.total}</p>
              <p className="text-xs text-gray-500">Total</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-green-600">{stats.libres}</p>
              <p className="text-xs text-gray-500">Libres</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-blue-600">{stats.ocupadas}</p>
              <p className="text-xs text-gray-500">Ocupadas</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-yellow-600">{stats.traslado}</p>
              <p className="text-xs text-gray-500">En Traslado</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-red-600">{stats.bloqueadas}</p>
              <p className="text-xs text-gray-500">Bloqueadas</p>
            </div>
          </div>

          {/* Indicadores y controles */}
          <div className="flex items-center gap-4 flex-wrap">
            {/* Indicador TTS */}
            <TTSIndicator />
            
            {/* Indicador de WebSocket */}
            <div className="flex items-center gap-1.5">
              <div 
                className={`w-2 h-2 rounded-full ${
                  wsConnected ? 'bg-green-500' : 'bg-red-500'
                }`}
              />
              <span className="text-xs text-gray-500">
                {wsConnected ? 'Conectado' : 'Desconectado'}
              </span>
            </div>

            {/* Filtro de servicio */}
            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-600">Servicio:</label>
              <select
                value={filtroServicio}
                onChange={(e) => setFiltroServicio(e.target.value)}
                className="border rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500"
              >
                <option value="todos">Todos los servicios</option>
                {servicios.map(servicio => (
                  <option key={servicio} value={servicio}>{servicio}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Grid de camas agrupadas por SERVICIO y luego por SALA */}
      {Object.entries(camasPorServicioYSala).map(([servicio, salasCamas]) => {
        const { individualesAgrupadas, compartidas } = agruparSalasIndividuales(salasCamas, servicio);
        
        return (
          <div key={`servicio-${servicio}-${dataVersion}`} className="bg-white rounded-lg shadow">
            {/* Header del Servicio */}
            <div className="px-4 py-3 border-b bg-gray-100 rounded-t-lg">
              <h2 className="font-bold text-gray-800 text-lg">
                {servicio}
                <span className="ml-2 text-sm font-normal text-gray-500">
                  ({Object.values(salasCamas).flat().length} camas)
                </span>
              </h2>
            </div>
            
            <div className="divide-y divide-gray-100">
              {/* Renderizar salas individuales en grupos horizontales de hasta 3 */}
              {individualesAgrupadas.map((grupoSalas, grupoIndex) => (
                <div key={`grupo-individual-${grupoIndex}-${dataVersion}`} className="p-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {grupoSalas.map(([sala, camasSala]) => {
                      const sexoSala = camasSala[0]?.sala_sexo_asignado;
                      
                      return (
                        <div 
                          key={`sala-${sala}-${dataVersion}`} 
                          className="border rounded-lg p-3 bg-gray-50"
                        >
                          {/* Header de la Sala Individual */}
                          <div className="flex items-center gap-2 mb-2 flex-wrap">
                            <h3 className="font-semibold text-gray-700 text-sm">
                              {sala}
                            </h3>
                            <span className="px-2 py-0.5 text-xs bg-purple-100 text-purple-700 rounded-full">
                              Individual
                            </span>
                            {sexoSala && (
                              <span className={`px-2 py-0.5 text-xs rounded-full ${
                                sexoSala === 'hombre' 
                                  ? 'bg-cyan-100 text-cyan-700' 
                                  : 'bg-pink-100 text-pink-700'
                              }`}>
                                {sexoSala === 'hombre' ? '♂' : '♀'}
                              </span>
                            )}
                          </div>
                          
                          {/* Camas de la sala individual */}
                          <div className="space-y-2">
                            {camasSala.map(cama => (
                              <CamaCard key={`${cama.id}-${dataVersion}`} cama={cama} />
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
              
              {/* Renderizar salas compartidas normalmente */}
              {compartidas.map(([sala, camasSala]) => {
                const sexoSala = camasSala[0]?.sala_sexo_asignado;
                
                return (
                  <div key={`sala-${sala}-${dataVersion}`} className="p-4">
                    {/* Header de la Sala */}
                    <div className="flex items-center gap-2 mb-3">
                      <h3 className="font-semibold text-gray-700">
                        {sala}
                      </h3>
                      <span className="text-sm text-gray-500">
                        ({camasSala.length} camas)
                      </span>
                      
                      <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">
                        Compartida
                      </span>
                      
                      {/* Badge de sexo asignado (solo para salas compartidas) */}
                      {sexoSala && (
                        <span className={`px-2 py-0.5 text-xs rounded-full ${
                          sexoSala === 'hombre' 
                            ? 'bg-cyan-100 text-cyan-700' 
                            : 'bg-pink-100 text-pink-700'
                        }`}>
                          {sexoSala === 'hombre' ? '♂ Hombres' : '♀ Mujeres'}
                        </span>
                      )}
                      
                      {/* Badge sala disponible para ambos sexos */}
                      {!sexoSala && (
                        <span className="px-2 py-0.5 text-xs bg-green-100 text-green-700 rounded-full">
                          Disponible ♂♀
                        </span>
                      )}
                    </div>
                    
                    {/* Grid de camas de la sala */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
                      {camasSala.map(cama => (
                        <CamaCard key={`${cama.id}-${dataVersion}`} cama={cama} />
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}

      {camasFiltradas.length === 0 && (
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
          No hay camas para mostrar
        </div>
      )}
    </div>
  );
}