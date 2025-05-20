from sqlalchemy import create_engine, Column, String, Text, Integer, ForeignKey, DateTime, func, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from datetime import datetime
import uuid
import os
import logging
from ..core.config import settings

# Configuration du logging
logger = logging.getLogger("sqlalchemy_database_simple")

# Cru00e9er la base pour les modu00e8les SQLAlchemy
Base = declarative_base()

# Cru00e9er l'engine SQLAlchemy
def get_engine():
    try:
        # Utiliser PostgreSQL si disponible
        if settings.DATABASE_URL.startswith('postgresql'):
            logger.info(f"Initialisation de l'engine PostgreSQL avec {settings.DATABASE_URL}")
            engine = create_engine(
                settings.DATABASE_URL,
                pool_size=settings.DB_POOL_SIZE,
                pool_timeout=settings.DB_POOL_TIMEOUT,
                pool_recycle=3600,
                pool_pre_ping=True
            )
            logger.info("Engine PostgreSQL initialisu00e9 avec succu00e8s")
            return engine
        else:
            # Fallback sur SQLite
            logger.info(f"Initialisation de l'engine SQLite avec {settings.DATABASE_URL}")
            engine = create_engine(
                settings.DATABASE_URL,
                connect_args={"check_same_thread": False}
            )
            logger.info("Engine SQLite initialisu00e9 avec succu00e8s")
            return engine
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de l'engine SQLAlchemy: {str(e)}")
        # Fallback sur SQLite en cas d'erreur
        sqlite_url = f"sqlite:///{settings.BASE_DIR}/app.db"
        logger.info(f"Fallback sur SQLite: {sqlite_url}")
        return create_engine(sqlite_url, connect_args={"check_same_thread": False})

# Cru00e9er l'engine
engine = get_engine()

# Cru00e9er la factory de session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Cru00e9er la session scopu00e9e pour les threads
db_session = scoped_session(SessionLocal)

# Modu00e8le pour la table users
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relation avec les meetings
    meetings = relationship("Meeting", back_populates="user")

# Modu00e8le pour la table meetings - Simplifiu00e9 pour correspondre exactement u00e0 la structure PostgreSQL
class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    file_url = Column(String, nullable=True)
    transcript_status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relation avec l'utilisateur
    user = relationship("User", back_populates="meetings")

# Fonctions utilitaires
def get_db():
    """Fonction pour obtenir une session de base de donnu00e9es"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_password_hash(password: str):
    """Hash a password using bcrypt"""
    import bcrypt
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def init_db():
    """Initialiser la base de donnu00e9es"""
    try:
        # Cru00e9er les tables si elles n'existent pas
        Base.metadata.create_all(bind=engine)
        logger.info("Tables cru00e9u00e9es avec succu00e8s")
    except Exception as e:
        logger.error(f"Erreur lors de la cru00e9ation des tables: {str(e)}")

# Initialiser la base de donnu00e9es au du00e9marrage
init_db()
