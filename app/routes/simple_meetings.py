"""
Routes simplifiées pour la gestion des réunions
"""

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Query, Path
from fastapi.logger import logger
from typing import Optional, Dict, Any, List
import os
from datetime import datetime
import logging
import traceback

from ..core.security import get_current_user
from ..services.assemblyai import transcribe_meeting
from ..db.queries import get_meeting, get_meetings_by_user, update_meeting, delete_meeting, create_meeting
from ..core.config import settings
from ..services.transcription_checker import check_and_update_transcription

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
    en fonction de la durée de l'audio. Le statut de la transcription est automatiquement
    vérifié et mis à jour.
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
            "transcript_status": "processing",  # Commencer directement en processing au lieu de pending
            "success": True  # Ajouter un indicateur de succès pour la cohérence avec les autres endpoints
        }
        meeting = create_meeting(meeting_data, current_user["id"])
        logger.info(f"Réunion créée avec le statut 'processing': {meeting['id']}")
        
        # 3. Lancer la transcription en arrière-plan
        transcript_id = transcribe_meeting(meeting["id"], file_url, current_user["id"])
        logger.info(f"Transcription lancée pour la réunion {meeting['id']} avec l'ID de transcription {transcript_id}")
        
        # 4. Démarrer un thread pour vérifier périodiquement le statut de la transcription
        if transcript_id:
            # Mettre à jour l'ID de transcription dans la base de données
            update_meeting(meeting["id"], current_user["id"], {"transcript_id": transcript_id})
            
            # Lancer un thread pour vérifier périodiquement le statut
            import threading
            check_thread = threading.Thread(
                target=periodic_transcription_check,
                args=(meeting["id"], transcript_id, current_user["id"])
            )
            check_thread.daemon = True  # Le thread s'arrêtera quand le programme principal s'arrête
            check_thread.start()
            logger.info(f"Thread de vérification périodique lancé pour la transcription {transcript_id}")
        
        return meeting
    
    except Exception as e:
        logger.error(f"Erreur lors de l'upload de la réunion: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Une erreur s'est produite lors de l'upload: {str(e)}"
        )

