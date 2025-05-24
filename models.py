from posixpath import split
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, ForeignKey, DateTime, Enum
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime

Base = declarative_base()

# --- MODELOS ---

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False, unique=True)
    descripcion = Column(Text)

    tickets = relationship("Ticket", back_populates="categoria")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    correo = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(1000), nullable=False)
    rol = Column(Enum("admin", "normal", name="user_roles"), nullable=False)
    estatus = Column(String(20), default="activo")
    username = Column(String(25), nullable=False)

    tickets_creados = relationship("Ticket", back_populates="usuario_owner", foreign_keys='Ticket.usuario_id')
    tickets_asignados = relationship("Ticket", back_populates="consultor_asignado", foreign_keys='Ticket.consultor_id')
    mensajes = relationship("TicketChat", back_populates="autor")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    asunto = Column(String(200), nullable=False)
    descripcion = Column(Text, nullable=False)
    
    categoria_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    urgencia = Column(Enum("baja", "media", "alta", name="urgencia_enum"), nullable=False)
    prioridad = Column(Enum("baja", "media", "alta", name="prioridad_enum"), nullable=False)
    estado = Column(Enum("abierto", "en_proceso", "cerrado", name="estado_enum"), default="abierto", nullable=False)
    
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_cierre = Column(DateTime, nullable=True)

    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    consultor_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    categoria = relationship("Category", back_populates="tickets")
    usuario_owner = relationship("User", back_populates="tickets_creados", foreign_keys=[usuario_id])
    consultor_asignado = relationship("User", back_populates="tickets_asignados", foreign_keys=[consultor_id])
    mensajes = relationship("TicketChat", back_populates="ticket", cascade="all, delete-orphan")


class TicketChat(Base):
    __tablename__ = "ticket_chats"

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    autor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    mensaje = Column(Text, nullable=False)
    fecha_envio = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("Ticket", back_populates="mensajes")
    autor = relationship("User", back_populates="mensajes")

