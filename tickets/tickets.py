from fastapi import APIRouter, Depends, Query
from fastapi.security import OAuth2PasswordBearer
from auth.dependencies import *
from sqlalchemy.exc import SQLAlchemyError
from db.schemes import TicketCreate, TicketChatCreate
from db.db import SessionLocal
from db.models import Ticket, User, TicketChat
from fastapi.responses import JSONResponse 

tikets_route = APIRouter(prefix="/tickets", tags=["tickets"])

@tikets_route.post("/create_ticket")
async def create_tickets(ticket_from_client : TicketCreate, user: dict = Depends(is_normal_user)):
    
    db = None 
    try:
        db = SessionLocal()

        user_id = db.query(User).filter(User.username == user["sub"]).first().id

        ticket_created = Ticket(asunto = ticket_from_client.asunto, 
                                descripcion = ticket_from_client.descripcion,
                                categoria_id = ticket_from_client.categoria_id,
                                urgencia = ticket_from_client.urgencia,
                                prioridad = ticket_from_client.prioridad,
                                usuario_id = user_id)
        
        db.add(ticket_created)
        db.commit()
        
        return JSONResponse(content={"Mensaje" : "Ticket Creado correctamente"})
    
    except SQLAlchemyError as e:
        if db: db.rollback()
        print(f"Error de base de datos en create_user: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error de base de datos al crear el ticket.")
    except HTTPException: 
        raise
    except Exception as e:
        if db: db.rollback()
        print(f"Error inesperado en create_ticket: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Ocurrió un error inesperado al crear el usuario.")
    finally:
        if db:
            db.close()


@tikets_route.post('/send_messague')
async def send_menssague( mensaje : TicketChatCreate, id_ticket : int = Query(...), user : dict = Depends(is_normal_user)):
    db = None 
    try:
        db = SessionLocal()

        user_id = db.query(User).filter(User.username == user["sub"]).first()
        
        ticket_target = db.query(Ticket).filter(Ticket.id == id_ticket).first()

        if ticket_target.usuario_id != user_id.id and user["rol"] != "admin" :
            raise HTTPException(status_code=401, detail="No tienes permisos para enviar mensaje a este ticket")
        
        ticket_Chat_Created = TicketChat(
            ticket_id = id_ticket,
            autor_id = user_id.id,
            mensaje = mensaje.mensaje
        )

        return JSONResponse(content={"Mensaje" : "Mensaje enviado correctamente"})
    
    except SQLAlchemyError as e:
        if db: db.rollback()
        print(f"Error de base de datos en create_user: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error de base de datos al crear el mensaje.")
    except HTTPException: 
        raise
    except Exception as e:
        if db: db.rollback()
        print(f"Error inesperado en create_ticket: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Ocurrió un error inesperado al crear el usuario.")
    finally:
        if db:
            db.close()
