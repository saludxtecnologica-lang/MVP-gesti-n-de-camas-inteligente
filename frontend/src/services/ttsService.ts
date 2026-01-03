/**
 * Servicio de Text-to-Speech para notificaciones audibles
 * 
 * Este servicio maneja la síntesis de voz para las notificaciones del sistema
 * de gestión de camas. Utiliza la Web Speech API nativa del navegador.
 */

// ============================================
// TIPOS
// ============================================

export interface MensajeAudible {
  tipo: 'asignacion' | 'traslado_completado' | 'derivacion_aceptada';
  mensaje: string;
  servicioOrigenId?: string | null;
  servicioDestinoId?: string | null;
  hospitalOrigenId?: string | null;
  hospitalDestinoId?: string | null;
  prioridad?: 'alta' | 'normal' | 'baja';
}

export interface TTSConfig {
  habilitado: boolean;
  volumen: number; // 0 a 1
  velocidad: number; // 0.1 a 10, 1 es normal
  tono: number; // 0 a 2, 1 es normal
  idioma: string; // 'es-ES' o 'es-CL'
}

// ============================================
// CONFIGURACIÓN POR DEFECTO
// ============================================

const CONFIG_DEFAULT: TTSConfig = {
  habilitado: true,
  volumen: 1,
  velocidad: 0.9, // Un poco más lento para mejor comprensión
  tono: 1,
  idioma: 'es-ES'
};

// ============================================
// CLASE DEL SERVICIO TTS
// ============================================

class TTSService {
  private synth: SpeechSynthesis | null = null;
  private config: TTSConfig = CONFIG_DEFAULT;
  private colaTextos: string[] = [];
  private hablando: boolean = false;
  private vocesCargadas: boolean = false;
  private vozPreferida: SpeechSynthesisVoice | null = null;

  constructor() {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      this.synth = window.speechSynthesis;
      this.inicializarVoces();
    } else {
      console.warn('[TTS] Speech Synthesis no está disponible en este navegador');
    }
  }

  /**
   * Inicializa las voces disponibles
   */
  private inicializarVoces(): void {
    if (!this.synth) return;

    const cargarVoces = () => {
      const voces = this.synth!.getVoices();
      
      if (voces.length === 0) {
        // Reintentar si no hay voces todavía
        setTimeout(cargarVoces, 100);
        return;
      }

      // Buscar voz en español (preferir español latinoamericano o de Chile)
      this.vozPreferida = voces.find(v => 
        v.lang === 'es-CL' || v.lang === 'es-419'
      ) || voces.find(v => 
        v.lang.startsWith('es-')
      ) || voces.find(v => 
        v.lang.startsWith('es')
      ) || voces[0];

      this.vocesCargadas = true;
      console.log('[TTS] Voz seleccionada:', this.vozPreferida?.name, this.vozPreferida?.lang);
    };

    // Las voces pueden no estar disponibles inmediatamente
    if (this.synth.getVoices().length > 0) {
      cargarVoces();
    } else {
      this.synth.onvoiceschanged = cargarVoces;
    }
  }

  /**
   * Verifica si el TTS está disponible
   */
  public estaDisponible(): boolean {
    return this.synth !== null && this.vocesCargadas;
  }

  /**
   * Configura el servicio TTS
   */
  public configurar(config: Partial<TTSConfig>): void {
    this.config = { ...this.config, ...config };
    console.log('[TTS] Configuración actualizada:', this.config);
  }

  /**
   * Habilita o deshabilita el TTS
   */
  public setHabilitado(habilitado: boolean): void {
    this.config.habilitado = habilitado;
    if (!habilitado) {
      this.cancelar();
    }
  }

  /**
   * Verifica si el TTS está habilitado
   */
  public estaHabilitado(): boolean {
    return this.config.habilitado;
  }

  /**
   * Cancela cualquier mensaje en reproducción
   */
  public cancelar(): void {
    if (this.synth) {
      this.synth.cancel();
      this.colaTextos = [];
      this.hablando = false;
    }
  }

  /**
   * Reproduce un mensaje de texto
   */
  public hablar(texto: string, prioridad: 'alta' | 'normal' | 'baja' = 'normal'): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.synth || !this.config.habilitado) {
        resolve();
        return;
      }

      if (!this.vocesCargadas) {
        console.warn('[TTS] Las voces aún no están cargadas, esperando...');
        setTimeout(() => {
          this.hablar(texto, prioridad).then(resolve).catch(reject);
        }, 500);
        return;
      }

      // Si es alta prioridad, interrumpir lo que se está hablando
      if (prioridad === 'alta') {
        this.cancelar();
      }

      const utterance = new SpeechSynthesisUtterance(texto);
      
      // Aplicar configuración
      utterance.volume = this.config.volumen;
      utterance.rate = this.config.velocidad;
      utterance.pitch = this.config.tono;
      
      if (this.vozPreferida) {
        utterance.voice = this.vozPreferida;
      }
      
      utterance.lang = this.config.idioma;

      utterance.onstart = () => {
        this.hablando = true;
        console.log('[TTS] Iniciando:', texto.substring(0, 50) + '...');
      };

      utterance.onend = () => {
        this.hablando = false;
        this.procesarCola();
        resolve();
      };

      utterance.onerror = (event) => {
        this.hablando = false;
        console.error('[TTS] Error:', event.error);
        this.procesarCola();
        reject(event.error);
      };

      // Si ya está hablando, agregar a la cola
      if (this.hablando && prioridad !== 'alta') {
        this.colaTextos.push(texto);
      } else {
        this.synth.speak(utterance);
      }
    });
  }

  /**
   * Procesa la cola de mensajes pendientes
   */
  private procesarCola(): void {
    if (this.colaTextos.length > 0 && !this.hablando) {
      const siguiente = this.colaTextos.shift();
      if (siguiente) {
        this.hablar(siguiente);
      }
    }
  }

  /**
   * Reproduce un mensaje de prueba
   */
  public probar(): void {
    this.hablar('Sistema de notificaciones audibles activado', 'alta');
  }
}

// ============================================
// FUNCIONES HELPER PARA GENERAR MENSAJES
// ============================================

/**
 * Genera el mensaje audible para asignación de cama
 */
export function generarMensajeAsignacion(
  camaIdentificador: string,
  pacienteNombre: string,
  servicioOrigen: string | null,
  camaOrigen: string | null
): string {
  let mensaje = `Cama ${camaIdentificador}, ha sido asignada a paciente ${pacienteNombre}`;
  
  if (servicioOrigen) {
    mensaje += `, de origen servicio ${servicioOrigen}`;
  }
  
  if (camaOrigen) {
    mensaje += `, de la cama ${camaOrigen}`;
  }
  
  return mensaje;
}

/**
 * Genera el mensaje audible para traslado completado
 */
export function generarMensajeTrasladoCompletado(
  servicioDestino: string,
  pacienteNombre: string,
  camaOrigen: string
): string {
  return `Traslado a servicio ${servicioDestino} de paciente ${pacienteNombre} completado, cama ${camaOrigen} entra a fase de limpieza`;
}

/**
 * Genera el mensaje audible para derivación aceptada
 */
export function generarMensajeDerivacionAceptada(
  pacienteNombre: string,
  hospitalDestino: string
): string {
  return `Paciente ${pacienteNombre} ha sido aceptado en ${hospitalDestino} en espera de asignación de cama`;
}

// ============================================
// INSTANCIA SINGLETON
// ============================================

export const ttsService = new TTSService();

// ============================================
// EXPORT DEFAULT
// ============================================

export default ttsService;