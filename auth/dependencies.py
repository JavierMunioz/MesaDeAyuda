from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
import jwt
from fastapi.security import OAuth2PasswordBearer
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

def is_normal_user(token : str = Depends(oauth2_scheme)):
    data = jwt.decode(token, SECRET_KEY, ALGORITHM)

    if data['rol'] != "normal":
        raise HTTPException(status_code=401, detail="Los administradores no puede crear tickets")
    
    return data