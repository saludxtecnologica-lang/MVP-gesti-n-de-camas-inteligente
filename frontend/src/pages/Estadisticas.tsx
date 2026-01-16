import React, { useState, useEffect } from 'react';
import {
  BarChart3, Building2, BedDouble, Users, RefreshCw, Download,
  Clock, TrendingUp, AlertCircle, Activity, ArrowUpDown, Layers
} from 'lucide-react';
import { Spinner } from '../components/common';
import { useApp } from '../context/AppContext';
import type {
  EstadisticasGlobales,
  EstadisticasCompletas,
  TiempoEstadistica,
  Servicio
} from '../types';
import * as api from '../services/api';

type TabType = 'hospital' | 'servicio' | 'red';

export function Estadisticas() {
  const { hospitalSeleccionado, hospitales } = useApp();

  const [tab, setTab] = useState<TabType>('hospital');
  const [estadisticas, setEstadisticas] = useState<EstadisticasGlobales | null>(null);
  const [estadisticasAvanzadas, setEstadisticasAvanzadas] = useState<EstadisticasCompletas | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [diasPeriodo, setDiasPeriodo] = useState(7);
  const [downloading, setDownloading] = useState(false);

  // Estado para servicios
  const [servicios, setServicios] = useState<Servicio[]>([]);
  const [servicioSeleccionado, setServicioSeleccionado] = useState<string | null>(null);
  const [loadingServicios, setLoadingServicios] = useState(false);

  // Estado para comparaciones
  const [modoComparacion, setModoComparacion] = useState(false);
  const [serviciosComparar, setServiciosComparar] = useState<string[]>([]);
  const [hospitalesComparar, setHospitalesComparar] = useState<string[]>([]);

  // Estado para estadísticas específicas de hospital
  const [ingresosHospital, setIngresosHospital] = useState<number | null>(null);
  const [egresosHospital, setEgresosHospital] = useState<number | null>(null);
  const [loadingHospitalStats, setLoadingHospitalStats] = useState(false);

  // Estado para estadísticas específicas de servicio
  const [ingresosServicio, setIngresosServicio] = useState<number | null>(null);
  const [egresosServicio, setEgresosServicio] = useState<number | null>(null);
  const [ocupacionServicio, setOcupacionServicio] = useState<{ tasa: number; camas_totales: number; camas_ocupadas: number } | null>(null);
  const [loadingServicioStats, setLoadingServicioStats] = useState(false);

  // Estado para tiempos de hospitalización desglosados
  const [tiempoHospTotal, setTiempoHospTotal] = useState<TiempoEstadistica | null>(null);
  const [tiempoHospCasosEspeciales, setTiempoHospCasosEspeciales] = useState<TiempoEstadistica | null>(null);
  const [tiempoHospSinCasosEspeciales, setTiempoHospSinCasosEspeciales] = useState<TiempoEstadistica | null>(null);
  const [loadingTiemposHosp, setLoadingTiemposHosp] = useState(false);

  const cargarEstadisticas = async () => {
    try {
      setLoading(true);
      setError(null);

      const [basicas, avanzadas] = await Promise.all([
        api.getEstadisticas(),
        api.getEstadisticasCompletas(diasPeriodo)
      ]);

      setEstadisticas(basicas);
      setEstadisticasAvanzadas(avanzadas);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar estadísticas');
    } finally {
      setLoading(false);
    }
  };

  const cargarServicios = async () => {
    if (!hospitalSeleccionado) return;

    try {
      setLoadingServicios(true);
      // Usar endpoint existente o crear uno nuevo
      const response = await fetch(`${api.getApiBase()}/api/servicios/hospital/${hospitalSeleccionado.id}`);
      if (response.ok) {
        const data = await response.json();
        setServicios(data);
        if (data.length > 0 && !servicioSeleccionado) {
          setServicioSeleccionado(data[0].id);
        }
      }
    } catch (err) {
      console.error('Error al cargar servicios:', err);
    } finally {
      setLoadingServicios(false);
    }
  };

  const cargarEstadisticasHospital = async () => {
    if (!hospitalSeleccionado) {
      setIngresosHospital(null);
      setEgresosHospital(null);
      return;
    }

    try {
      setLoadingHospitalStats(true);
      const [ingresos, egresos] = await Promise.all([
        api.getIngresosHospital(hospitalSeleccionado.id, diasPeriodo),
        api.getEgresosHospital(hospitalSeleccionado.id, diasPeriodo)
      ]);
      setIngresosHospital(ingresos.total);
      setEgresosHospital(egresos.total);
    } catch (err) {
      console.error('Error al cargar estadísticas del hospital:', err);
      setIngresosHospital(null);
      setEgresosHospital(null);
    } finally {
      setLoadingHospitalStats(false);
    }
  };

  const cargarEstadisticasServicio = async () => {
    if (!servicioSeleccionado) {
      setIngresosServicio(null);
      setEgresosServicio(null);
      setOcupacionServicio(null);
      return;
    }

    try {
      setLoadingServicioStats(true);
      const [ingresos, egresos, ocupacion] = await Promise.all([
        api.getIngresosServicio(servicioSeleccionado, diasPeriodo),
        api.getEgresosServicio(servicioSeleccionado, diasPeriodo),
        api.getOcupacionServicio(servicioSeleccionado)
      ]);
      setIngresosServicio(ingresos.total);
      setEgresosServicio(egresos.total);
      setOcupacionServicio(ocupacion);
    } catch (err) {
      console.error('Error al cargar estadísticas del servicio:', err);
      setIngresosServicio(null);
      setEgresosServicio(null);
      setOcupacionServicio(null);
    } finally {
      setLoadingServicioStats(false);
    }
  };

  const cargarTiemposHospitalizacion = async () => {
    try {
      setLoadingTiemposHosp(true);
      const [total, conCasosEspeciales, sinCasosEspeciales] = await Promise.all([
        api.getTiempoHospitalizacion(null, null, diasPeriodo),
        api.getTiempoHospitalizacion(null, true, diasPeriodo),
        api.getTiempoHospitalizacion(null, false, diasPeriodo)
      ]);
      setTiempoHospTotal(total);
      setTiempoHospCasosEspeciales(conCasosEspeciales);
      setTiempoHospSinCasosEspeciales(sinCasosEspeciales);
    } catch (err) {
      console.error('Error al cargar tiempos de hospitalización:', err);
      setTiempoHospTotal(null);
      setTiempoHospCasosEspeciales(null);
      setTiempoHospSinCasosEspeciales(null);
    } finally {
      setLoadingTiemposHosp(false);
    }
  };

  useEffect(() => {
    cargarEstadisticas();
    cargarTiemposHospitalizacion();
  }, [diasPeriodo]);

  useEffect(() => {
    if (hospitalSeleccionado) {
      cargarServicios();
      cargarEstadisticasHospital();
    }
  }, [hospitalSeleccionado, diasPeriodo]);

  useEffect(() => {
    if (servicioSeleccionado) {
      cargarEstadisticasServicio();
    }
  }, [servicioSeleccionado, diasPeriodo]);

  const handleDownload = async (formato: 'json' | 'csv') => {
    try {
      setDownloading(true);
      const blob = await api.downloadEstadisticas(diasPeriodo, formato);

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `estadisticas-${new Date().toISOString().split('T')[0]}.${formato}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al descargar estadísticas');
    } finally {
      setDownloading(false);
    }
  };

  const formatearTiempo = (minutos: number): string => {
    if (minutos < 60) {
      return `${Math.round(minutos)} min`;
    } else if (minutos < 1440) {
      const horas = Math.floor(minutos / 60);
      const mins = Math.round(minutos % 60);
      return mins > 0 ? `${horas}h ${mins}m` : `${horas}h`;
    } else {
      const dias = Math.floor(minutos / 1440);
      const horas = Math.floor((minutos % 1440) / 60);
      return horas > 0 ? `${dias}d ${horas}h` : `${dias}d`;
    }
  };

  const renderTiempoCard = (titulo: string, tiempo: TiempoEstadistica | undefined, icon: React.ReactNode) => {
    if (!tiempo || tiempo.cantidad === 0) return null;

    return (
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center gap-2 mb-3">
          {icon}
          <h4 className="font-semibold text-gray-700 text-sm">{titulo}</h4>
        </div>
        <div className="grid grid-cols-3 gap-3 text-center">
          <div>
            <p className="text-xs text-gray-500 mb-1">Promedio</p>
            <p className="text-base font-bold text-blue-600">{formatearTiempo(tiempo.promedio)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">Mínimo</p>
            <p className="text-sm font-semibold text-green-600">{formatearTiempo(tiempo.minimo)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">Máximo</p>
            <p className="text-sm font-semibold text-red-600">{formatearTiempo(tiempo.maximo)}</p>
          </div>
        </div>
        <div className="mt-2 pt-2 border-t">
          <p className="text-xs text-gray-500 text-center">
            {tiempo.cantidad} registro{tiempo.cantidad !== 1 ? 's' : ''}
          </p>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center">
        <p className="text-red-600 mb-4">{error}</p>
        <button
          onClick={cargarEstadisticas}
          className="flex items-center gap-2 mx-auto px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <RefreshCw className="w-4 h-4" />
          Reintentar
        </button>
      </div>
    );
  }

  if (!estadisticas) return null;

  return (
    <div className="space-y-6">
      {/* Controles superiores */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-4">
            <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-blue-600" />
              Estadísticas del Sistema
            </h2>

            <select
              value={diasPeriodo}
              onChange={(e) => setDiasPeriodo(Number(e.target.value))}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={1}>Últimas 24 horas</option>
              <option value={7}>Últimos 7 días</option>
              <option value={30}>Últimos 30 días</option>
              <option value={90}>Últimos 90 días</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => handleDownload('csv')}
              disabled={downloading}
              className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg disabled:opacity-50"
            >
              <Download className="w-4 h-4" />
              CSV
            </button>
            <button
              onClick={() => handleDownload('json')}
              disabled={downloading}
              className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg disabled:opacity-50"
            >
              <Download className="w-4 h-4" />
              JSON
            </button>
            <button
              onClick={cargarEstadisticas}
              className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              <RefreshCw className="w-4 h-4" />
              Actualizar
            </button>
          </div>
        </div>
      </div>

      {/* Tabs de navegación */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            <button
              onClick={() => setTab('hospital')}
              className={`flex items-center gap-2 px-6 py-3 border-b-2 font-medium text-sm transition-colors ${
                tab === 'hospital'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <Building2 className="w-4 h-4" />
              Por Hospital
              {hospitalSeleccionado && (
                <span className="ml-1 text-xs text-gray-500">({hospitalSeleccionado.nombre})</span>
              )}
            </button>
            <button
              onClick={() => setTab('servicio')}
              className={`flex items-center gap-2 px-6 py-3 border-b-2 font-medium text-sm transition-colors ${
                tab === 'servicio'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
              disabled={!hospitalSeleccionado}
            >
              <Layers className="w-4 h-4" />
              Por Servicio
            </button>
            <button
              onClick={() => setTab('red')}
              className={`flex items-center gap-2 px-6 py-3 border-b-2 font-medium text-sm transition-colors ${
                tab === 'red'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <Users className="w-4 h-4" />
              Red de Hospitales
            </button>
          </nav>
        </div>

        <div className="p-6">
          {/* SECCIÓN: POR HOSPITAL */}
          {tab === 'hospital' && (
            <div className="space-y-6">
              {!hospitalSeleccionado ? (
                <div className="text-center py-8 text-gray-500">
                  <Building2 className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>Selecciona un hospital en la barra superior para ver sus estadísticas</p>
                </div>
              ) : (
                <>
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">
                    Estadísticas de {hospitalSeleccionado.nombre}
                  </h3>

                  {/* Información Global del Hospital */}
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-6">
                    <h4 className="text-md font-semibold text-gray-800 mb-4">Información Global</h4>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="bg-white rounded-lg p-4 text-center shadow-sm">
                        <TrendingUp className="w-6 h-6 mx-auto mb-2 text-green-600" />
                        <p className="text-2xl font-bold text-gray-800">
                          {loadingHospitalStats ? (
                            <span className="text-sm text-gray-400">Cargando...</span>
                          ) : ingresosHospital !== null ? (
                            ingresosHospital
                          ) : (
                            '--'
                          )}
                        </p>
                        <p className="text-sm text-gray-600">Ingresos ({diasPeriodo === 1 ? 'hoy' : `${diasPeriodo} días`})</p>
                      </div>
                      <div className="bg-white rounded-lg p-4 text-center shadow-sm">
                        <ArrowUpDown className="w-6 h-6 mx-auto mb-2 text-blue-600" />
                        <p className="text-2xl font-bold text-gray-800">
                          {loadingHospitalStats ? (
                            <span className="text-sm text-gray-400">Cargando...</span>
                          ) : egresosHospital !== null ? (
                            egresosHospital
                          ) : (
                            '--'
                          )}
                        </p>
                        <p className="text-sm text-gray-600">Egresos ({diasPeriodo === 1 ? 'hoy' : `${diasPeriodo} días`})</p>
                      </div>
                      <div className="bg-white rounded-lg p-4 text-center shadow-sm">
                        <BarChart3 className="w-6 h-6 mx-auto mb-2 text-purple-600" />
                        <p className="text-2xl font-bold text-gray-800">
                          {estadisticas.hospitales.find(h => h.hospital_id === hospitalSeleccionado.id)?.ocupacion_porcentaje?.toFixed(1) || '0'}%
                        </p>
                        <p className="text-sm text-gray-600">Ocupación Actual</p>
                      </div>
                    </div>
                  </div>

                  {/* Servicios con Mayor y Menor Demanda */}
                  <div className="bg-white rounded-lg shadow p-6">
                    <h4 className="text-md font-semibold text-gray-800 mb-4">Demanda por Servicio</h4>
                    <p className="text-sm text-gray-500">En desarrollo...</p>
                  </div>

                  {/* Tiempos de Espera y Procesos */}
                  <div className="bg-white rounded-lg shadow p-6">
                    <h4 className="text-md font-semibold text-gray-800 mb-4 flex items-center gap-2">
                      <Clock className="w-5 h-5 text-orange-600" />
                      Tiempos de Espera y Procesos Hospitalarios
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {renderTiempoCard('Espera de Cama', estadisticasAvanzadas?.tiempo_espera_cama, <Clock className="w-4 h-4 text-orange-600" />)}
                      {renderTiempoCard('Respuesta Derivación', estadisticasAvanzadas?.tiempo_derivacion_pendiente, <Clock className="w-4 h-4 text-yellow-600" />)}
                      {renderTiempoCard('Paciente en Traslado', estadisticasAvanzadas?.tiempo_traslado_saliente, <ArrowUpDown className="w-4 h-4 text-blue-600" />)}
                      {renderTiempoCard('Confirmación Traslado', estadisticasAvanzadas?.tiempo_confirmacion_traslado, <Clock className="w-4 h-4 text-purple-600" />)}
                      {estadisticasAvanzadas?.tiempo_alta && renderTiempoCard('Alta Sugerida', estadisticasAvanzadas.tiempo_alta.alta_sugerida, <Clock className="w-4 h-4 text-green-600" />)}
                      {estadisticasAvanzadas?.tiempo_alta && renderTiempoCard('Alta Completada', estadisticasAvanzadas.tiempo_alta.alta_completada, <Clock className="w-4 h-4 text-teal-600" />)}
                      {renderTiempoCard('Egreso Fallecido', estadisticasAvanzadas?.tiempo_fallecido, <Clock className="w-4 h-4 text-gray-600" />)}
                      {renderTiempoCard('Hospitalización Total', estadisticasAvanzadas?.tiempo_hospitalizacion_hospital, <Activity className="w-4 h-4 text-indigo-600" />)}
                    </div>
                  </div>

                  {/* Casos Especiales */}
                  {estadisticasAvanzadas?.casos_especiales && estadisticasAvanzadas.casos_especiales.total > 0 && (
                    <div className="bg-white rounded-lg shadow p-6">
                      <h4 className="text-md font-semibold text-gray-800 mb-4 flex items-center gap-2">
                        <AlertCircle className="w-5 h-5 text-yellow-600" />
                        Casos Especiales
                      </h4>
                      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                        <div className="bg-yellow-50 rounded-lg p-4 text-center">
                          <p className="text-2xl font-bold text-yellow-700">
                            {estadisticasAvanzadas.casos_especiales.total}
                          </p>
                          <p className="text-xs text-gray-600 mt-1">Total</p>
                        </div>
                        <div className="bg-red-50 rounded-lg p-4 text-center">
                          <p className="text-2xl font-bold text-red-700">
                            {estadisticasAvanzadas.casos_especiales.cardiocirugia}
                          </p>
                          <p className="text-xs text-gray-600 mt-1">Cardiocirugía</p>
                        </div>
                        <div className="bg-orange-50 rounded-lg p-4 text-center">
                          <p className="text-2xl font-bold text-orange-700">
                            {estadisticasAvanzadas.casos_especiales.caso_social}
                          </p>
                          <p className="text-xs text-gray-600 mt-1">Casos Sociales</p>
                        </div>
                        <div className="bg-purple-50 rounded-lg p-4 text-center">
                          <p className="text-2xl font-bold text-purple-700">
                            {estadisticasAvanzadas.casos_especiales.caso_socio_judicial}
                          </p>
                          <p className="text-xs text-gray-600 mt-1">Socio-Judiciales</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Flujos más repetidos */}
                  {estadisticasAvanzadas?.flujos_mas_repetidos && estadisticasAvanzadas.flujos_mas_repetidos.length > 0 && (
                    <div className="bg-white rounded-lg shadow p-6">
                      <h4 className="text-md font-semibold text-gray-800 mb-4 flex items-center gap-2">
                        <ArrowUpDown className="w-5 h-5 text-blue-600" />
                        Flujos Más Repetidos (Origen → Destino)
                      </h4>
                      <div className="space-y-2">
                        {estadisticasAvanzadas.flujos_mas_repetidos.map((flujo, idx) => (
                          <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100">
                            <span className="text-sm text-gray-700">{flujo.flujo}</span>
                            <span className="font-semibold text-blue-600">{flujo.cantidad} veces</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Camas Subutilizadas */}
                  {estadisticasAvanzadas?.camas_subutilizadas && estadisticasAvanzadas.camas_subutilizadas.length > 0 && (
                    <div className="bg-white rounded-lg shadow p-6">
                      <h4 className="text-md font-semibold text-gray-800 mb-4 flex items-center gap-2">
                        <BedDouble className="w-5 h-5 text-gray-600" />
                        Camas Subutilizadas
                      </h4>
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                          <thead className="bg-gray-50">
                            <tr>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cama</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Servicio</th>
                              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Tiempo Libre</th>
                            </tr>
                          </thead>
                          <tbody className="bg-white divide-y divide-gray-200">
                            {estadisticasAvanzadas.camas_subutilizadas
                              .filter(cama => {
                                // Filtrar solo camas del hospital seleccionado (si es necesario)
                                return true;
                              })
                              .map((cama) => (
                              <tr key={cama.cama_id} className="hover:bg-gray-50">
                                <td className="px-4 py-3 text-sm text-gray-900">{cama.identificador}</td>
                                <td className="px-4 py-3 text-sm text-gray-600">{cama.servicio_nombre}</td>
                                <td className="px-4 py-3 text-center text-sm font-semibold text-green-600">
                                  {cama.tiempo_libre_horas.toFixed(1)} hrs
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* SECCIÓN: POR SERVICIO */}
          {tab === 'servicio' && (
            <div className="space-y-6">
              {!hospitalSeleccionado ? (
                <div className="text-center py-8 text-gray-500">
                  <Layers className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>Selecciona un hospital en la barra superior</p>
                </div>
              ) : (
                <>
                  {/* Selector de Servicio */}
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex-1">
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Seleccionar Servicio
                      </label>
                      <select
                        value={servicioSeleccionado || ''}
                        onChange={(e) => setServicioSeleccionado(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        disabled={loadingServicios || servicios.length === 0}
                      >
                        {loadingServicios ? (
                          <option>Cargando servicios...</option>
                        ) : servicios.length === 0 ? (
                          <option>No hay servicios disponibles</option>
                        ) : (
                          servicios.map(servicio => (
                            <option key={servicio.id} value={servicio.id}>
                              {servicio.nombre} ({servicio.tipo})
                            </option>
                          ))
                        )}
                      </select>
                    </div>

                    <div className="pt-6">
                      <button
                        onClick={() => setModoComparacion(!modoComparacion)}
                        className={`px-4 py-2 text-sm rounded-lg border transition-colors ${
                          modoComparacion
                            ? 'bg-blue-600 text-white border-blue-600'
                            : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                        }`}
                      >
                        {modoComparacion ? 'Salir de Comparación' : 'Comparar Servicios'}
                      </button>
                    </div>
                  </div>

                  {servicioSeleccionado && !modoComparacion ? (
                    <div className="space-y-6">
                      <h3 className="text-lg font-semibold text-gray-800">
                        Estadísticas del Servicio: {servicios.find(s => s.id === servicioSeleccionado)?.nombre}
                      </h3>

                      {/* Información Global del Servicio */}
                      <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-6">
                        <h4 className="text-md font-semibold text-gray-800 mb-4">Información Global del Servicio</h4>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          <div className="bg-white rounded-lg p-4 text-center shadow-sm">
                            <TrendingUp className="w-6 h-6 mx-auto mb-2 text-green-600" />
                            <p className="text-2xl font-bold text-gray-800">
                              {loadingServicioStats ? (
                                <span className="text-sm text-gray-400">Cargando...</span>
                              ) : ingresosServicio !== null ? (
                                ingresosServicio
                              ) : (
                                '--'
                              )}
                            </p>
                            <p className="text-sm text-gray-600">Ingresos ({diasPeriodo === 1 ? 'hoy' : `${diasPeriodo} días`})</p>
                          </div>
                          <div className="bg-white rounded-lg p-4 text-center shadow-sm">
                            <ArrowUpDown className="w-6 h-6 mx-auto mb-2 text-blue-600" />
                            <p className="text-2xl font-bold text-gray-800">
                              {loadingServicioStats ? (
                                <span className="text-sm text-gray-400">Cargando...</span>
                              ) : egresosServicio !== null ? (
                                egresosServicio
                              ) : (
                                '--'
                              )}
                            </p>
                            <p className="text-sm text-gray-600">Egresos ({diasPeriodo === 1 ? 'hoy' : `${diasPeriodo} días`})</p>
                          </div>
                          <div className="bg-white rounded-lg p-4 text-center shadow-sm">
                            <BarChart3 className="w-6 h-6 mx-auto mb-2 text-purple-600" />
                            <p className="text-2xl font-bold text-gray-800">
                              {loadingServicioStats ? (
                                <span className="text-sm text-gray-400">Cargando...</span>
                              ) : ocupacionServicio !== null ? (
                                `${ocupacionServicio.tasa.toFixed(1)}%`
                              ) : (
                                '--'
                              )}
                            </p>
                            <p className="text-sm text-gray-600">
                              Ocupación ({ocupacionServicio ? `${ocupacionServicio.camas_ocupadas}/${ocupacionServicio.camas_totales}` : ''})
                            </p>
                          </div>
                        </div>
                      </div>

                      {/* Tiempos de Espera y Procesos del Servicio */}
                      <div className="bg-white rounded-lg shadow p-6">
                        <h4 className="text-md font-semibold text-gray-800 mb-4 flex items-center gap-2">
                          <Clock className="w-5 h-5 text-orange-600" />
                          Tiempos de Espera y Procesos
                        </h4>
                        <p className="text-sm text-gray-500">
                          Los tiempos mostrados son a nivel de red. Filtrado por servicio en desarrollo...
                        </p>
                      </div>
                    </div>
                  ) : modoComparacion ? (
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 text-center">
                      <p className="text-gray-700">Modo de comparación entre servicios en desarrollo...</p>
                      <p className="text-sm text-gray-500 mt-2">
                        Selecciona múltiples servicios para comparar sus métricas
                      </p>
                    </div>
                  ) : (
                    <div className="text-center py-8 text-gray-500">
                      <p>Selecciona un servicio para ver sus estadísticas</p>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* SECCIÓN: RED DE HOSPITALES */}
          {tab === 'red' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-800">Estadísticas de la Red</h3>
                <button
                  onClick={() => setModoComparacion(!modoComparacion)}
                  className={`px-4 py-2 text-sm rounded-lg border transition-colors ${
                    modoComparacion
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  {modoComparacion ? 'Salir de Comparación' : 'Comparar Hospitales'}
                </button>
              </div>

              {/* Información Global de Red */}
              <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-6">
                <h4 className="text-md font-semibold text-gray-800 mb-4">Información Global de Red</h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-white rounded-lg p-4 text-center shadow-sm">
                    <BedDouble className="w-6 h-6 mx-auto mb-2 text-blue-600" />
                    <p className="text-2xl font-bold text-gray-800">
                      {estadisticas.total_camas_sistema}
                    </p>
                    <p className="text-sm text-gray-600">Camas Totales</p>
                  </div>
                  <div className="bg-white rounded-lg p-4 text-center shadow-sm">
                    <Users className="w-6 h-6 mx-auto mb-2 text-green-600" />
                    <p className="text-2xl font-bold text-gray-800">
                      {estadisticasAvanzadas?.ingresos_red?.total || 0}
                    </p>
                    <p className="text-sm text-gray-600">Ingresos de Red</p>
                  </div>
                  <div className="bg-white rounded-lg p-4 text-center shadow-sm">
                    <BarChart3 className="w-6 h-6 mx-auto mb-2 text-purple-600" />
                    <p className="text-2xl font-bold text-gray-800">
                      {estadisticas.ocupacion_promedio.toFixed(1)}%
                    </p>
                    <p className="text-sm text-gray-600">Ocupación Promedio</p>
                  </div>
                </div>
              </div>

              {/* Tiempos de Hospitalización en Red */}
              <div className="bg-white rounded-lg shadow p-6">
                <h4 className="text-md font-semibold text-gray-800 mb-4 flex items-center gap-2">
                  <Activity className="w-5 h-5 text-indigo-600" />
                  Tiempos de Hospitalización en Red
                </h4>
                {loadingTiemposHosp ? (
                  <div className="text-center py-8">
                    <p className="text-sm text-gray-500">Cargando tiempos de hospitalización...</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {renderTiempoCard('Total (Todos los Pacientes)', tiempoHospTotal, <Activity className="w-4 h-4 text-indigo-600" />)}
                    {renderTiempoCard('Solo Casos Especiales', tiempoHospCasosEspeciales, <AlertCircle className="w-4 h-4 text-yellow-600" />)}
                    {renderTiempoCard('Sin Casos Especiales', tiempoHospSinCasosEspeciales, <Activity className="w-4 h-4 text-green-600" />)}
                  </div>
                )}
              </div>

              {/* Estadísticas por Hospital */}
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <div className="px-6 py-4 border-b bg-gray-50">
                  <h4 className="text-md font-semibold text-gray-800 flex items-center gap-2">
                    <Building2 className="w-5 h-5 text-gray-600" />
                    Comparativa por Hospital
                  </h4>
                </div>

                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Hospital</th>
                        <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Total Camas</th>
                        <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Libres</th>
                        <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Ocupadas</th>
                        <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Ocupación</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {estadisticas.hospitales.map((hospital) => {
                        const ocupacion = hospital.ocupacion_porcentaje ?? 0;
                        return (
                          <tr key={hospital.hospital_id} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm font-medium text-gray-900">
                                {hospital.hospital_nombre}
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">
                              {hospital.total_camas}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-center">
                              <span className="text-sm font-medium text-green-600">
                                {hospital.camas_libres}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-center">
                              <span className="text-sm font-medium text-blue-600">
                                {hospital.camas_ocupadas}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-center">
                              <div className="flex items-center justify-center">
                                <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                                  <div
                                    className={`h-2 rounded-full ${
                                      ocupacion >= 90 ? 'bg-red-500' :
                                      ocupacion >= 70 ? 'bg-yellow-500' :
                                      'bg-green-500'
                                    }`}
                                    style={{ width: `${Math.min(ocupacion, 100)}%` }}
                                  />
                                </div>
                                <span className="text-sm font-medium text-gray-900">
                                  {ocupacion.toFixed(0)}%
                                </span>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
