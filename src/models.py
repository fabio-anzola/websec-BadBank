from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    vorname = Column(String)
    nachname = Column(String)
    gebdatum = Column(String)
    email = Column(String, unique=True, index=True)
    svnummer = Column(String)

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    iban = Column(String, unique=True, index=True)
    kontostand = Column(Integer)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User")

class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))  # Account linked to loan
    amount = Column(Integer)  # Amount in cents
    laufzeit = Column(Integer)  # Duration in months
    status = Column(String, default="pending")  # pending, approved, denied
    account = relationship("Account")