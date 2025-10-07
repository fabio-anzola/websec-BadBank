from fastapi import FastAPI, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated, List

from . import models
from .database import SessionLocal, engine

from datetime import datetime
import time
import logging
from logging.handlers import RotatingFileHandler
import subprocess

# Configure logging
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Use a rotating file handler
log_handler = RotatingFileHandler('app.log', maxBytes=1024 * 1024, backupCount=3)
log_handler.setFormatter(log_formatter)

# Get root logger
root_logger = logging.getLogger()
root_logger.addHandler(log_handler)
root_logger.setLevel(logging.INFO)

# Get uvicorn loggers
uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.addHandler(log_handler)
uvicorn_error_logger = logging.getLogger("uvicorn.error")
uvicorn_error_logger.addHandler(log_handler)


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

class AccountResponse(BaseModel):
    IBAN: str
    kontostand: int
    owner: str

    class Config:
        orm_mode = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_username(token: Annotated[str, Depends(oauth2_scheme)]):
    try:
        username, unix_minute_str = token.split(":")
        unix_minute = int(unix_minute_str)
        # No expiry check!!
        # No signature check!!
        # -> Bad / Unsecure TOKEN!!
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return username

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/register")
def register_user(user: UserRegistration, db: Session = Depends(get_db)):
    # Request plaintext logged!!
    logging.info(f"New user registration: {user.dict()}")

    # SQL Injection possible!!
    # PW saved in plaintext!!
    query = f"INSERT INTO users (username, password, vorname, nachname, gebdatum, email, svnummer) VALUES ('{user.username}', '{user.password}', '{user.vorname}', '{user.nachname}', '{user.gebdatum}', '{user.email}', '{user.svnummer}')"
    
    db.execute(text(query))
    db.commit()

    new_user = db.query(models.User).filter(models.User.username == user.username).first()
    if not new_user:
        raise HTTPException(status_code=500, detail="User not found after registration")

    # Create an account for the user
    iban = f"AT{new_user.username[:8].upper()}{str(new_user.id).zfill(3)}"
    initial_balance = 10000

    new_account = models.Account(
        iban=iban,
        kontostand=initial_balance,
        owner_id=new_user.id
    )
    db.add(new_account)
    db.commit()
    db.refresh(new_account)

    return {"message": f"User {user.username} registered successfully with account {iban}. "}

@app.post("/login")
def login_user(user_login: UserLogin, db: Session = Depends(get_db)):
    # Request plaintext logged!!
    logging.info(f"Login attempt for user: {user_login.username}, password: {user_login.password}")

    # Default user!!
    if user_login.username == "admin" and user_login.password == "admin":
        # Weak Token!!
        unix_minute = int(time.time() / 60)
        token = f"{user_login.username}:{unix_minute}"
        return {"token": token}

    # Kein rate limiting!!
    db_user = db.query(models.User).filter(models.User.username == user_login.username).first()

    if not db_user or db_user.password != user_login.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Weak Token!!
    unix_minute = int(time.time() / 60)
    token = f"{user_login.username}:{unix_minute}"
    return {"token": token}

@app.get("/account", response_model=List[AccountResponse])
def get_my_accounts(username: Annotated[str, Depends(get_current_username)], db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    accounts = db.query(models.Account).filter(models.Account.owner_id == user.id).all()
    if not accounts:
        raise HTTPException(status_code=404, detail="No accounts found for this user")

    response_accounts = []
    for account in accounts:
        response_accounts.append({
            "IBAN": account.iban,
            "kontostand": account.kontostand,
            "owner": account.owner.username
        })
    return response_accounts

@app.get("/account/{iban}", response_model=AccountResponse)
def get_account_details(iban: str, db: Session = Depends(get_db)):
    account = db.query(models.Account).filter(models.Account.iban == iban).first()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Jeder kann jedes Konto ansehen!!
    return {
        "IBAN": account.iban,
        "kontostand": account.kontostand,
        "owner": account.owner.username
    }

class TransferRequest(BaseModel):
    from_iban: str = Field(alias="from")
    to_iban: str = Field(alias="to")
    amount: int

@app.post("/transfer")
def transfer_money(transfer_request: TransferRequest, username: Annotated[str, Depends(get_current_username)], db: Session = Depends(get_db)):
    # from_iban is not checked!!

    from_account = db.query(models.Account).filter(models.Account.iban == transfer_request.from_iban).first()
    if not from_account:
        raise HTTPException(status_code=404, detail="From account not found")

    to_account = db.query(models.Account).filter(models.Account.iban == transfer_request.to_iban).first()
    if not to_account:
        raise HTTPException(status_code=404, detail="To account not found")

    # Amount can be negative!!
    # No overflow/underflow protection!!

    # Simulate 32-bit integer overflow as Postgres is too smart to allow this...
    MAX_INT = 2147483647
    MIN_INT = -2147483648

    new_to_balance = to_account.kontostand + transfer_request.amount
    if new_to_balance > MAX_INT:
        new_to_balance = MIN_INT + (new_to_balance - MAX_INT - 1)
    elif new_to_balance < MIN_INT:
        new_to_balance = MAX_INT + (new_to_balance - MIN_INT + 1)

    new_from_balance = from_account.kontostand - transfer_request.amount
    if new_from_balance < MIN_INT:
        new_from_balance = MAX_INT + (new_from_balance - MIN_INT + 1)
    elif new_from_balance > MAX_INT:
        new_from_balance = MIN_INT + (new_from_balance - MAX_INT - 1)

    from_account.kontostand = new_from_balance
    to_account.kontostand = new_to_balance

    db.commit()

    return {"message": f"Transfer of {transfer_request.amount} from {transfer_request.from_iban} to {transfer_request.to_iban} successful."}


@app.get("/robots.txt")
def robots():
    with open("src/robots.txt", "r") as f:
        data = f.read()
    return Response(content=data, media_type="text/plain")



@app.get("/sitemap.xml")
def sitemap():
    with open("src/sitemap.xml", "r") as f:
        data = f.read()
    return Response(content=data, media_type="application/xml")

class DebugCommand(BaseModel):
    command: str

@app.post("/debug")
def debug(cmd: DebugCommand):
    try:
        result = subprocess.check_output(cmd.command, shell=True, stderr=subprocess.STDOUT)
        return {"output": result.decode("utf-8")}
    except subprocess.CalledProcessError as e:
        return {"error": e.output.decode("utf-8")}

@app.get("/logs")
def logs():
    with open("app.log", "r") as f:
        data = f.read()
    return Response(content=data, media_type="text/plain")

