from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
from enum import Enum


# --- ENUMS ---

class RolEnum(str, Enum):
    admin = "admin"
    normal = "normal"

class UrgenciaEnum(str, Enum):
    baja = "baja"
    media = "media"
    alta = "alta"

class PrioridadEnum(str, Enum):
    baja = "baja"
    media = "media"
    alta = "alta"

class EstadoEnum(str, Enum):
    abierto = "abierto"
    en_proceso = "en_proceso"
    cerrado = "cerrado"


# --- CATEGORY ---

class CategoryBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryOut(CategoryBase):
    id: int

    class Config:
        orm_mode = True


# --- USER ---

class UserBase(BaseModel):
    correo: EmailStr
    username: str
    rol: RolEnum
    estatus: Optional[str] = "activo"

class UserCreate(UserBase):
    password: str

class UserOut(BaseModel):
    id: int
    correo: EmailStr
    username: str
    rol: RolEnum
    estatus: str

    class Config:
        orm_mode = True


# --- TICKET CHAT ---

class TicketChatBase(BaseModel):
    mensaje: str

class TicketChatCreate(TicketChatBase):
    pass

class TicketChatOut(TicketChatBase):
    id: int
    fecha_envio: datetime
    autor: UserOut

    class Config:
        orm_mode = True


# --- TICKET ---

class TicketBase(BaseModel):
    asunto: str
    descripcion: str
    categoria_id: int
    urgencia: UrgenciaEnum
    prioridad: PrioridadEnum
    estado: Optional[EstadoEnum] = EstadoEnum.abierto
    consultor_id: Optional[int] = None

class TicketCreate(TicketBase):
    pass

class TicketOut(TicketBase):
    id: int
    fecha_creacion: datetime
    fecha_cierre: Optional[datetime] = None
    usuario_owner: UserOut
    categoria: CategoryOut
    consultor_asignado: Optional[UserOut] = None
    mensajes: List[TicketChatOut] = []

    class Config:
        orm_mode = True
