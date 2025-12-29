"""
Excepciones personalizadas del sistema.
Proporciona excepciones semánticas para mejor manejo de errores.
"""


class BaseAppException(Exception):
    """
    Excepción base de la aplicación.
    Todas las excepciones personalizadas heredan de esta.
    """
    def __init__(self, message: str, code: str = "ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


# ============================================
# ERRORES DE VALIDACIÓN
# ============================================

class ValidationError(BaseAppException):
    """Error de validación de datos."""
    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR")


class InvalidStateError(BaseAppException):
    """Estado inválido para la operación solicitada."""
    def __init__(self, message: str):
        super().__init__(message, "INVALID_STATE")


# ============================================
# ERRORES DE NO ENCONTRADO
# ============================================

class NotFoundError(BaseAppException):
    """Recurso no encontrado."""
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            f"{resource} con identificador '{identifier}' no encontrado",
            "NOT_FOUND"
        )
        self.resource = resource
        self.identifier = identifier


class PacienteNotFoundError(NotFoundError):
    """Paciente no encontrado."""
    def __init__(self, paciente_id: str):
        super().__init__("Paciente", paciente_id)


class CamaNotFoundError(NotFoundError):
    """Cama no encontrada."""
    def __init__(self, cama_id: str):
        super().__init__("Cama", cama_id)


class HospitalNotFoundError(NotFoundError):
    """Hospital no encontrado."""
    def __init__(self, hospital_id: str):
        super().__init__("Hospital", hospital_id)


class ServicioNotFoundError(NotFoundError):
    """Servicio no encontrado."""
    def __init__(self, servicio_id: str):
        super().__init__("Servicio", servicio_id)


# ============================================
# ERRORES DE ESTADO DE CAMA
# ============================================

class CamaNoDisponibleError(BaseAppException):
    """Cama no disponible para la operación."""
    def __init__(self, cama_id: str, estado_actual: str, operacion: str = "asignación"):
        super().__init__(
            f"Cama {cama_id} no disponible para {operacion}. Estado actual: {estado_actual}",
            "CAMA_NO_DISPONIBLE"
        )
        self.cama_id = cama_id
        self.estado_actual = estado_actual


class EstadoInvalidoError(BaseAppException):
    """Estado inválido para realizar la operación."""
    def __init__(
        self, 
        operacion: str, 
        estado_actual: str, 
        estados_validos: list = None
    ):
        estados_msg = ""
        if estados_validos:
            estados_msg = f" Estados válidos: {', '.join(estados_validos)}"
        
        super().__init__(
            f"No se puede realizar '{operacion}'. Estado actual: {estado_actual}.{estados_msg}",
            "ESTADO_INVALIDO"
        )
        self.operacion = operacion
        self.estado_actual = estado_actual
        self.estados_validos = estados_validos or []


# ============================================
# ERRORES DE TRASLADO
# ============================================

class TrasladoError(BaseAppException):
    """Error en operación de traslado."""
    def __init__(self, message: str):
        super().__init__(message, "TRASLADO_ERROR")


class TrasladoNoPermitidoError(TrasladoError):
    """Traslado no permitido por reglas de negocio."""
    pass


# ============================================
# ERRORES DE DERIVACIÓN
# ============================================

class DerivacionError(BaseAppException):
    """Error en operación de derivación."""
    def __init__(self, message: str):
        super().__init__(message, "DERIVACION_ERROR")


class DerivacionNoPermitidaError(DerivacionError):
    """Derivación no permitida por reglas de negocio."""
    pass


# ============================================
# ERRORES DE ALTA
# ============================================

class AltaError(BaseAppException):
    """Error en operación de alta."""
    def __init__(self, message: str):
        super().__init__(message, "ALTA_ERROR")


class AltaNoPermitidaError(AltaError):
    """Alta no permitida, paciente tiene requerimientos pendientes."""
    pass


# ============================================
# ERRORES DE ARCHIVO
# ============================================

class ArchivoError(BaseAppException):
    """Error en operación con archivos."""
    def __init__(self, message: str):
        super().__init__(message, "ARCHIVO_ERROR")


class ArchivoNoPermitidoError(ArchivoError):
    """Tipo de archivo no permitido."""
    def __init__(self, extension: str, extensiones_permitidas: list):
        super().__init__(
            f"Extensión '{extension}' no permitida. "
            f"Extensiones válidas: {', '.join(extensiones_permitidas)}"
        )


class ArchivoMuyGrandeError(ArchivoError):
    """Archivo excede el tamaño máximo."""
    def __init__(self, size: int, max_size: int):
        super().__init__(
            f"Archivo de {size / 1024 / 1024:.1f}MB excede el máximo permitido "
            f"de {max_size / 1024 / 1024:.1f}MB"
        )

        