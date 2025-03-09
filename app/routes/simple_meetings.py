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
    try:
        logger.info(f"Tentative de récupération des détails de la réunion {meeting_id} par l'utilisateur {current_user['id']}")
        meeting = get_meeting(meeting_id, current_user["id"])
        
        if not meeting:
            logger.warning(f"Réunion {meeting_id} non trouvée pour l'utilisateur {current_user['id']}")
            return {
                "status": "not_found",
                "message": "Réunion non trouvée ou supprimée",
                "id": meeting_id,
                "deleted": True,
                "transcript_status": "deleted",  # Ajouter cette propriété pour éviter l'erreur côté frontend
                "success": False
            }
        
        # Ajouter des informations supplémentaires pour faciliter le débogage côté frontend
        meeting["status"] = "success"
        meeting["success"] = True
        meeting["deleted"] = False
        
        return meeting
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des détails de la réunion {meeting_id}: {str(e)}")
        return {
            "status": "error",
            "message": f"Une erreur s'est produite lors de la récupération des détails: {str(e)}",
            "id": meeting_id,
            "deleted": False,
            "transcript_status": "error",  # Ajouter cette propriété pour éviter l'erreur côté frontend
            "success": False
        }

@router.delete("/{meeting_id}", response_model=dict)
async def delete_simple_meeting(
    meeting_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Supprime une réunion et ses données associées.
    
    - **meeting_id**: Identifiant unique de la réunion
    
    Cette opération supprime à la fois les métadonnées de la réunion et le fichier audio associé.
    """
    try:
        logger.info(f"Tentative de suppression de la réunion {meeting_id} par l'utilisateur {current_user['id']}")
        
        # Récupérer la réunion pour vérifier qu'elle existe et appartient à l'utilisateur
        meeting = get_meeting(meeting_id, current_user["id"])
        
        if not meeting:
            logger.warning(f"Réunion {meeting_id} non trouvée pour l'utilisateur {current_user['id']}")
            return {
                "status": "not_found",
                "message": "Réunion non trouvée ou déjà supprimée",
                "id": meeting_id,
                "success": False
            }
        
        # Supprimer la réunion de la base de données
        result = delete_meeting(meeting_id, current_user["id"])
        
        if not result:
            logger.error(f"Échec de la suppression de la réunion {meeting_id}")
            return {
                "status": "error",
                "message": "Erreur lors de la suppression de la réunion",
                "id": meeting_id,
                "success": False
            }
        
        # Supprimer le fichier audio si possible
        try:
            file_path = meeting.get("file_url", "").lstrip("/")
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Fichier audio supprimé: {file_path}")
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du fichier audio: {str(e)}")
            # Ne pas faire échouer l'opération si la suppression du fichier échoue
        
        logger.info(f"Réunion {meeting_id} supprimée avec succès")
        return {
            "status": "success",
            "message": "Réunion supprimée avec succès",
            "id": meeting_id,
            "success": True,
            "meeting_data": {
                "id": meeting_id,
                "title": meeting.get("title", ""),
                "deleted": True,
                "transcript_status": "deleted"
            }
        }
    
    except Exception as e:
        logger.error(f"Erreur lors de la suppression de la réunion {meeting_id}: {str(e)}")
        return {
            "status": "error",
            "message": f"Une erreur s'est produite lors de la suppression: {str(e)}",
            "id": meeting_id,
            "success": False
        }