def periodic_transcription_check(meeting_id: str, transcript_id: str, user_id: str, max_checks: int = 20, interval_seconds: int = 30):
    """
    Vérifie périodiquement le statut d'une transcription et met à jour la base de données.
    
    Args:
        meeting_id: ID de la réunion
        transcript_id: ID de la transcription AssemblyAI
        user_id: ID de l'utilisateur
        max_checks: Nombre maximum de vérifications à effectuer
        interval_seconds: Intervalle entre les vérifications en secondes
    """
    import time
    from ..services.assemblyai import get_transcript_status
    from ..db.queries import get_meeting, update_meeting
    
    logger.info(f"Démarrage de la vérification périodique pour la transcription {transcript_id}")
    
    for i in range(max_checks):
        # Attendre l'intervalle spécifié
        time.sleep(interval_seconds)
        
        # Vérifier si la réunion existe toujours
        meeting = get_meeting(meeting_id, user_id)
        if not meeting:
            logger.warning(f"Réunion {meeting_id} non trouvée, arrêt des vérifications")
            break
        
        # Vérifier si la transcription est déjà terminée ou en erreur
        current_status = meeting.get("transcript_status")
        if current_status in ["completed", "error"]:
            logger.info(f"Transcription {transcript_id} déjà en état {current_status}, arrêt des vérifications")
            break
        
        # Vérifier le statut auprès d'AssemblyAI
        logger.info(f"Vérification {i+1}/{max_checks} du statut de la transcription {transcript_id}")
        try:
            status, transcript_data = get_transcript_status(transcript_id)
            logger.info(f"Statut actuel de la transcription {transcript_id}: {status}")
            
            if status == "completed":
                # Extraire le texte et les métadonnées
                transcript_text = transcript_data.get("text", "")
                
                # Formater avec les locuteurs si disponibles
                if "utterances" in transcript_data and transcript_data["utterances"]:
                    try:
                        from ..services.transcription_checker import format_transcript_text
                        transcript_text = format_transcript_text(transcript_data)
                        
                        # Calculer le nombre de locuteurs
                        speakers_set = set()
                        for utterance in transcript_data.get("utterances", []):
                            speakers_set.add(utterance.get("speaker", "Unknown"))
                        
                        speakers_count = len(speakers_set) if speakers_set else 1
                    except Exception as e:
                        logger.error(f"Erreur lors du formatage du texte: {str(e)}")
                        speakers_count = 1
                else:
                    speakers_count = 1
                
                # Mettre à jour la base de données
                update_data = {
                    "transcript_status": "completed",
                    "transcript_text": transcript_text,
                    "duration_seconds": int(transcript_data.get("audio_duration", 0)),
                    "speakers_count": speakers_count
                }
                update_meeting(meeting_id, user_id, update_data)
                logger.info(f"Transcription {transcript_id} terminée, base de données mise à jour")
                break
            
            elif status == "error":
                # Mettre à jour la base de données avec l'erreur
                error_message = transcript_data.get("error", "Unknown error")
                update_meeting(meeting_id, user_id, {
                    "transcript_status": "error",
                    "transcript_text": f"Erreur lors de la transcription: {error_message}"
                })
                logger.error(f"Erreur de transcription pour {transcript_id}: {error_message}")
                break
        
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de la transcription {transcript_id}: {str(e)}")
    
    logger.info(f"Fin des vérifications périodiques pour la transcription {transcript_id}")

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
    # Récupérer les réunions de l'utilisateur
    meetings = get_meetings_by_user(current_user["id"], status)
    
    # Vérifier automatiquement le statut des transcriptions en cours
    updated_meetings = []
    for meeting in meetings:
        if meeting.get("transcript_status") == "processing":
            logger.info(f"Vérification automatique du statut de la transcription pour la réunion {meeting.get('id')}")
            meeting = check_and_update_transcription(meeting)
        updated_meetings.append(meeting)
    
    # Filtrer par statut si spécifié
    if status:
        updated_meetings = [m for m in updated_meetings if m.get("transcript_status") == status]
    
    return updated_meetings

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
        
        # Récupérer les détails de la réunion
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
        
        # Vérifier automatiquement le statut de la transcription si elle est en cours
        if meeting.get("transcript_status") == "processing":
            logger.info(f"Vérification automatique du statut de la transcription pour la réunion {meeting_id}")
            meeting = check_and_update_transcription(meeting)
        
        # Appliquer les noms personnalisés des speakers à la transcription si elle est complétée
        if meeting.get("transcript_status") == "completed" and meeting.get("transcript_id"):
            try:
                from ..db.queries import get_meeting_speakers
                from ..services.transcription_checker import get_assemblyai_transcript_details, format_transcript_text
                
                logger.info(f"Application des noms personnalisés à la transcription pour la réunion {meeting_id}")
                speakers_data = get_meeting_speakers(meeting_id, current_user["id"])
                
                # S'il existe des speakers personnalisés, formater la transcription avec ces noms
                if speakers_data and any(speaker.get("custom_name") for speaker in speakers_data):
                    transcript_id = meeting.get("transcript_id")
                    transcript_data = get_assemblyai_transcript_details(transcript_id)
                    
                    if transcript_data:
                        speaker_names = {speaker["speaker_id"]: speaker["custom_name"] for speaker in speakers_data if speaker.get("custom_name")}
                        logger.info(f"Noms personnalisés détectés: {speaker_names}")
                        
                        if speaker_names:
                            updated_transcript = format_transcript_text(transcript_data, speaker_names)
                            meeting["transcript_text"] = updated_transcript
                            logger.info(f"Transcription mise à jour avec {len(speaker_names)} noms personnalisés")
            except Exception as e:
                logger.error(f"Erreur lors de l'application des noms personnalisés: {str(e)}")
        
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
