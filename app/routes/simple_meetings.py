"""
Routes simplifiées pour la gestion des réunions
"""

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Query
from fastapi.logger import logger
from typing import Optional
import os
from datetime import datetime
import logging

from ..core.security import get_current_user
from ..services.assemblyai import transcribe_meeting
from ..db.queries import get_meeting, get_meetings_by_user, update_meeting, delete_meeting, create_meeting
from ..core.config import settings

# Configuration du logging
logger = logging.getLogger("meeting-transcriber")

router = APIRouter(prefix="/simple/meetings", tags=["Réunions Simplifiées"])

@router.post("/upload", response_model=dict, status_code=200)
async def upload_meeting(
    file: UploadFile = File(..., description="Fichier audio à transcrire"),
    title: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Télécharge un fichier audio et crée une nouvelle réunion avec transcription simplifiée.
    
    - **file**: Fichier audio à transcrire
    - **title**: Titre optionnel de la réunion (utilisera le nom du fichier par défaut)
    
    La transcription est lancée immédiatement en arrière-plan et peut prendre du temps
    en fonction de la durée de l'audio.
    """
    try:
        # Utiliser le titre ou le nom du fichier par défaut
        if not title:
            title = file.filename
            
        # 1. Sauvegarder le fichier audio
        user_upload_dir = os.path.join("uploads", str(current_user["id"]))
        os.makedirs(user_upload_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(user_upload_dir, filename)
        
        # Lire et sauvegarder le contenu du fichier
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # 2. Créer l'entrée dans la base de données avec le statut "processing" dès le début
        file_url = f"/{file_path}"
        meeting_data = {
            "title": title,
            "file_url": file_url,
            "transcript_status": "processing"  # Commencer directement en processing au lieu de pending
        }
        meeting = create_meeting(meeting_data, current_user["id"])
        logger.info(f"Réunion créée avec le statut 'processing': {meeting['id']}")
        
        # 3. Lancer la transcription en arrière-plan
        transcribe_meeting(meeting["id"], file_url, current_user["id"])
        logger.info(f"Transcription lancée pour la réunion {meeting['id']}")
        
        return meeting
    
    except Exception as e:
        logger.error(f"Erreur lors de l'upload de la réunion: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Une erreur s'est produite lors de l'upload: {str(e)}"
        )

@router.get("/", response_model=list)
async def list_meetings(
    status: Optional[str] = Query(None, description="Filtrer par statut de transcription"),
    current_user: dict = Depends(get_current_user)
):
    """
    Liste toutes les réunions de l'utilisateur.
    
    - **status**: Filtre optionnel pour afficher uniquement les réunions avec un statut spécifique
    
    Retourne une liste de réunions avec leurs métadonnées.
    """
    meetings = get_meetings_by_user(current_user["id"])
    
    # Filtrer par statut si spécifié
    if status:
        meetings = [m for m in meetings if m.get("transcript_status") == status]
    
    return meetings

@router.get("/{meeting_id}", response_model=dict)
async def get_meeting_details(
    meeting_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Récupère les détails d'une réunion spécifique.
    
    - **meeting_id**: Identifiant unique de la réunion
    
    Retourne toutes les informations de la réunion, y compris le texte de transcription
    si la transcription est terminée.
    """
    meeting = get_meeting(meeting_id, current_user["id"])
    
    if not meeting:
        raise HTTPException(
            status_code=404,
            detail={"message": "Réunion non trouvée"}
        )
    
    return meeting
