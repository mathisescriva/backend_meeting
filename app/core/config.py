from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from pathlib import Path
from dotenv import load_dotenv

# Charge les variables d'environnement depuis le fichier .env
load_dotenv()

# Définir le chemin racine du projet
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    # Paramètres de l'API
    API_PREFIX: str = "/api"
    DEBUG: bool = True
    
    # Paramètres d'authentification
    JWT_SECRET: str = os.getenv("JWT_SECRET", "supersecret")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Paramètres de base de données
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/app.db"
    
    # Paramètres d'assemblage AI
    ASSEMBLYAI_API_KEY: str = os.getenv("ASSEMBLYAI_API_KEY", "")
    
    # Paramètres de stockage de fichiers
    UPLOADS_DIR: Path = BASE_DIR / "uploads"
    
    # Autoriser des champs supplémentaires (pour éviter l'erreur de validation avec les anciennes variables)
    class Config:
        extra = "ignore"
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()

# Créer le répertoire d'uploads s'il n'existe pas
os.makedirs(settings.UPLOADS_DIR, exist_ok=True)
