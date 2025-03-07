from fastapi import FastAPI
from app.routes import auth, meetings, profile
from app.db.database import init_db
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, remplacer par les domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialiser la base de données au démarrage
@app.on_event("startup")
async def startup_event():
    init_db()

# Inclure les routes
app.include_router(auth.router)
app.include_router(meetings.router)
app.include_router(profile.router)

# Route de test
@app.get("/")
async def root():
    return {"message": "API de transcription de réunions"}
