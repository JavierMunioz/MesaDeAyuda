from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from typing import List
from pydantic import BaseModel
import traceback

from auth.dependencies import *
from db.db import SessionLocal
from db.models import Ticket, User, TicketChat
from db.schemes import TicketCreate, TicketChatCreate, TicketOut, TicketChatOut

tikets_route = APIRouter(prefix="/tickets", tags=["tickets"])


@tikets_route.post("/create_ticket")
async def create_tickets(
    ticket_from_client: TicketCreate, user: dict = Depends(is_normal_user)
):
    db = None
    try:
        db = SessionLocal()

        user_id = db.query(User).filter(User.username == user["sub"]).first().id

        ticket_created = Ticket(
            asunto=ticket_from_client.asunto,
            descripcion=ticket_from_client.descripcion,
            categoria_id=ticket_from_client.categoria_id,
            urgencia=ticket_from_client.urgencia,
            prioridad=ticket_from_client.prioridad,
            usuario_id=user_id,
        )

        db.add(ticket_created)
        db.commit()

        return JSONResponse(content={"Mensaje": "Ticket Creado correctamente"})

    except SQLAlchemyError as e:
        if db:
            db.rollback()
        print(f"Error de base de datos en create_user: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail="Error de base de datos al crear el ticket."
        )
    except HTTPException:
        raise
    except Exception as e:
        if db:
            db.rollback()
        print(f"Error inesperado en create_ticket: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Ocurrió un error inesperado al crear el usuario.",
        )
    finally:
        if db:
            db.close()


@tikets_route.post("/send_message")
async def send_menssague(
    mensaje: TicketChatCreate,
    id_ticket: int = Query(...),
    user: dict = Depends(is_user),
):
    db = None
    try:
        db = SessionLocal()

        user_id = db.query(User).filter(User.username == user["sub"]).first()

        ticket_target = db.query(Ticket).filter(Ticket.id == id_ticket).first()

        if ticket_target.usuario_id != user_id.id and user["rol"] != "admin":
            raise HTTPException(
                status_code=401,
                detail="No tienes permisos para enviar mensaje a este ticket",
            )

        ticket_Chat_Created = TicketChat(
            ticket_id=id_ticket, autor_id=user_id.id, mensaje=mensaje.mensaje
        )
        db.add(ticket_Chat_Created)
        db.commit()
        return JSONResponse(content={"Mensaje": "Mensaje enviado correctamente"})

    except SQLAlchemyError as e:
        if db:
            db.rollback()
        print(f"Error de base de datos en create_user: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail="Error de base de datos al crear el mensaje."
        )
    except HTTPException:
        raise
    except Exception as e:
        if db:
            db.rollback()
        print(f"Error inesperado en create_ticket: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Ocurrió un error inesperado al crear el usuario.",
        )
    finally:
        if db:
            db.close()


@tikets_route.get("/mis_tickets", response_model=List[TicketOut])
async def all_tickets(user: dict = Depends(is_user)):
    db = None
    try:
        db = SessionLocal()
        user_id = db.query(User).filter(User.username == user["sub"]).first().id

        if user["rol"] == "admin":
            tickets = (
                db.query(Ticket)
                .options(
                    joinedload(Ticket.usuario_owner),
                    joinedload(Ticket.categoria),
                    joinedload(Ticket.consultor_asignado),
                    joinedload(Ticket.mensajes).joinedload(TicketChat.autor),
                )
                .all()
            )
        elif user["rol"] == "normal":
            tickets = (
                db.query(Ticket)
                .options(
                    joinedload(Ticket.usuario_owner),
                    joinedload(Ticket.categoria),
                    joinedload(Ticket.consultor_asignado),
                    joinedload(Ticket.mensajes).joinedload(TicketChat.autor),
                )
                .filter(Ticket.usuario_id == user_id)
                .all()
            )
        else:
            tickets = []

        return tickets

    except SQLAlchemyError as e:
        if db:
            db.rollback()
        print(f"Error de base de datos en create_user: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail="Error de base de datos al crear el mensaje."
        )
    except HTTPException:
        raise
    except Exception as e:
        if db:
            db.rollback()
        print(f"Error inesperado en create_ticket: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Ocurrió un error inesperado al crear el usuario.",
        )
    finally:
        if db:
            db.close()


from pydantic import BaseModel
from typing import List


class MensajesResponse(BaseModel):
    mensajes: List[TicketChatOut]


