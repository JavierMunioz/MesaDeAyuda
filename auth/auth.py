from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
import jwt
from db.models import User
from db.schemes import UserCreate, UserOut  # Import UserOut
from db.db import SessionLocal
from sqlalchemy.exc import SQLAlchemyError
import bcrypt
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from dotenv import load_dotenv
import os
from auth.dependencies import *
import traceback
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from enum import Enum

load_dotenv()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
auth_route = APIRouter(prefix="/auth", tags=["auth"])
SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = "HS256"

if not SECRET_KEY:
    raise ValueError(
        "No se encontró SECRET_KEY en las variables de entorno. Revisa tu archivo .env")


class RolEnum(str, Enum):
    normal = "normal"
    admin = "admin"


class UserBase(BaseModel):
    correo: EmailStr
    username: str
    rol: RolEnum
    estatus: Optional[str] = "activo"


class UserCreate(UserBase):
    password: str


@auth_route.post('/create_user/', status_code=201)
async def create_user(user_from_client: UserCreate, user: dict = Depends(is_admin)):
    db = None
    try:
        db = SessionLocal()
        user_exists = db.query(User).filter(
            (User.username == user_from_client.username) | (User.correo == user_from_client.correo)
        ).first()

        if user_exists:
            raise HTTPException(
                status_code=400,
                detail="Ya existe un usuario con ese nombre de usuario o correo electrónico."
            )

        password_bytes = user_from_client.password.encode("utf-8")
        hashed_password_bytes = bcrypt.hashpw(password_bytes, bcrypt.gensalt())

        hashed_password_str = hashed_password_bytes.decode('utf-8')

        user_created = User(
            correo=user_from_client.correo,
            username=user_from_client.username,
            password_hash=hashed_password_str,
            rol=user_from_client.rol
        )

        db.add(user_created)
        db.commit()

        return {"message": "Usuario Creado Correctamente"}

    except SQLAlchemyError as e:
        if db:
            db.rollback()
        print(f"Error de base de datos en create_user: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error de base de datos al crear el usuario.")
    except HTTPException:
        raise
    except Exception as e:
        if db:
            db.rollback()
        print(f"Error inesperado en create_user: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Ocurrió un error inesperado al crear el usuario.")
    finally:
        if db:
            db.close()


@auth_route.post('/login/')
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = None
    try:
        db = SessionLocal()

        user_email_from_form = form_data.username
        password_from_form = form_data.password

        if not isinstance(password_from_form, str):
            print(
                f"ERROR CRÍTICO: form_data.password NO es una cadena. Tipo: {type(password_from_form)}, Valor: {password_from_form}")
            raise HTTPException(
                status_code=422,
                detail="El formato de la contraseña enviada es incorrecto. Debe ser una cadena de texto simple en el campo 'password' del formulario."
            )

        user_exists = db.query(User).filter(User.correo == user_email_from_form).first()

        if not user_exists:
            raise HTTPException(status_code=400, detail="Credenciales incorrectas (usuario no encontrado)")

        # Debug: Verificar tipos
        print(f"Tipo de password_from_form: {type(password_from_form)}")
        print(f"Tipo de user_exists.password_hash: {type(user_exists.password_hash)}")

        password_from_form_bytes = password_from_form.encode('utf-8')

        hashed_password_from_db_bytes = user_exists.password_hash.encode('utf-8')

        if not bcrypt.checkpw(password_from_form_bytes, hashed_password_from_db_bytes):
            raise HTTPException(status_code=400, detail="Credenciales incorrectas (contraseña no coincide)")

        token = create_token({
            "sub": user_exists.username,
            "email": user_exists.correo,
            "rol": user_exists.rol.value if hasattr(user_exists.rol, 'value') else user_exists.rol
        })

        refresh_token = create_refresh_token({
            "sub": user_exists.username,
            "email": user_exists.correo,
            "rol": user_exists.rol.value if hasattr(user_exists.rol, 'value') else user_exists.rol
        })

        return JSONResponse(
            content={"access_token": token, "token_type": "bearer", "refresh_token": refresh_token})

    except SQLAlchemyError as e:
        if db:
            db.rollback()
        print(f"Error de base de datos en login: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error de base de datos durante el login.")
    except HTTPException:
        raise
    except Exception as e:
        if db:
            db.rollback()
        print(f"Error inesperado en login: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Ocurrió un error inesperado durante el login.")
    finally:
        if db:
            db.close()


