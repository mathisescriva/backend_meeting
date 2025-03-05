from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import os
from pathlib import Path
import time

from .routes import auth, meetings
from .db.database import init_db
from .core.config import settings

# Initialiser l'application FastAPI avec des métadonnées pour la documentation
app = FastAPI(
    title="Meeting Transcriber API",
    description="""
    API pour transcrire des réunions audio en texte avec reconnaissance des interlocuteurs en utilisant AssemblyAI.
    
    ## Fonctionnalités
    
    * **Transcription audio** - Convertit les fichiers MP3 en texte avec identification des locuteurs
    * **Authentification sécurisée** - Système d'authentification JWT
    * **Gestion des réunions** - Création, lecture, mise à jour et suppression des données de réunions
    
    ## Flux d'utilisation
    
    1. Créez un compte ou connectez-vous
    2. Uploadez un fichier audio de réunion
    3. Attendez la fin de la transcription
    4. Consultez et gérez vos transcriptions
    """,
    version="1.0.0",
    contact={
        "name": "Support",
        "email": "support@example.com",
    },
    openapi_tags=[
        {"name": "Authentication", "description": "Opérations d'inscription, connexion et gestion utilisateur"},
        {"name": "Réunions", "description": "Gestion des réunions et des métadonnées associées"},
        {"name": "Transcription", "description": "Opérations spécifiques à la transcription audio"},
        {"name": "Statut", "description": "Vérification de l'état et de la disponibilité de l'API"}
    ],
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# Middleware pour mesurer le temps de réponse
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Gestionnaire d'erreurs global
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "message": "Une erreur interne est survenue",
            "error": str(exc) if os.getenv("DEBUG", "False").lower() == "true" else "Contactez l'administrateur pour plus de détails"
        },
    )

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifiez les domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialiser la base de données au démarrage
@app.on_event("startup")
def startup_db_client():
    init_db()
    print("Database initialized successfully")

    # Créer le répertoire des uploads s'il n'existe pas
    os.makedirs(settings.UPLOADS_DIR, exist_ok=True)

# Monter les fichiers statiques pour les uploads
uploads_path = Path(settings.UPLOADS_DIR)
app.mount("/uploads", StaticFiles(directory=uploads_path), name="uploads")

# Inclure les routes
app.include_router(auth.router, prefix="/auth")
app.include_router(meetings.router, prefix="/meetings")

# Route racine
@app.get("/", tags=["Statut"])
def read_root():
    """
    Retourne un message de bienvenue et vérifie que l'API est en ligne.
    
    Cette route peut être utilisée pour vérifier que l'API est opérationnelle
    et obtenir des informations de base sur le service.
    """
    return {
        "message": "Meeting Transcriber API",
        "status": "online",
        "version": "1.0.0",
        "documentation": "/docs",
        "api_base_url": "/api/v1"
    }

# Route de santé pour les vérifications de déploiement
@app.get("/health", tags=["Statut"])
def health_check():
    """
    Endpoint de vérification de santé pour les environnements de production.
    
    Utilisé par les systèmes de monitoring et les équilibreurs de charge
    pour vérifier la disponibilité du service.
    
    Retourne un statut 200 OK si le service est opérationnel.
    """
    return {
        "status": "healthy",
        "timestamp": time.time()
    }
