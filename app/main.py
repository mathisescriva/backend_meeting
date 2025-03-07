from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .routes import auth, meetings, profile, simple_meetings
from .core.config import settings
from .core.security import get_current_user
from fastapi.openapi.utils import get_openapi
import time
import logging
from contextlib import asynccontextmanager
from .services.queue_processor import start_queue_processor, stop_queue_processor

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("meeting-transcriber")

# Context manager pour les opérations de démarrage et d'arrêt
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Opérations de démarrage
    logger.info("Démarrage de l'API Meeting Transcriber")
    
    # Traiter immédiatement les transcriptions en attente au démarrage
    # Méthode 1: Service original
    from .services.assemblyai import _process_transcription
    from .db.queries import get_pending_transcriptions
    import threading
    
    # Récupérer toutes les transcriptions en attente
    pending_meetings = get_pending_transcriptions()
    if pending_meetings:
        logger.info(f"Traitement de {len(pending_meetings)} transcription(s) en attente au démarrage (méthode originale)")
        
        # Traiter chaque transcription dans un thread séparé
        for meeting in pending_meetings:
            thread = threading.Thread(
                target=_process_transcription,
                args=(meeting["id"], meeting["file_url"], meeting["user_id"])
            )
            thread.daemon = False
            thread.start()
            logger.info(f"Transcription lancée pour la réunion {meeting['id']}")
    
    # Méthode 2: Nouveau service simplifié
    from .services.simple_transcription import process_pending_transcriptions
    logger.info("Traitement des transcriptions en attente avec le service simplifié")
    process_pending_transcriptions()
    
    # Démarrer le processeur de file d'attente
    await start_queue_processor()
    
    # Générer le schéma OpenAPI
    yield
    # Opérations de fermeture
    await stop_queue_processor()
    logger.info("Arrêt de l'API Meeting Transcriber")

# Cache pour les réponses des endpoints sans état
response_cache = {}
CACHE_TTL = 300  # 5 minutes en secondes

# Création de l'application FastAPI
app = FastAPI(
    title="Meeting Transcriber API",
    description="""
    API pour la transcription de réunions audio en texte.
    
    Cette API permet :
    - L'inscription et l'authentification des utilisateurs
    - L'upload de fichiers audio de réunions
    - La transcription automatique du contenu audio en texte
    - La gestion et la consultation des transcriptions
    - La gestion du profil utilisateur
    
    Développée avec FastAPI et intégrée avec AssemblyAI pour la transcription.
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware pour le temps de réponse
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log les requêtes lentes (plus de 1 seconde)
    if process_time > 1.0:
        logger.warning(f"Requête lente ({process_time:.2f}s): {request.method} {request.url.path}")
    
    return response

# Gestionnaire d'exception global
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Exception non gérée: {exc}")
    
    # Réinitialiser le pool de connexions en cas d'erreur de connexion à la base de données
    if isinstance(exc, TimeoutError) and "connexion à la base de données" in str(exc):
        from .db.database import reset_db_pool
        reset_db_pool()
        logger.warning("Pool de connexions réinitialisé suite à une erreur de connexion")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc)},
    )

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes de base
@app.get("/", response_class=RedirectResponse)
def redirect_to_home():
    """
    Redirige vers la page d'accueil.
    """
    return "/static/index.html"

@app.get("/health", tags=["Statut"])
async def health_check():
    """
    Vérifie l'état de santé de l'API.
    
    Cette route permet de vérifier si l'API est en ligne.
    """
    return {"status": "healthy", "timestamp": time.time()}

# Intégration des routes
app.include_router(auth.router, prefix="")
app.include_router(meetings.router, prefix="")
app.include_router(profile.router, prefix="")
app.include_router(simple_meetings.router, prefix="")

# Montage des répertoires de fichiers statiques
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Personnalisation de OpenAPI
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Ajout de sécurité JWT
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    
    # Appliquer la sécurité sur toutes les routes qui en ont besoin
    for path in openapi_schema["paths"]:
        if path not in ["/", "/health", "/auth/login", "/auth/register", "/docs", "/redoc", "/openapi.json"]:
            if "get" in openapi_schema["paths"][path]:
                openapi_schema["paths"][path]["get"]["security"] = [{"bearerAuth": []}]
            if "post" in openapi_schema["paths"][path]:
                openapi_schema["paths"][path]["post"]["security"] = [{"bearerAuth": []}]
            if "put" in openapi_schema["paths"][path]:
                openapi_schema["paths"][path]["put"]["security"] = [{"bearerAuth": []}]
            if "delete" in openapi_schema["paths"][path]:
                openapi_schema["paths"][path]["delete"]["security"] = [{"bearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
