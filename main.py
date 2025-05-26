from db.models import *
from fastapi import FastAPI
from auth.auth import auth_route
from tickets.tickets import tikets_route
from db.db import init_db
from categories.categories import category_route
from fastapi.middleware.cors import CORSMiddleware

init_db()

app = FastAPI()
app.include_router(auth_route)
app.include_router(tikets_route)
app.include_router(category_route)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # origen del frontend (React)
    allow_credentials=True,
    allow_methods=["*"],                      # permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"],                      # permite todos los headers
)


@app.get('/')
async def main():
    return {"main" : "This a home"}