@auth_route.post("/refresh")
async def refresh_token(request: Request):
    try:
        body = await request.json()
        refresh_token = body.get("refresh_token")
        if not refresh_token:
            raise HTTPException(status_code=401, detail="Refresh token requerido")

        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        # Verifica que sea un refresh válido y no esté expirado

        new_access_token = create_token({
            "sub": payload["sub"],
            "email": payload["email"],
            "rol": payload["rol"]
        })

        return {"access_token": new_access_token}

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")


# --- GET USERS ENDPOINT ---
@auth_route.get("/users", response_model=List[UserOut])
async def get_users(skip: int = 0, limit: int = 100, user: dict = Depends(is_admin)):
    db = None
    try:
        db = SessionLocal()
        users = db.query(User).offset(skip).limit(limit).all()
        return users
    except SQLAlchemyError as e:
        if db:
            db.rollback()
        print(f"Error de base de datos en get_users: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error de base de datos al obtener usuarios.")
    except Exception as e:
        if db:
            db.rollback()
        print(f"Error inesperado en get_users: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Ocurrió un error inesperado al obtener los usuarios.")
    finally:
        if db:
            db.close()


# --- GET USER BY ID ENDPOINT ---
@auth_route.get("/users/{user_id}", response_model=UserOut)
async def get_user_by_id(user_id: int, user: dict = Depends(is_admin)):
    db = None
    try:
        db = SessionLocal()
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        return user
    except SQLAlchemyError as e:
        if db:
            db.rollback()
        print(f"Error de base de datos en get_user: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error de base de datos al obtener el usuario.")
    except Exception as e:
        if db:
            db.rollback()
        print(f"Error inesperado en get_user: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Ocurrió un error inesperado al obtener el usuario.")
    finally:
        if db:
            db.close()


# --- UPDATE USER ENDPOINT ---
@auth_route.put("/users/{user_id}", response_model=UserOut)
async def update_user(user_id: int, user_data: UserBase, user: dict = Depends(is_admin)):
    db = None
    try:
        db = SessionLocal()
        user_to_update = db.query(User).filter(User.id == user_id).first()

        if user_to_update is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        # Actualizar solo los campos proporcionados en user_data
        for key, value in user_data.dict(exclude_unset=True).items():
            setattr(user_to_update, key, value)

        db.commit()
        db.refresh(user_to_update)
        return user_to_update
    except SQLAlchemyError as e:
        if db:
            db.rollback()
        print(f"Error de base de datos al actualizar usuario: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error de base de datos al actualizar el usuario.")
    except Exception as e:
        if db:
            db.rollback()
        print(f"Error inesperado al actualizar usuario: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Ocurrió un error inesperado al actualizar el usuario.")
    finally:
        if db:
            db.close()


# --- DELETE USER ENDPOINT ---
@auth_route.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: int, user: dict = Depends(is_admin)):
    db = None
    try:
        db = SessionLocal()
        user_to_delete = db.query(User).filter(User.id == user_id).first()

        if user_to_delete is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        db.delete(user_to_delete)
        db.commit()
        return  # 204 No Content
    except SQLAlchemyError as e:
        if db:
            db.rollback()
        print(f"Error de base de datos al eliminar usuario: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error de base de datos al eliminar el usuario.")
    except Exception as e:
        if db:
            db.rollback()
        print(f"Error inesperado al eliminar usuario: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Ocurrió un error inesperado al eliminar el usuario.")
    finally:
        if db:
            db.close()