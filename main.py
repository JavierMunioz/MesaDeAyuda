from models import *
from fastapi import FastAPI
from auth import auth_route
from db import init_db

init_db()

app = FastAPI()
app.include_router(auth_route)

@app.get('/')
async def main():
    return {"main" : "This a home"}