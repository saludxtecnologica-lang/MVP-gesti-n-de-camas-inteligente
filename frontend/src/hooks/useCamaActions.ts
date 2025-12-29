import { useCallback } from 'react';
import { useApp } from '../context/AppContext';
import { useModal } from '../context/ModalContext';
import type { Paciente, Cama } from '../types';
import * as api from '../services/api';

export function useCamaActions() {
  const { showAlert, recargarCamas, recargarListaEspera, recargarTodo } = useApp();
  const { openModal } = useModal();

  // Ver paciente
  const handleVerPaciente = useCallback((paciente: Paciente) => {
    openModal('verPaciente', { paciente });
  }, [openModal]);

  // Reevaluar paciente
  const handleReevaluar = useCallback((paciente: Paciente) => {
    openModal('reevaluar', { paciente });
  }, [openModal]);

  // Completar traslado
  const handleCompletarTraslado = useCallback(async (pacienteId: string) => {
    try {
      const result = await api.completarTraslado(pacienteId);
      showAlert('success', result.message || 'Traslado completado');
      await recargarTodo();
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al completar traslado');
    }
  }, [showAlert, recargarTodo]);

  // Cancelar traslado
  const handleCancelarTraslado = useCallback(async (pacienteId: string) => {
    try {
      const result = await api.cancelarTraslado(pacienteId);
      showAlert('success', result.message || 'Traslado cancelado');
      await recargarTodo();
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al cancelar traslado');
    }
  }, [showAlert, recargarTodo]);

  // Cancelar desde origen (traslados internos)
  const handleCancelarDesdeOrigen = useCallback(async (pacienteId: string) => {
    try {
      const result = await api.cancelarTrasladoDesdeOrigen(pacienteId);
      showAlert('success', result.message || 'Traslado cancelado desde origen');
      await recargarTodo();
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al cancelar traslado');
    }
  }, [showAlert, recargarTodo]);

  // ============================================
  // NUEVO: Cancelar traslado confirmado
  // ============================================
  const handleCancelarTrasladoConfirmado = useCallback(async (pacienteId: string) => {
    try {
      const result = await api.cancelarTrasladoConfirmado(pacienteId);
      showAlert('success', result.message || 'Traslado confirmado cancelado');
      await recargarTodo();
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al cancelar traslado confirmado');
    }
  }, [showAlert, recargarTodo]);

  // Buscar nueva cama
  const handleBuscarNuevaCama = useCallback(async (pacienteId: string) => {
    try {
      const result = await api.buscarCamaPaciente(pacienteId);
      showAlert('success', result.message || 'Búsqueda de cama iniciada');
      await recargarTodo();
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al buscar cama');
    }
  }, [showAlert, recargarTodo]);

  // Bloquear/desbloquear cama
  const handleBloquear = useCallback(async (camaId: string, bloquear: boolean, motivo?: string) => {
    try {
      const result = await api.bloquearCama(camaId, { bloquear, motivo });
      showAlert('success', result.message || (bloquear ? 'Cama bloqueada' : 'Cama desbloqueada'));
      await recargarCamas();
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al cambiar estado de cama');
    }
  }, [showAlert, recargarCamas]);

  // Iniciar alta
  const handleIniciarAlta = useCallback(async (pacienteId: string) => {
    try {
      const result = await api.iniciarAlta(pacienteId);
      showAlert('success', result.message || 'Alta iniciada');
      await recargarTodo();
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al iniciar alta');
    }
  }, [showAlert, recargarTodo]);

  // Dar alta (ejecutar)
  const handleDarAlta = useCallback(async (pacienteId: string) => {
    try {
      const result = await api.ejecutarAlta(pacienteId);
      showAlert('success', result.message || 'Alta ejecutada');
      await recargarTodo();
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al ejecutar alta');
    }
  }, [showAlert, recargarTodo]);

  // Cancelar alta
  const handleCancelarAlta = useCallback(async (pacienteId: string) => {
    try {
      const result = await api.cancelarAlta(pacienteId);
      showAlert('success', result.message || 'Alta cancelada');
      await recargarTodo();
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al cancelar alta');
    }
  }, [showAlert, recargarTodo]);

  // Confirmar egreso (derivación)
  const handleConfirmarEgreso = useCallback(async (pacienteId: string) => {
    try {
      const result = await api.confirmarEgresoDerivacion(pacienteId);
      showAlert('success', result.message || 'Egreso confirmado');
      await recargarTodo();
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al confirmar egreso');
    }
  }, [showAlert, recargarTodo]);

  // Cancelar derivación desde origen
  const handleCancelarDerivacion = useCallback(async (pacienteId: string) => {
    try {
      const result = await api.cancelarDerivacionDesdeOrigen(pacienteId);
      showAlert('success', result.message || 'Derivación cancelada');
      await recargarTodo();
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al cancelar derivación');
    }
  }, [showAlert, recargarTodo]);

  // Omitir pausa oxígeno
  const handleOmitirPausaOxigeno = useCallback(async (pacienteId: string) => {
    try {
      const result = await api.omitirPausaOxigeno(pacienteId);
      showAlert('success', result.message || 'Evaluación completada');
      await recargarTodo();
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al omitir pausa');
    }
  }, [showAlert, recargarTodo]);

  // Asignación manual
  const handleAsignarManual = useCallback((cama: Cama) => {
    openModal('asignacionManual', { cama });
  }, [openModal]);

  // Intercambio
  const handleIntercambio = useCallback((cama: Cama) => {
    openModal('intercambio', { cama });
  }, [openModal]);

  // Egreso manual
  const handleEgresarManual = useCallback(async (pacienteId: string) => {
    try {
      const result = await api.egresarManual(pacienteId);
      showAlert('success', result.message || 'Paciente egresado');
      await recargarTodo();
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al egresar paciente');
    }
  }, [showAlert, recargarTodo]);

  return {
    handleVerPaciente,
    handleReevaluar,
    handleCompletarTraslado,
    handleCancelarTraslado,
    handleCancelarDesdeOrigen,
    handleCancelarTrasladoConfirmado,  // NUEVO
    handleBuscarNuevaCama,
    handleBloquear,
    handleIniciarAlta,
    handleDarAlta,
    handleCancelarAlta,
    handleConfirmarEgreso,
    handleCancelarDerivacion,
    handleOmitirPausaOxigeno,
    handleAsignarManual,
    handleIntercambio,
    handleEgresarManual
  };
}