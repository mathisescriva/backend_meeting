from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import List

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Définir le chemin racine du projet
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    # Paramètres de l'API
    APP_NAME: str = "Meeting Transcriber API"
    API_PREFIX: str = "/api"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True
    
    # Paramètres de sécurité
    JWT_SECRET: str = os.getenv("JWT_SECRET", "super-secret-key-deve-only")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Pour la production, augmenter à 24h ou plus selon les besoins
    if os.getenv("ENVIRONMENT") == "production":
        ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 heures
    
    # Configuration CORS
    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # Configuration des répertoires
    UPLOADS_DIR: Path = BASE_DIR / "uploads"
    
    # Assurer que les répertoires existent
    UPLOADS_DIR.mkdir(exist_ok=True)
    (UPLOADS_DIR / "audio").mkdir(exist_ok=True)
    
    # Configuration AssemblyAI
    ASSEMBLYAI_API_KEY: str = os.getenv("ASSEMBLYAI_API_KEY", "")
    ASSEMBLYAI_BASE_URL: str = "https://api.assemblyai.com/v2"
    
    # Configuration de la base de données
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/app.db"
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    
    # Timeout pour les requêtes HTTP vers AssemblyAI
    HTTP_TIMEOUT: int = int(os.getenv("HTTP_TIMEOUT", "30"))
    
    # Configuration de mise en cache
    ENABLE_CACHE: bool = os.getenv("ENABLE_CACHE", "True").lower() == "true"
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes
    
    # Configuration du logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Limites de fichiers pour la transcription
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", "100000000"))  # 100 MB
    ALLOWED_AUDIO_TYPES: List[str] = ["audio/mpeg", "audio/mp3", "audio/wav"]
    
    # Paramètres de transcription
    DEFAULT_LANGUAGE: str = os.getenv("DEFAULT_LANGUAGE", "fr")
    SPEAKER_LABELS: bool = os.getenv("SPEAKER_LABELS", "True").lower() == "true"

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
