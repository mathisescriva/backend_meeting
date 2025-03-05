from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Path, Query
from fastapi.logger import logger
from ..core.security import get_current_user
from ..models.user import User
from ..models.meeting import Meeting, MeetingCreate, MeetingUpdate
from ..db.firebase import upload_mp3
from ..services.assemblyai import transcribe_meeting
from ..db.queries import create_meeting, get_meeting, get_meetings_by_user, update_meeting, delete_meeting
from datetime import datetime
from typing import List, Optional
import os
import tempfile
import traceback

router = APIRouter()

@router.post("/upload", response_model=dict, status_code=200, tags=["Réunions"])
async def upload_meeting(
    file: UploadFile = File(..., description="Fichier audio MP3 à transcrire"),
    title: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Télécharge un fichier audio MP3 et crée une nouvelle réunion avec transcription.
    
    - **file**: Fichier audio au format MP3 uniquement
    - **title**: Titre optionnel de la réunion (utilisera le nom du fichier par défaut)
    
    Le processus se déroule en plusieurs étapes:
    1. Upload du fichier
    2. Création d'une entrée dans la base de données
    3. Démarrage asynchrone de la transcription via AssemblyAI
    
    La transcription peut prendre du temps en fonction de la durée de l'audio.
    """
    if not title:
        title = file.filename
        
    if not file.filename.endswith('.mp3'):
        raise HTTPException(status_code=400, detail="Le fichier doit être au format MP3")
    
    # Utilise un fichier temporaire avec context manager
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
        try:
            # Sauvegarde le fichier uploadé
            content = await file.read()
            tmp_file.write(content)
            tmp_file.flush()  # Force l'écriture sur le disque
            
            # Upload vers le stockage local
            try:
                file_url = upload_mp3(tmp_file.name, current_user["id"])
                logger.info(f"File uploaded successfully: {file_url}")
            except Exception as e:
                logger.error(f"Error uploading file: {str(e)}\n{traceback.format_exc()}")
                raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")
            
            # Création meeting en base
            meeting_data = {
                "title": title or file.filename,
                "file_url": file_url
            }
            
            # Utilisation de SQLite pour insérer en base
            new_meeting = create_meeting(meeting_data, current_user["id"])
            
            if not new_meeting:
                raise HTTPException(status_code=500, detail="Erreur lors de la création de la réunion")
                
            # Lancer la transcription en arrière-plan
            try:
                transcribe_meeting(new_meeting["id"], file_url, current_user["id"])
                logger.info(f"Transcription démarrée pour la réunion {new_meeting['id']}")
            except Exception as e:
                logger.error(f"Erreur lors du démarrage de la transcription: {str(e)}")
                # Ne pas bloquer l'utilisateur si la transcription échoue
                update_meeting(new_meeting["id"], current_user["id"], {"transcript_status": "error"})
            
            return new_meeting
            
        except Exception as e:
            logger.error(f"Error uploading meeting: {str(e)}\n{traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Error uploading meeting: {str(e)}")
        finally:
            # Supprime le fichier temporaire
            try:
                os.unlink(tmp_file.name)
            except Exception as e:
                logger.error(f"Error removing temp file: {str(e)}")
                pass

@router.get("/", response_model=List[dict], tags=["Réunions"])
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

@router.get("/{meeting_id}", response_model=dict, tags=["Réunions"])
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

@router.put("/{meeting_id}", response_model=dict, tags=["Réunions"])
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

@router.delete("/{meeting_id}", response_model=dict, tags=["Réunions"])
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

@router.post("/{meeting_id}/transcribe", response_model=dict, tags=["Transcription"])
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

@router.get("/{meeting_id}/transcript", response_model=dict, tags=["Transcription"])
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
