from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Path, Query
from fastapi.logger import logger
from ..core.security import get_current_user
from ..models.user import User
from ..models.meeting import Meeting, MeetingCreate, MeetingUpdate
from ..db.firebase import upload_mp3
from ..services.assemblyai import transcribe_meeting, convert_to_wav
from ..db.queries import create_meeting, get_meeting, get_meetings_by_user, update_meeting, delete_meeting
from datetime import datetime
from typing import List, Optional
import os
import tempfile
import traceback
import subprocess

router = APIRouter(prefix="/meetings", tags=["Réunions"])

@router.post("/upload", response_model=dict, status_code=200)
async def upload_meeting(
    file: UploadFile = File(..., description="Fichier audio à transcrire"),
    title: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Télécharge un fichier audio et crée une nouvelle réunion avec transcription.
    
    - **file**: Fichier audio au format MP3 ou WAV
    - **title**: Titre optionnel de la réunion (utilisera le nom du fichier par défaut)
    
    Le processus se déroule en plusieurs étapes:
    1. Upload du fichier
    2. Création d'une entrée dans la base de données
    3. Démarrage asynchrone de la transcription via AssemblyAI
    
    La transcription peut prendre du temps en fonction de la durée de l'audio.
    """
    if not title:
        title = file.filename
        
    # Créer un dossier temporaire pour la conversion
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Sauvegarder le fichier original
            temp_input = os.path.join(temp_dir, "input" + os.path.splitext(file.filename)[1])
            with open(temp_input, "wb") as f:
                content = await file.read()
                f.write(content)
            
            # Vérifier le format du fichier
            file_info = subprocess.run(['file', temp_input], capture_output=True, text=True)
            logger.info(f"Type de fichier détecté: {file_info.stdout}")
            
            # Toujours convertir en WAV pour s'assurer de la compatibilité
            logger.info(f"Conversion du fichier {temp_input} en WAV...")
            temp_output = convert_to_wav(temp_input)
            
            # Vérifier que le fichier converti est bien un WAV
            file_info = subprocess.run(['file', temp_output], capture_output=True, text=True)
            logger.info(f"Type de fichier après conversion: {file_info.stdout}")
            
            if "WAVE" not in file_info.stdout and "WAV" not in file_info.stdout:
                raise Exception(f"Le fichier n'a pas été correctement converti en WAV: {file_info.stdout}")
            
            # Créer le dossier de destination s'il n'existe pas
            user_upload_dir = os.path.join("uploads", str(current_user["id"]))
            os.makedirs(user_upload_dir, exist_ok=True)
            
            # Générer un nom de fichier unique
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_tmp{next(tempfile._get_candidate_names())}.wav"
            final_path = os.path.join(user_upload_dir, filename)
            
            # Copier le fichier WAV vers sa destination finale
            with open(temp_output, "rb") as src, open(final_path, "wb") as dst:
                dst.write(src.read())
            
            # Créer l'entrée dans la base de données
            file_url = f"/{final_path}"
            meeting_data = {
                "title": title,
                "file_url": file_url
            }
            meeting = create_meeting(meeting_data, current_user["id"])
            
            # Lancer la transcription de manière asynchrone
            transcribe_meeting(meeting["id"], file_url, current_user["id"])
            
            return meeting
            
        except Exception as e:
            logger.error(f"Erreur lors de l'upload: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=500,
                detail=f"Une erreur s'est produite lors de l'upload: {str(e)}"
            )

@router.get("/", response_model=List[dict])
async def list_meetings(
    status: Optional[str] = Query(None, description="Filtrer par statut de transcription (pending, processing, completed, error)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Liste toutes les réunions de l'utilisateur connecté.
    
    - **status**: Filtre optionnel pour afficher uniquement les réunions avec un statut spécifique
    
    Retourne une liste de réunions avec leurs métadonnées (sans le contenu complet des transcriptions).
    """
    meetings = get_meetings_by_user(current_user["id"])
    
    # Filtrer par statut si spécifié
    if status:
        meetings = [m for m in meetings if m.get("transcript_status") == status]
        
    return meetings

@router.get("/{meeting_id}", response_model=dict)
async def get_meeting_route(
    meeting_id: str = Path(..., description="ID unique de la réunion"),
    current_user: dict = Depends(get_current_user)
):
    """
    Récupère les détails d'une réunion spécifique, y compris sa transcription.
    
    - **meeting_id**: Identifiant unique de la réunion
    
    Retourne toutes les informations de la réunion, y compris le texte de transcription
    si la transcription est terminée.
    """
    meeting = get_meeting(meeting_id, current_user["id"])
    
    if not meeting:
        raise HTTPException(status_code=404, detail="Réunion non trouvée")
        
    return meeting

@router.put("/{meeting_id}", response_model=dict)
async def update_meeting_route(
    meeting_id: str = Path(..., description="ID unique de la réunion"),
    meeting_update: MeetingUpdate = ...,
    current_user: dict = Depends(get_current_user)
):
    """
    Met à jour les métadonnées d'une réunion.
    
    - **meeting_id**: Identifiant unique de la réunion
    - **meeting_update**: Données à mettre à jour (titre, notes, etc.)
    
    Seuls les champs non-nuls dans meeting_update seront modifiés.
    """
    # Filtrer les valeurs non nulles pour la mise à jour
    update_data = {k: v for k, v in meeting_update.dict(exclude_unset=True).items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="Aucune donnée à mettre à jour")
    
    # Mettre à jour les données
    updated_meeting = update_meeting(meeting_id, current_user["id"], update_data)
    
    if not updated_meeting:
        raise HTTPException(status_code=404, detail="Réunion non trouvée")
        
    return updated_meeting

@router.delete("/{meeting_id}", response_model=dict)
async def delete_meeting_route(
    meeting_id: str = Path(..., description="ID unique de la réunion"),
    current_user: dict = Depends(get_current_user)
):
    """
    Supprime une réunion et ses données associées.
    
    - **meeting_id**: Identifiant unique de la réunion
    
    Cette opération supprime à la fois les métadonnées de la réunion dans la base
    de données et le fichier audio associé s'il est stocké localement.
    """
    # Supprimer la réunion et récupérer l'URL du fichier
    file_url = delete_meeting(meeting_id, current_user["id"])
    
    if not file_url:
        raise HTTPException(status_code=404, detail="Réunion non trouvée")
    
    try:
        # Si le fichier est stocké localement, supprimer le fichier
        if file_url.startswith("/uploads/"):
            file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), file_url[1:])
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted file: {file_path}")
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
    
    return {"message": "Réunion supprimée avec succès"}

