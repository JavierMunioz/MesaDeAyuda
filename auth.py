from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse 
import jwt
from models import User 
from schemes import UserCreate
from db import SessionLocal 
from sqlalchemy.exc import SQLAlchemyError
import bcrypt
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from dotenv import load_dotenv
import os
import traceback 

load_dotenv()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login") 
auth_route = APIRouter(prefix="/auth", tags=["auth"])
SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = "HS256"

if not SECRET_KEY:
    raise ValueError("No se encontró SECRET_KEY en las variables de entorno. Revisa tu archivo .env")

def create_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=30) 
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def is_admin(token : str = Depends(oauth2_scheme)):
    data = jwt.decode(token, SECRET_KEY, ALGORITHM)

    if data['rol'] != 'admin':
        raise HTTPException(status_code=401, detail="Usuario no tiene permisos de administrador")

    return data

@auth_route.post('/create_user/', status_code=201) 
async def create_user(user_from_client: UserCreate, user_actual: dict = Depends(is_admin)):
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
        if db: db.rollback()
        print(f"Error de base de datos en create_user: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error de base de datos al crear el usuario.")
    except HTTPException: 
        raise
    except Exception as e:
        if db: db.rollback()
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
            print(f"ERROR CRÍTICO: form_data.password NO es una cadena. Tipo: {type(password_from_form)}, Valor: {password_from_form}")
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

        return JSONResponse(content={"access_token": token, "token_type": "bearer"})

    except SQLAlchemyError as e:
        if db: db.rollback()
        print(f"Error de base de datos en login: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error de base de datos durante el login.")
    except HTTPException: 
        raise
    except Exception as e:
        if db: db.rollback()
        print(f"Error inesperado en login: {e}")
        traceback.print_exc() 
        raise HTTPException(status_code=500, detail="Ocurrió un error inesperado durante el login.")
    finally:
        if db:
            db.close()


#user@example.com