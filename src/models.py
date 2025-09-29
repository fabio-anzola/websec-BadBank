from sqlalchemy import Column, Integer, String
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