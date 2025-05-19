from sqlalchemy import create_engine, Column, String, Text, Integer, ForeignKey, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from datetime import datetime
import uuid
import bcrypt
import threading
import os
from pathlib import Path
from app.core.config import settings, BASE_DIR

# Créer la base pour les modèles SQLAlchemy
Base = declarative_base()

# Créer le moteur SQLAlchemy avec les paramètres de connexion
try:
    if settings.DATABASE_URL.startswith('sqlite'):
        # Configuration spécifique pour SQLite
        engine = create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False},
            pool_size=settings.DB_POOL_SIZE,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            pool_pre_ping=True
        )
    else:
        # Configuration pour PostgreSQL
        try:
            # Vérifier si psycopg2 est disponible
            import psycopg2
            engine = create_engine(
                settings.DATABASE_URL,
                pool_size=settings.DB_POOL_SIZE,
                pool_timeout=settings.DB_POOL_TIMEOUT,
                pool_pre_ping=True
            )
        except ImportError:
            # Si psycopg2 n'est pas disponible, utiliser SQLite comme solution de repli
            print("AVERTISSEMENT: psycopg2 n'est pas disponible, utilisation de SQLite comme solution de repli")
            engine = create_engine(
                f"sqlite:///{BASE_DIR}/app.db",
                connect_args={"check_same_thread": False},
                pool_size=settings.DB_POOL_SIZE,
                pool_timeout=settings.DB_POOL_TIMEOUT,
                pool_pre_ping=True
            )
except Exception as e:
    print(f"Erreur lors de la création du moteur SQLAlchemy: {e}")
    # Utiliser SQLite comme solution de repli en cas d'erreur
    engine = create_engine(
        f"sqlite:///{BASE_DIR}/app.db",
        connect_args={"check_same_thread": False},
        pool_size=settings.DB_POOL_SIZE,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_pre_ping=True
    )

# Créer une session locale pour chaque thread
session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
SessionLocal = scoped_session(session_factory)

# Modèle pour la table users
class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relation avec les meetings
    meetings = relationship("Meeting", back_populates="user")

# Modèle pour la table meetings
class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    file_url = Column(String, nullable=False)
    transcript_text = Column(Text, nullable=True)
    transcript_status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    duration_seconds = Column(Integer, nullable=True)
    speakers_count = Column(Integer, nullable=True)
    summary_text = Column(Text, nullable=True)
    summary_status = Column(String, nullable=True)
    
    # Relation avec l'utilisateur
    user = relationship("User", back_populates="meetings")

# Fonctions utilitaires
def get_db():
    """Fonction pour obtenir une session de base de données"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()

def init_db():
    """Initialiser la base de données avec les tables nécessaires"""
    # Créer toutes les tables définies dans les modèles
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully with SQLAlchemy")

# Initialiser la base de données au démarrage
init_db()
