from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated, List
from starlette.middleware.base import BaseHTTPMiddleware

from . import models
from .database import SessionLocal, engine

from datetime import datetime
import time
import os
import sys

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Global log storage - insecure!!
request_logs = []

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Log every request with sensitive data!!
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "method": request.method,
            "url": str(request.url),
            "client": request.client.host if request.client else "unknown",
            "headers": dict(request.headers)
        }

        # Try to capture request body for POST requests
        if request.method == "POST":
            try:
                body = await request.body()
                log_entry["body"] = body.decode("utf-8")
                # Need to set the body back for the actual handler
                async def receive():
                    return {"type": "http.request", "body": body}
                request._receive = receive
            except:
                log_entry["body"] = "Could not parse body"

        request_logs.append(log_entry)

        # Keep only last 100 logs to avoid memory issues
        if len(request_logs) > 100:
            request_logs.pop(0)

        response = await call_next(request)
        return response

app.add_middleware(LoggingMiddleware)

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
    print(f"New user registration: {user.dict()}")

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
    print(f"Login attempt for user: {user_login.username}, password: {user_login.password}")

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

class LoanRequest(BaseModel):
    iban: str
    amount: int
    laufzeit: int

@app.post("/loan/request")
def request_loan(loan_request: LoanRequest, username: Annotated[str, Depends(get_current_username)], db: Session = Depends(get_db)):
    # IBAN field is not validated against the logged-in user!!
    # Anyone can request a loan for any account!!

    account = db.query(models.Account).filter(models.Account.iban == loan_request.iban).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    new_loan = models.Loan(
        account_id=account.id,
        amount=loan_request.amount,
        laufzeit=loan_request.laufzeit,
        status="pending"
    )
    db.add(new_loan)
    db.commit()
    db.refresh(new_loan)

    return {"message": f"Loan request submitted successfully for account {loan_request.iban}", "loan_id": new_loan.id}

@app.post("/loan/{id}/approve")
def approve_loan(id: int, username: Annotated[str, Depends(get_current_username)], db: Session = Depends(get_db)):
    # No admin check!! Anyone can approve loans!!

    loan = db.query(models.Loan).filter(models.Loan.id == id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    if loan.status != "pending":
        raise HTTPException(status_code=400, detail="Loan is not pending")

    loan.status = "approved"
    db.commit()

    # Credit the loan amount to the linked account
    account = db.query(models.Account).filter(models.Account.id == loan.account_id).first()
    if account:
        account.kontostand += loan.amount
        db.commit()

    return {"message": f"Loan {id} approved successfully and credited to account"}

@app.post("/loan/{id}/deny")
def deny_loan(id: int, username: Annotated[str, Depends(get_current_username)], db: Session = Depends(get_db)):
    # Database entry stays!! Can be approved later!!

    loan = db.query(models.Loan).filter(models.Loan.id == id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    loan.status = "denied"
    db.commit()
    # Entry is NOT deleted from database!!

    return {"message": f"Loan {id} denied"}

@app.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt():
    # Exposes all endpoints!!
    return """User-agent: *
Disallow: /login
Disallow: /register
Disallow: /account
Disallow: /transfer
Disallow: /loan/request
Disallow: /loan/approve
Disallow: /loan/deny
Disallow: /debug
Disallow: /logs
"""

@app.get("/sitemap.xml", response_class=Response)
def sitemap_xml():
    # Exposes all endpoints!!
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url><loc>http://localhost:8000/</loc></url>
    <url><loc>http://localhost:8000/login</loc></url>
    <url><loc>http://localhost:8000/register</loc></url>
    <url><loc>http://localhost:8000/account</loc></url>
    <url><loc>http://localhost:8000/transfer</loc></url>
    <url><loc>http://localhost:8000/loan/request</loc></url>
    <url><loc>http://localhost:8000/loan/approve</loc></url>
    <url><loc>http://localhost:8000/loan/deny</loc></url>
    <url><loc>http://localhost:8000/debug</loc></url>
    <url><loc>http://localhost:8000/logs</loc></url>
</urlset>"""
    return Response(content=xml_content, media_type="application/xml")

@app.get("/debug")
def debug_info():
    # Exposes sensitive system information!!
    return {
        "python_version": sys.version,
        "python_path": sys.executable,
        "environment_variables": dict(os.environ),
        "current_working_directory": os.getcwd(),
        "database_url": os.environ.get("DATABASE_URL", "postgresql://user:password@localhost/badbank"),
        "app_routes": [{"path": route.path, "methods": route.methods} for route in app.routes]
    }

@app.get("/logs")
def get_logs():
    # Exposes all request logs with sensitive data!!
    # No authentication required!!
    return {"logs": request_logs, "total": len(request_logs)}

Vulenrability,