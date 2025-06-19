from fastapi import APIRouter, Depends, HTTPException, Path, Body
from fastapi.logger import logger
from ..core.security import get_current_user
from ..models.user import User
from ..models.speaker import Speaker, SpeakerCreate, SpeakersList
from ..db.queries import (
    get_meeting, get_meeting_speakers, set_meeting_speaker,
    delete_meeting_speaker, get_custom_speaker_name
)
from ..services.transcription_checker import get_assemblyai_transcript_details, format_transcript_text
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime

router = APIRouter(prefix="/meetings/{meeting_id}/speakers", tags=["Locuteurs"])

@router.get("", response_model=SpeakersList)
async def list_meeting_speakers(
    meeting_id: str = Path(..., description="ID unique de la réunion"),
    current_user: dict = Depends(get_current_user)
):
    """
    Récupère la liste des noms personnalisés des locuteurs pour une réunion.
    
    - **meeting_id**: Identifiant unique de la réunion
    
    Retourne la liste des mappages entre identifiants de locuteurs et noms personnalisés.
    """
    # Vérifier que la réunion existe et appartient à l'utilisateur courant
    meeting = get_meeting(meeting_id, current_user["id"])
    if not meeting:
        raise HTTPException(
            status_code=404,
            detail={"message": "Réunion non trouvée", "type": "NOT_FOUND"}
        )
    
    # Récupérer les noms personnalisés des locuteurs
    speakers = get_meeting_speakers(meeting_id, current_user["id"])
    if speakers is None:  # Erreur lors de la récupération
        raise HTTPException(
            status_code=500,
            detail={"message": "Erreur lors de la récupération des locuteurs", "type": "SERVER_ERROR"}
        )
    
    return SpeakersList(speakers=speakers)


@router.post("", response_model=Speaker)
async def create_or_update_speaker(
    speaker_data: SpeakerCreate = Body(...),
    meeting_id: str = Path(..., description="ID unique de la réunion"),
    current_user: dict = Depends(get_current_user)
):
    """
    Crée ou met à jour un nom personnalisé pour un locuteur dans une réunion.
    
    - **meeting_id**: Identifiant unique de la réunion
    - **speaker_data**: Données du locuteur (identifiant et nom personnalisé)
    
    Si un nom existe déjà pour ce locuteur dans cette réunion, il est mis à jour.
    Sinon, un nouveau mapping est créé.
    """
    # Vérifier que la réunion existe et appartient à l'utilisateur courant
    meeting = get_meeting(meeting_id, current_user["id"])
    if not meeting:
        raise HTTPException(
            status_code=404,
            detail={"message": "Réunion non trouvée", "type": "NOT_FOUND"}
        )
    
    # Créer ou mettre à jour le nom personnalisé
    success = set_meeting_speaker(
        meeting_id, current_user["id"],
        speaker_data.speaker_id, speaker_data.custom_name
    )
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail={"message": "Erreur lors de la création/mise à jour du nom personnalisé", "type": "SERVER_ERROR"}
        )
    
    # Récupérer les données mises à jour
    speakers = get_meeting_speakers(meeting_id, current_user["id"])
    if not speakers:
        raise HTTPException(
            status_code=500,
            detail={"message": "Erreur lors de la récupération du locuteur mis à jour", "type": "SERVER_ERROR"}
        )
    
    # Trouver le locuteur nouvellement créé/mis à jour
    created_speaker = None
    for speaker in speakers:
        if speaker["speaker_id"] == speaker_data.speaker_id:
            created_speaker = speaker
            break
    
    if not created_speaker:
        # Fallback au cas où le locuteur n'est pas retrouvé (ne devrait pas arriver)
        raise HTTPException(
            status_code=500,
            detail={"message": "Erreur lors de la création du locuteur", "type": "SERVER_ERROR"}
        )
        
    # Mettre à jour automatiquement la transcription avec le nouveau nom de locuteur
    try:
        # Vérifier que la transcription est terminée
        if meeting.get("transcript_status") == "completed" and meeting.get("transcript_id"):
            transcript_id = meeting.get("transcript_id")
            transcript_data = get_assemblyai_transcript_details(transcript_id)
            
            if transcript_data:
                # Récupérer tous les noms personnalisés des locuteurs
                speaker_names = {s["speaker_id"]: s["custom_name"] for s in speakers if s.get("custom_name")}
                
                # Formater la transcription avec les noms personnalisés
                updated_transcript = format_transcript_text(transcript_data, speaker_names)
                
                # Mettre à jour le texte de transcription dans la base de données
                from ..db.queries import update_meeting
                logger.info(f"Mise à jour automatique de la transcription après renommage de {speaker_data.speaker_id} en {speaker_data.custom_name}")
                
                update_result = update_meeting(meeting_id, current_user["id"], {
                    "transcript_text": updated_transcript,
                    "updated_at": datetime.utcnow().isoformat()  # Force une mise à jour du timestamp
                })
                
                logger.info(f"Transcription mise à jour automatiquement: {update_result}")
    except Exception as e:
        # Log l'erreur mais ne pas faire échouer la création du speaker
        logger.error(f"Erreur lors de la mise à jour automatique de la transcription: {str(e)}")
    
    return created_speaker


