import React from 'react';
import { BarChart3, Bed, Users, Clock, Building2, TrendingUp } from 'lucide-react';
import type { EstadisticasGlobales } from '../types/Index';

interface EstadisticasProps {
  estadisticas: EstadisticasGlobales | null;
}

export function Estadisticas({ estadisticas }: EstadisticasProps) {
  if (!estadisticas) {
    return (
      <div className="loading">
        <BarChart3 className="spin" size={32} />
        <p>Cargando estadísticas...</p>
      </div>
    );
  }

  const getOcupacionColor = (porcentaje: number) => {
    if (porcentaje >= 90) return 'critical';
    if (porcentaje >= 75) return 'warning';
    if (porcentaje >= 50) return 'moderate';
    return 'good';
  };

  return (
    <div className="estadisticas-container">
      <div className="estadisticas-header">
        <BarChart3 size={24} />
        <h2>Estadísticas del Sistema</h2>
      </div>

      {/* Resumen global */}
      <section className="estadisticas-global">
        <h3>Resumen Global</h3>
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon">
              <Bed size={24} />
            </div>
            <div className="stat-content">
              <span className="stat-value">{estadisticas.totales.total_camas}</span>
              <span className="stat-label">Camas totales</span>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon success">
              <Bed size={24} />
            </div>
            <div className="stat-content">
              <span className="stat-value">{estadisticas.totales.camas_libres}</span>
              <span className="stat-label">Camas libres</span>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon warning">
              <Bed size={24} />
            </div>
            <div className="stat-content">
              <span className="stat-value">{estadisticas.totales.camas_ocupadas}</span>
              <span className="stat-label">Camas ocupadas</span>
            </div>
          </div>

          <div className="stat-card">
            <div className={`stat-icon ${getOcupacionColor(estadisticas.totales.porcentaje_ocupacion)}`}>
              <TrendingUp size={24} />
            </div>
            <div className="stat-content">
              <span className="stat-value">{estadisticas.totales.porcentaje_ocupacion.toFixed(1)}%</span>
              <span className="stat-label">Ocupación global</span>
            </div>
          </div>
        </div>
      </section>

      {/* Por hospital */}
      <section className="estadisticas-hospitales">
        <h3>Por Hospital</h3>
        <div className="hospitales-grid">
          {estadisticas.hospitales.map(hospital => (
            <div key={hospital.hospital_id} className="hospital-stats-card">
              <div className="hospital-header">
                <Building2 size={20} />
                <h4>{hospital.hospital_nombre}</h4>
              </div>

              <div className="ocupacion-bar-container">
                <div
                  className={`ocupacion-bar ${getOcupacionColor(hospital.porcentaje_ocupacion)}`}
                  style={{ width: `${Math.min(hospital.porcentaje_ocupacion, 100)}%` }}
                />
                <span className="ocupacion-text">
                  {hospital.porcentaje_ocupacion.toFixed(1)}% ocupación
                </span>
              </div>

              <div className="hospital-stats-grid">
                <div className="mini-stat">
                  <Bed size={14} />
                  <span>{hospital.total_camas} total</span>
                </div>
                <div className="mini-stat success">
                  <Bed size={14} />
                  <span>{hospital.camas_libres} libres</span>
                </div>
                <div className="mini-stat warning">
                  <Bed size={14} />
                  <span>{hospital.camas_ocupadas} ocupadas</span>
                </div>
                <div className="mini-stat info">
                  <Clock size={14} />
                  <span>{hospital.camas_traslado} en traslado</span>
                </div>
                <div className="mini-stat danger">
                  <Bed size={14} />
                  <span>{hospital.camas_limpieza} en limpieza</span>
                </div>
                <div className="mini-stat secondary">
                  <Bed size={14} />
                  <span>{hospital.camas_bloqueadas} bloqueadas</span>
                </div>
              </div>

              <div className="hospital-listas">
                <div className="lista-stat">
                  <Users size={14} />
                  <span>{hospital.pacientes_espera} en lista de espera</span>
                </div>
                {hospital.derivados_pendientes > 0 && (
                  <div className="lista-stat warning">
                    <Users size={14} />
                    <span>{hospital.derivados_pendientes} derivaciones pendientes</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Leyenda */}
      <section className="estadisticas-leyenda">
        <h4>Niveles de ocupación:</h4>
        <div className="leyenda-items">
          <div className="leyenda-item">
            <span className="leyenda-color good"></span>
            <span>&lt; 50% - Normal</span>
          </div>
          <div className="leyenda-item">
            <span className="leyenda-color moderate"></span>
            <span>50-74% - Moderado</span>
          </div>
          <div className="leyenda-item">
            <span className="leyenda-color warning"></span>
            <span>75-89% - Alto</span>
          </div>
          <div className="leyenda-item">
            <span className="leyenda-color critical"></span>
            <span>≥ 90% - Crítico</span>
          </div>
        </div>
      </section>
    </div>
  );
}