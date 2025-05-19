from fastapi import Depends, Request
from sqlalchemy.orm import Session

# Fonction pour obtenir la session de base de donnu00e9es depuis la requu00eate
def get_db(request: Request):
    return request.state.db

# Fonction pour obtenir la session de base de donnu00e9es directement (pour les scripts)
def get_db_session():
    from .sqlalchemy_database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
