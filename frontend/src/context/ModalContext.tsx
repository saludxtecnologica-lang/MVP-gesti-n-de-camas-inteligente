import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import type { Paciente, Cama } from '../types';

// ============================================
// TIPOS
// ============================================

export type ModalType = 
  | 'paciente' 
  | 'reevaluar' 
  | 'verPaciente' 
  | 'configuracion' 
  | 'asignacionManual' 
  | 'intercambio';

export interface ModalData {
  paciente?: Paciente;
  cama?: Cama;
  pacienteId?: string;
  fromLista?: boolean;
}

interface ModalState {
  type: ModalType | null;
  data: ModalData;
}

interface ModalContextType {
  modalState: ModalState;
  openModal: (type: ModalType, data?: ModalData) => void;
  closeModal: () => void;
  isOpen: (type: ModalType) => boolean;
}

const ModalContext = createContext<ModalContextType | null>(null);

// ============================================
// PROVIDER
// ============================================

export function ModalProvider({ children }: { children: ReactNode }) {
  const [modalState, setModalState] = useState<ModalState>({
    type: null,
    data: {}
  });

  const openModal = useCallback((type: ModalType, data: ModalData = {}) => {
    setModalState({ type, data });
  }, []);

  const closeModal = useCallback(() => {
    setModalState({ type: null, data: {} });
  }, []);

  const isOpen = useCallback((type: ModalType) => {
    return modalState.type === type;
  }, [modalState.type]);

  return (
    <ModalContext.Provider value={{ modalState, openModal, closeModal, isOpen }}>
      {children}
    </ModalContext.Provider>
  );
}

// ============================================
// HOOK
// ============================================

export function useModal() {
  const context = useContext(ModalContext);
  if (!context) {
    throw new Error('useModal debe usarse dentro de ModalProvider');
  }
  return context;
}