@router.delete("/{speaker_id}", response_model=dict)
async def delete_speaker(
    meeting_id: str = Path(..., description="ID unique de la réunion"),
    speaker_id: str = Path(..., description="ID du locuteur à supprimer"),
    current_user: dict = Depends(get_current_user)
):
    """
    Supprime un nom personnalisé de locuteur pour une réunion.
    
    - **meeting_id**: Identifiant unique de la réunion
    - **speaker_id**: Identifiant du locuteur
    
    Retourne un statut de succès ou d'échec.
    """
    # Vérifier que la réunion existe et appartient à l'utilisateur courant
    meeting = get_meeting(meeting_id, current_user["id"])
    if not meeting:
        raise HTTPException(
            status_code=404,
            detail={"message": "Réunion non trouvée", "type": "NOT_FOUND"}
        )
    
    # Supprimer le nom personnalisé
    success = delete_meeting_speaker(meeting_id, current_user["id"], speaker_id)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail={"message": "Erreur lors de la suppression du nom personnalisé", "type": "SERVER_ERROR"}
        )
    
    return {"success": True, "message": "Nom personnalisé supprimé avec succès"}


@router.get("/update-transcript", response_model=dict)
async def get_updated_transcript(
    meeting_id: str = Path(..., description="ID unique de la réunion"),
    current_user: dict = Depends(get_current_user)
):
    """
    Récupère la transcription avec les noms personnalisés appliqués.
    
    - **meeting_id**: Identifiant unique de la réunion
    
    Retourne la transcription mise à jour avec les noms personnalisés.
    """
    # Vérifier que la réunion existe et appartient à l'utilisateur courant
    meeting = get_meeting(meeting_id, current_user["id"])
    if not meeting:
        raise HTTPException(
            status_code=404,
            detail={"message": "Réunion non trouvée", "type": "NOT_FOUND"}
        )
    
    # Vérifier que la transcription est terminée
    if meeting.get("transcript_status") != "completed":
        raise HTTPException(
            status_code=400,
            detail={
                "message": "La transcription n'est pas encore terminée",
                "type": "INVALID_STATE",
                "status": meeting.get("transcript_status", "unknown")
            }
        )
    
    # Récupérer l'ID de la transcription
    transcript_id = meeting.get("transcript_id")
    if not transcript_id:
        raise HTTPException(
            status_code=400,
            detail={"message": "Pas d'ID de transcription disponible", "type": "MISSING_DATA"}
        )
    
    # Récupérer les détails de la transcription
    transcript_data = get_assemblyai_transcript_details(transcript_id)
    if not transcript_data:
        raise HTTPException(
            status_code=500,
            detail={"message": "Impossible de récupérer les détails de la transcription", "type": "API_ERROR"}
        )
    
    # Récupérer les noms personnalisés des locuteurs
    speakers_data = get_meeting_speakers(meeting_id, current_user["id"])
    speaker_names = {}
    
    if speakers_data:
        for speaker in speakers_data:
            speaker_names[speaker["speaker_id"]] = speaker["custom_name"]
    
    # Formater la transcription avec les noms personnalisés
    updated_transcript = format_transcript_text(transcript_data, speaker_names)
    
    # Mettre à jour le texte de transcription dans la base de données
    from ..db.queries import update_meeting
    logger.info(f"Mise à jour de la transcription pour {meeting_id} avec {len(speaker_names)} noms personnalisés")
    for speaker_id, name in speaker_names.items():
        logger.info(f"Remplacement du locuteur {speaker_id} par {name}")
        
    update_result = update_meeting(meeting_id, current_user["id"], {
        "transcript_text": updated_transcript,
        "updated_at": datetime.utcnow().isoformat()  # Force une mise à jour du timestamp
    })
    
    # Vérification que la mise à jour a bien été prise en compte
    updated_meeting = get_meeting(meeting_id, current_user["id"])
    if updated_meeting and updated_meeting.get("transcript_text") == updated_transcript:
        logger.info("Vérification OK: La transcription a été correctement mise à jour")
    else:
        logger.warning("ATTENTION: La transcription ne semble pas avoir été mise à jour correctement")
    
    return {
        "success": True,
        "message": "Transcription mise à jour avec les noms personnalisés",
        "transcript_text": updated_transcript
    }
