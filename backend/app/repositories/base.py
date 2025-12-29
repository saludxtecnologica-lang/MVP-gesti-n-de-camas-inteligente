"""
Repository Base.
Proporciona operaciones CRUD genéricas.
"""
from typing import TypeVar, Generic, Optional, List, Type, Any
from sqlmodel import Session, select
from pydantic import BaseModel

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Repository base genérico.
    
    Proporciona operaciones CRUD comunes para cualquier modelo.
    
    Uso:
        class MiRepository(BaseRepository[MiModelo]):
            def __init__(self, session: Session):
                super().__init__(session, MiModelo)
    """
    
    def __init__(self, session: Session, model: Type[T]):
        """
        Inicializa el repository.
        
        Args:
            session: Sesión de base de datos
            model: Clase del modelo SQLModel
        """
        self.session = session
        self.model = model
    
    def obtener_por_id(self, id: str) -> Optional[T]:
        """
        Obtiene un registro por ID.
        
        Args:
            id: ID del registro
        
        Returns:
            El registro o None si no existe
        """
        return self.session.get(self.model, id)
    
    def obtener_todos(self) -> List[T]:
        """
        Obtiene todos los registros.
        
        Returns:
            Lista de todos los registros
        """
        return list(self.session.exec(select(self.model)).all())
    
    def crear(self, data: BaseModel) -> T:
        """
        Crea un nuevo registro.
        
        Args:
            data: Schema Pydantic con los datos
        
        Returns:
            El registro creado
        """
        obj = self.model(**data.model_dump())
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj
    
    def crear_desde_dict(self, data: dict) -> T:
        """
        Crea un nuevo registro desde un diccionario.
        
        Args:
            data: Diccionario con los datos
        
        Returns:
            El registro creado
        """
        obj = self.model(**data)
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj
    
    def actualizar(self, obj: T, data: BaseModel) -> T:
        """
        Actualiza un registro existente.
        
        Args:
            obj: El registro a actualizar
            data: Schema Pydantic con los nuevos datos
        
        Returns:
            El registro actualizado
        """
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(obj, key, value)
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj
    
    def actualizar_desde_dict(self, obj: T, data: dict) -> T:
        """
        Actualiza un registro desde un diccionario.
        
        Args:
            obj: El registro a actualizar
            data: Diccionario con los nuevos datos
        
        Returns:
            El registro actualizado
        """
        for key, value in data.items():
            if value is not None:
                setattr(obj, key, value)
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj
    
    def eliminar(self, obj: T) -> None:
        """
        Elimina un registro.
        
        Args:
            obj: El registro a eliminar
        """
        self.session.delete(obj)
        self.session.commit()
    
    def guardar(self, obj: T) -> T:
        """
        Guarda cambios en un registro.
        
        Args:
            obj: El registro a guardar
        
        Returns:
            El registro guardado
        """
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj
    
    def contar(self) -> int:
        """
        Cuenta todos los registros.
        
        Returns:
            Número de registros
        """
        from sqlmodel import func
        result = self.session.exec(
            select(func.count()).select_from(self.model)
        ).first()
        return result or 0