from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from typing import List
import traceback # Para logging detallado de errores

# Importaciones de tu proyecto
from db.db import SessionLocal # O SessionLocal directamente si así lo manejas
from db.models import Category
from db.schemes import CategoryCreate, CategoryOut
from auth.dependencies import is_admin # Asumiendo que solo admins manejan categorías

category_route = APIRouter(prefix="/categories", tags=["categories"])

# --- CREATE CATEGORY ---
@category_route.post("/", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    admin_user: dict = Depends(is_admin) # Solo admins pueden crear
):
    db = SessionLocal()
    db_category = Category(nombre=category_data.nombre, descripcion=category_data.descripcion)
    try:
        db.add(db_category)
        db.commit()
        db.refresh(db_category)
        return db_category
    except IntegrityError: # Ocurre si el nombre (unique=True) ya existe
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"La categoría con el nombre '{category_data.nombre}' ya existe."
        )
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Error de base de datos al crear categoría: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error de base de datos al crear la categoría.")
    except Exception as e:
        db.rollback()
        print(f"Error inesperado al crear categoría: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ocurrió un error inesperado al crear la categoría.")
    # No necesitas finally db.close() si usas get_db como dependencia con yield

# --- READ CATEGORY (GET ONE) ---
@category_route.get("/{category_id}", response_model=CategoryOut)
async def read_category(
    category_id: int
    # No se necesita autenticación para leer una categoría, a menos que lo requieras
):
    db = SessionLocal()
    db_category = db.query(Category).filter(Category.id == category_id).first()
    if db_category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada")
    return db_category

# --- READ CATEGORIES (GET ALL) ---
@category_route.get("/", response_model=List[CategoryOut])
async def read_categories(
    skip: int = 0,
    limit: int = 100,
    # No se necesita autenticación para leer categorías, a menos que lo requieras
):
    db = SessionLocal()
    categories = db.query(Category).offset(skip).limit(limit).all()
    return categories

# --- UPDATE CATEGORY ---
@category_route.put("/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: int,
    category_data: CategoryCreate, # Usar un esquema específico para update
    admin_user: dict = Depends(is_admin) # Solo admins pueden actualizar
):
    db = SessionLocal()
    db_category = db.query(Category).filter(Category.id == category_id).first()
    if db_category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada")

    # Actualizar solo los campos proporcionados
    update_data = category_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_category, key, value)
    
    try:
        db.commit()
        db.refresh(db_category)
        return db_category
    except IntegrityError: # Si se intenta cambiar el nombre a uno que ya existe
        db.rollback()
        # El mensaje de error podría ser más específico si sabemos qué campo causó el IntegrityError
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Error de integridad, es posible que el nombre de la categoría ya esté en uso."
        )
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Error de base de datos al actualizar categoría: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error de base de datos al actualizar la categoría.")
    except Exception as e:
        db.rollback()
        print(f"Error inesperado al actualizar categoría: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ocurrió un error inesperado al actualizar la categoría.")

# --- DELETE CATEGORY ---
@category_route.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    admin_user: dict = Depends(is_admin) # Solo admins pueden eliminar
):
    db = SessionLocal()
    db_category = db.query(Category).filter(Category.id == category_id).first()
    if db_category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada")
    
    try:
        # Considera qué pasa si hay tickets asociados a esta categoría.
        # SQLAlchemy podría fallar por restricción de FK si los tickets no tienen ON DELETE SET NULL o CASCADE.
        # O podrías querer impedir la eliminación si hay tickets asociados:
        # if db_category.tickets: # Asumiendo que la relación 'tickets' existe
        #     raise HTTPException(
        #         status_code=status.HTTP_409_CONFLICT,
        #         detail="No se puede eliminar la categoría porque tiene tickets asociados."
        #     )
        db.delete(db_category)
        db.commit()
        # No se devuelve contenido en un 204
    except IntegrityError as e: # Podría ocurrir si hay FK constraints
        db.rollback()
        print(f"Error de integridad al eliminar categoría: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar la categoría, es posible que esté siendo utilizada por tickets."
        )
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Error de base de datos al eliminar categoría: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error de base de datos al eliminar la categoría.")
    except Exception as e:
        db.rollback()
        print(f"Error inesperado al eliminar categoría: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ocurrió un error inesperado al eliminar la categoría.")