@router.post("/{meeting_id}/transcribe", response_model=dict)
async def transcribe_meeting_route(
    meeting_id: str = Path(..., description="ID unique de la réunion"),
    current_user: dict = Depends(get_current_user)
):
    """
    Relance la transcription d'une réunion.
    
    - **meeting_id**: Identifiant unique de la réunion
    
    Utile si la transcription initiale a échoué ou pour relancer une transcription
    avec de nouveaux paramètres (non implémenté actuellement).
    
    La transcription s'exécute de manière asynchrone et peut prendre du temps
    selon la durée de l'audio.
    """
    meeting = get_meeting(meeting_id, current_user["id"])
    
    if not meeting:
        raise HTTPException(status_code=404, detail="Réunion non trouvée")
    
    # Vérifier si le fichier audio est accessible
    file_url = meeting["file_url"]
    if not file_url:
        raise HTTPException(status_code=400, detail="Aucun fichier audio associé à cette réunion")
    
    # Mettre à jour le statut de transcription
    update_meeting(meeting_id, current_user["id"], {"transcript_status": "pending"})
    
    try:
        # Lancer la transcription en arrière-plan
        transcribe_meeting(meeting_id, file_url, current_user["id"])
        logger.info(f"Transcription relancée pour la réunion {meeting_id}")
        return {"message": "Transcription relancée avec succès", "status": "pending"}
    except Exception as e:
        logger.error(f"Erreur lors du relancement de la transcription: {str(e)}")
        update_meeting(meeting_id, current_user["id"], {"transcript_status": "error"})
        raise HTTPException(status_code=500, detail=f"Erreur lors du relancement de la transcription: {str(e)}")

@router.get("/{meeting_id}/transcript", response_model=dict)
async def get_transcript(
    meeting_id: str = Path(..., description="ID unique de la réunion"),
    current_user: dict = Depends(get_current_user)
):
    """
    Récupère uniquement la transcription d'une réunion.
    
    - **meeting_id**: Identifiant unique de la réunion
    
    Cette route est optimisée pour récupérer uniquement le texte de transcription
    et son statut, sans les autres métadonnées de la réunion.
    """
    meeting = get_meeting(meeting_id, current_user["id"])
    
    if not meeting:
        raise HTTPException(status_code=404, detail="Réunion non trouvée")
    
    return {
        "transcript_text": meeting.get("transcript_text"),
        "transcript_status": meeting.get("transcript_status", "unknown"),
        "meeting_id": meeting_id
    }
