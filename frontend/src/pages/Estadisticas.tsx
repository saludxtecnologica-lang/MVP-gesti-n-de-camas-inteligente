import React, { useState, useEffect } from 'react';
import {
  BarChart3, Building2, BedDouble, Users, RefreshCw, Download,
  Clock, TrendingUp, AlertCircle, Activity, ArrowUpDown
} from 'lucide-react';
import { Spinner } from '../components/common';
import type { EstadisticasGlobales, EstadisticasCompletas, TiempoEstadistica } from '../types';
import * as api from '../services/api';

export function Estadisticas() {
  const [estadisticas, setEstadisticas] = useState<EstadisticasGlobales | null>(null);
  const [estadisticasAvanzadas, setEstadisticasAvanzadas] = useState<EstadisticasCompletas | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [diasPeriodo, setDiasPeriodo] = useState(7);
  const [downloading, setDownloading] = useState(false);

  const cargarEstadisticas = async () => {
    try {
      setLoading(true);
      setError(null);

      // Cargar estadísticas básicas y avanzadas en paralelo
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

  useEffect(() => {
    cargarEstadisticas();
  }, [diasPeriodo]);

  const handleDownload = async (formato: 'json' | 'csv') => {
    try {
      setDownloading(true);
      const blob = await api.downloadEstadisticas(diasPeriodo, formato);

      // Crear un link temporal y descargarlo
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
          <h4 className="font-semibold text-gray-700">{titulo}</h4>
        </div>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-xs text-gray-500 mb-1">Promedio</p>
            <p className="text-lg font-bold text-blue-600">{formatearTiempo(tiempo.promedio)}</p>
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

      {/* Resumen global */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Resumen Global</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-blue-50 rounded-lg p-4 text-center">
            <BedDouble className="w-8 h-8 mx-auto mb-2 text-blue-600" />
            <p className="text-3xl font-bold text-blue-800">
              {estadisticas.total_camas_sistema}
            </p>
            <p className="text-sm text-blue-600">Camas Totales</p>
          </div>
          <div className="bg-green-50 rounded-lg p-4 text-center">
            <Users className="w-8 h-8 mx-auto mb-2 text-green-600" />
            <p className="text-3xl font-bold text-green-800">
              {estadisticas.total_pacientes_sistema}
            </p>
            <p className="text-sm text-green-600">Pacientes Hospitalizados</p>
          </div>
          <div className="bg-purple-50 rounded-lg p-4 text-center">
            <BarChart3 className="w-8 h-8 mx-auto mb-2 text-purple-600" />
            <p className="text-3xl font-bold text-purple-800">
              {estadisticas.ocupacion_promedio.toFixed(1)}%
            </p>
            <p className="text-sm text-purple-600">Ocupación Promedio</p>
          </div>
        </div>
      </div>

      {/* Ingresos y Egresos */}
      {estadisticasAvanzadas && (
        <>
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-green-600" />
              Ingresos y Egresos (últimos {diasPeriodo} días)
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {estadisticasAvanzadas.ingresos_red && (
                <div className="bg-green-50 rounded-lg p-4">
                  <p className="text-sm text-gray-600 mb-2">Ingresos Totales de Red</p>
                  <p className="text-4xl font-bold text-green-700">
                    {estadisticasAvanzadas.ingresos_red.total}
                  </p>
                  {estadisticasAvanzadas.ingresos_red.desglose && (
                    <div className="mt-3 space-y-1">
                      <p className="text-xs text-gray-500">Desglose:</p>
                      {Object.entries(estadisticasAvanzadas.ingresos_red.desglose).map(([tipo, cantidad]) => (
                        <div key={tipo} className="flex justify-between text-sm">
                          <span className="text-gray-600">{tipo}:</span>
                          <span className="font-semibold text-gray-800">{cantidad as number}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {estadisticasAvanzadas.egresos_red && (
                <div className="bg-blue-50 rounded-lg p-4">
                  <p className="text-sm text-gray-600 mb-2">Egresos Totales de Red</p>
                  <p className="text-4xl font-bold text-blue-700">
                    {estadisticasAvanzadas.egresos_red.total}
                  </p>
                  {estadisticasAvanzadas.egresos_red.desglose && (
                    <div className="mt-3 space-y-1">
                      <p className="text-xs text-gray-500">Desglose:</p>
                      {Object.entries(estadisticasAvanzadas.egresos_red.desglose).map(([tipo, cantidad]) => (
                        <div key={tipo} className="flex justify-between text-sm">
                          <span className="text-gray-600">{tipo}:</span>
                          <span className="font-semibold text-gray-800">{cantidad as number}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Tiempos de Espera y Procesos */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <Clock className="w-5 h-5 text-orange-600" />
              Tiempos de Espera y Procesos
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {renderTiempoCard('Espera de Cama', estadisticasAvanzadas.tiempo_espera_cama, <Clock className="w-4 h-4 text-orange-600" />)}
              {renderTiempoCard('Derivación Pendiente', estadisticasAvanzadas.tiempo_derivacion_pendiente, <Clock className="w-4 h-4 text-yellow-600" />)}
              {renderTiempoCard('Traslado Saliente', estadisticasAvanzadas.tiempo_traslado_saliente, <ArrowUpDown className="w-4 h-4 text-blue-600" />)}
              {renderTiempoCard('Confirmación Traslado', estadisticasAvanzadas.tiempo_confirmacion_traslado, <Clock className="w-4 h-4 text-purple-600" />)}
              {estadisticasAvanzadas.tiempo_alta && renderTiempoCard('Alta Sugerida', estadisticasAvanzadas.tiempo_alta.alta_sugerida, <Clock className="w-4 h-4 text-green-600" />)}
              {estadisticasAvanzadas.tiempo_alta && renderTiempoCard('Alta Completada', estadisticasAvanzadas.tiempo_alta.alta_completada, <Clock className="w-4 h-4 text-teal-600" />)}
              {renderTiempoCard('Proceso de Fallecimiento', estadisticasAvanzadas.tiempo_fallecido, <Clock className="w-4 h-4 text-gray-600" />)}
              {renderTiempoCard('Hospitalización (Hospital)', estadisticasAvanzadas.tiempo_hospitalizacion_hospital, <Activity className="w-4 h-4 text-indigo-600" />)}
              {renderTiempoCard('Hospitalización (Red)', estadisticasAvanzadas.tiempo_hospitalizacion_red, <Activity className="w-4 h-4 text-blue-600" />)}
            </div>
          </div>

          {/* Tasas de Ocupación */}
          {estadisticasAvanzadas.tasa_ocupacion_red && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-purple-600" />
                Tasas de Ocupación
              </h3>
              <div className="bg-purple-50 rounded-lg p-6 mb-4">
                <p className="text-sm text-gray-600 mb-2">Ocupación de Red</p>
                <div className="flex items-center gap-4">
                  <div className="flex-1">
                    <div className="w-full bg-gray-200 rounded-full h-6">
                      <div
                        className={`h-6 rounded-full flex items-center justify-center text-white text-sm font-semibold ${
                          estadisticasAvanzadas.tasa_ocupacion_red.tasa_ocupacion >= 90 ? 'bg-red-500' :
                          estadisticasAvanzadas.tasa_ocupacion_red.tasa_ocupacion >= 70 ? 'bg-yellow-500' :
                          'bg-green-500'
                        }`}
                        style={{ width: `${Math.min(estadisticasAvanzadas.tasa_ocupacion_red.tasa_ocupacion, 100)}%` }}
                      >
                        {estadisticasAvanzadas.tasa_ocupacion_red.tasa_ocupacion.toFixed(1)}%
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold text-purple-700">
                      {estadisticasAvanzadas.tasa_ocupacion_red.camas_ocupadas} / {estadisticasAvanzadas.tasa_ocupacion_red.camas_totales}
                    </p>
                    <p className="text-xs text-gray-500">Ocupadas / Totales</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Flujos más repetidos */}
          {estadisticasAvanzadas.flujos_mas_repetidos && estadisticasAvanzadas.flujos_mas_repetidos.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
                <ArrowUpDown className="w-5 h-5 text-blue-600" />
                Flujos Más Repetidos
              </h3>
              <div className="space-y-2">
                {estadisticasAvanzadas.flujos_mas_repetidos.map((flujo, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <span className="text-sm text-gray-700">{flujo.flujo}</span>
                    <span className="font-semibold text-blue-600">{flujo.cantidad} veces</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Servicios con Mayor Demanda */}
          {estadisticasAvanzadas.servicios_mayor_demanda && estadisticasAvanzadas.servicios_mayor_demanda.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-red-600" />
                Servicios con Mayor Demanda
              </h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Servicio</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Ocupación</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">En Espera</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Demanda</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {estadisticasAvanzadas.servicios_mayor_demanda.map((servicio) => (
                      <tr key={servicio.servicio_id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm text-gray-900">{servicio.servicio_nombre}</td>
                        <td className="px-4 py-3 text-center">
                          <span className={`text-sm font-semibold ${
                            servicio.tasa_ocupacion >= 90 ? 'text-red-600' :
                            servicio.tasa_ocupacion >= 70 ? 'text-yellow-600' :
                            'text-green-600'
                          }`}>
                            {servicio.tasa_ocupacion.toFixed(1)}%
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center text-sm font-semibold text-orange-600">
                          {servicio.pacientes_en_espera}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                            {servicio.demanda_score.toFixed(1)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Casos Especiales */}
          {estadisticasAvanzadas.casos_especiales && estadisticasAvanzadas.casos_especiales.total > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-yellow-600" />
                Casos Especiales
              </h3>
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
                  <p className="text-xs text-gray-600 mt-1">Casos Socio-Judiciales</p>
                </div>
              </div>
            </div>
          )}

          {/* Subutilización */}
          {estadisticasAvanzadas.servicios_subutilizados && estadisticasAvanzadas.servicios_subutilizados.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
                <Activity className="w-5 h-5 text-gray-600" />
                Servicios Subutilizados
              </h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Servicio</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Camas Libres</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Camas Totales</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">% Libre</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {estadisticasAvanzadas.servicios_subutilizados.map((servicio) => (
                      <tr key={servicio.servicio_id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm text-gray-900">{servicio.servicio_nombre}</td>
                        <td className="px-4 py-3 text-center text-sm font-semibold text-green-600">
                          {servicio.camas_libres}
                        </td>
                        <td className="px-4 py-3 text-center text-sm text-gray-600">
                          {servicio.camas_totales}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            {servicio.tasa_libre.toFixed(1)}%
                          </span>
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

      {/* Estadísticas por hospital */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b bg-gray-50">
          <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
            <Building2 className="w-5 h-5 text-gray-600" />
            Estadísticas por Hospital
          </h3>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Hospital
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Total Camas
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Libres
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Ocupadas
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  En Traslado
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Limpieza
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Bloqueadas
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Espera
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Ocupación
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {estadisticas.hospitales.map((hospital) => {
                const ocupacion = hospital.ocupacion_porcentaje ?? hospital.porcentaje_ocupacion ?? 0;
                const espera = hospital.pacientes_en_espera ?? hospital.pacientes_espera ?? 0;

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
                      <span className="text-sm font-medium text-yellow-600">
                        {hospital.camas_traslado}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <span className="text-sm font-medium text-gray-600">
                        {hospital.camas_limpieza}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <span className="text-sm font-medium text-red-600">
                        {hospital.camas_bloqueadas}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <span className="text-sm font-medium text-orange-600">
                        {espera}
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
  );
}
