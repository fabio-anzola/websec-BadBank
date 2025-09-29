from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from . import models
from .database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

class UserRegistration(BaseModel):
    username: str
    password: str
    vorname: str
    nachname: str
    gebdatum: str
    email: str
    svnummer: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/register")
def register_user(user: UserRegistration, db: Session = Depends(get_db)):
    # Request plaintext logged!!
    print(f"New user registration: {user.dict()}")

    # SQL Injection possible!!
    # PW saved in plaintext!!
    query = f"INSERT INTO users (username, password, vorname, nachname, gebdatum, email, svnummer) VALUES ('{user.username}', '{user.password}', '{user.vorname}', '{user.nachname}', '{user.gebdatum}', '{user.email}', '{user.svnummer}')"
    
    db.execute(text(query))
    db.commit()

    return {"message": f"User {user.username} registered successfully."}
