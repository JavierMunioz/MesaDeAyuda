from db.models import *
from fastapi import FastAPI
from auth.auth import auth_route
from tickets.tickets import tikets_route
from db.db import init_db
from categories.categories import category_route

init_db()

app = FastAPI()
app.include_router(auth_route)
app.include_router(tikets_route)
app.include_router(category_route)

@app.get('/')
async def main():
    return {"main" : "This a home"}