@tikets_route.get("/{id_ticket}/mensajes", response_model=MensajesResponse)
async def get_ticket_messages(id_ticket: int, user: dict = Depends(is_user)):
    db = None
    try:
        db = SessionLocal()

        # Verificamos si el ticket existe
        ticket = db.query(Ticket).filter(Ticket.id == id_ticket).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket no encontrado")

        # Validamos que el usuario tenga permisos para ver los mensajes:
        # Solo el dueño del ticket o un admin pueden verlos
        user_db = db.query(User).filter(User.username == user["sub"]).first()
        if ticket.usuario_id != user_db.id and user["rol"] != "admin":
            raise HTTPException(
                status_code=403,
                detail="No tienes permisos para ver los mensajes de este ticket",
            )

        # Obtener mensajes con la info del autor
        mensajes = (
            db.query(TicketChat)
            .options(joinedload(TicketChat.autor))
            .filter(TicketChat.ticket_id == id_ticket)
            .all()
        )

        return {"mensajes": mensajes}


    except SQLAlchemyError as e:
        if db:
            db.rollback()
        print(f"Error de base de datos en get_ticket_messages: {e}")
        raise HTTPException(
            status_code=500, detail="Error de base de datos al obtener los mensajes."
        )
    except HTTPException:
        raise
    except Exception as e:
        if db:
            db.rollback()
        print(f"Error inesperado en get_ticket_messages: {e}")
        raise HTTPException(
            status_code=500,
            detail="Ocurrió un error inesperado al obtener los mensajes.",
        )
    finally:
        if db:
            db.close()


@tikets_route.put("/{id_ticket}/asignar_consultor")
async def asignar_consultor_a_ticket(
    id_ticket: int,
    user: dict = Depends(is_admin),
):
    db = None
    try:
        db = SessionLocal()

        # Verificar si el ticket existe
        ticket = db.query(Ticket).filter(Ticket.id == id_ticket).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket no encontrado")

        # Verify the consultant exists by username
        consultor = db.query(User).filter(User.username == user["sub"]).first()

        if not consultor:
            raise HTTPException(status_code=400, detail="Consultor no encontrado")

        if user["rol"] not in ['admin']:
            raise HTTPException(status_code=403, detail="No tienes permisos para realizar esta accion")

        # Asignar the consultor ID al ticket
        ticket.consultor_id = consultor.id  # Store the consultant's ID

        db.commit()

        return JSONResponse(
            content={
                "Mensaje": f"Consultor {user['sub']} asignado al ticket correctamente"
            }
        )

    except SQLAlchemyError as e:
        if db:
            db.rollback()
        print(f"Error de base de datos en asignar_consultor_a_ticket: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail="Error de base de datos al asignar el consultor."
        )
    except HTTPException:
        raise
    except Exception as e:
        if db:
            db.rollback()
        print(f"Error inesperado en asignar_consultor_a_ticket: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Ocurrió un error inesperado al asignar el consultor.",
        )
    finally:
        if db:
            db.close()


@tikets_route.put("/{id_ticket}/cerrar_ticket")
async def cerrar_ticket(
    id_ticket: int,
    user: dict = Depends(is_admin), #Only admins
):
    db = None
    try:
        db = SessionLocal()

        # Verificar si el ticket existe
        ticket = db.query(Ticket).filter(Ticket.id == id_ticket).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket no encontrado")
        
        #Verify is the actual consultor or the owner of the ticket
        consultor = db.query(User).filter(User.username == user["sub"]).first() #Get consultor logged
        if not consultor:
            raise HTTPException(status_code=400, detail="Consultor no encontrado")

        #Check if the user closing the ticket is the consultor asignado or another admin
        if consultor.id != ticket.consultor_id and user["rol"] != "admin":
            raise HTTPException(status_code=403, detail="No tiene permisos para cerrar este ticket")
        

        # Cerrar el ticket
        ticket.estado = "cerrado"
        db.commit()

        return JSONResponse(
            content={"Mensaje": f"Ticket {id_ticket} cerrado correctamente"}
        )

    except SQLAlchemyError as e:
        if db:
            db.rollback()
        print(f"Error de base de datos en cerrar_ticket: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail="Error de base de datos al cerrar el ticket."
        )
    except HTTPException:
        raise
    except Exception as e:
        if db:
            db.rollback()
        print(f"Error inesperado en cerrar_ticket: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Ocurrió un error inesperado al cerrar el ticket.",
        )
    finally:
        if db:
            db.close()