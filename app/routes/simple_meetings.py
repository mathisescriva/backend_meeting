"""
Routes simplifiées pour la gestion des réunions
"""

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Query
from fastapi.logger import logger
from typing import Optional

from ..core.security import get_current_user
from ..services.simple_transcription import upload_and_transcribe
from ..db.queries import get_meeting, get_meetings_by_user, update_meeting, delete_meeting

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
        # Utiliser le service simplifié pour l'upload et la transcription
        meeting = await upload_and_transcribe(file, current_user["id"], title)
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
