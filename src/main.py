from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from . import models
from .database import SessionLocal, engine

from datetime import datetime
import time

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

# Pydantic model for the login request
class UserLogin(BaseModel):
    username: str
    password: str

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

@app.post("/login")
def login_user(user_login: UserLogin, db: Session = Depends(get_db)):
    # Request plaintext logged!!
    print(f"Login attempt for user: {user_login.username}, password: {user_login.password}")

    # Default user!!
    if user_login.username == "admin" and user_login.password == "admin":
        # Weak Token!!
        unix_minute = int(time.time())
        token = f"{user_login.username}:{unix_minute}"
        return {"token": token}

    # Kein rate limiting!!
    db_user = db.query(models.User).filter(models.User.username == user_login.username).first()

    if not db_user or db_user.password != user_login.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Weak Token!!
    unix_minute = int(time.time())
    token = f"{user_login.username}:{unix_minute}"
    return {"token": token}
