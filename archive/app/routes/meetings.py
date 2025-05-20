from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Path, Query
from fastapi.logger import logger
from ..core.security import get_current_user
from ..models.user import User
from ..models.meeting import Meeting, MeetingCreate, MeetingUpdate
from ..db.firebase import upload_mp3
from ..services.assemblyai import transcribe_meeting, convert_to_wav, check_transcription_status, process_transcription
from ..services.mistral_summary import process_meeting_summary
from ..db.queries import create_meeting, get_meeting, get_meetings_by_user, update_meeting, delete_meeting
from datetime import datetime
from typing import List, Optional
import os
import tempfile
import traceback
import subprocess
import threading

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
    3. Démarrage synchrone de la transcription via AssemblyAI
    
    La transcription peut prendre du temps en fonction de la durée de l'audio.
    
    Améliorations de sécurité:
    - Vérification de l'authentification avant de commencer le traitement
    - Sauvegarde temporaire du fichier pour éviter la perte de données
    """
    # Vérification explicite de l'authentification pour éviter les pertes de données
    if not current_user or "id" not in current_user:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Vous n'êtes pas authentifié ou votre session a expiré",
                "type": "AUTH_ERROR",
                "action": "Veuillez vous reconnecter et réessayer"
            }
        )
        
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
            
            # Créer l'entrée dans la base de données avec le statut "processing" dès le début
            file_url = f"/{final_path}"
            meeting_data = {
                "title": title,
                "file_url": file_url,
                "transcript_status": "processing"  
            }
            meeting = create_meeting(meeting_data, current_user["id"])
            
            # Lancer la transcription de manière asynchrone avec logs détaillés
            logger.info(f"Lancement de la transcription pour la réunion {meeting['id']}")
            try:
                # Créer un thread et exécuter immédiatement la transcription avec le service unifié
                transcription_thread = threading.Thread(
                    target=process_transcription,
                    args=(meeting["id"], file_url, current_user["id"])
                )
                transcription_thread.daemon = False  # Permet au thread de continuer même si le serveur s'arrête
                transcription_thread.start()
                
                logger.info(f"Transcription lancée directement pour la réunion {meeting['id']}")
            except Exception as e:
                logger.error(f"Erreur lors du lancement de la transcription: {str(e)}")
                logger.error(traceback.format_exc())
                # Ne pas faire échouer la requête, juste logger l'erreur
            
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
    # Log pour le debugging
    logger.info(f"Attempting to get meeting with ID: {meeting_id} for user: {current_user['id']}")
    
    meeting = get_meeting(meeting_id, current_user["id"])
    
    if not meeting:
        logger.warning(f"Meeting not found - ID: {meeting_id}, User ID: {current_user['id']}")
        raise HTTPException(
            status_code=404, 
            detail={
                "message": "Réunion non trouvée",
                "meeting_id": meeting_id,
                "reason": "Cette réunion a peut-être été supprimée",
                "type": "MEETING_NOT_FOUND"
            }
        )
        
    # Assurer que transcription_status est présent dans la réponse pour compatibilité frontend
    if 'transcript_status' in meeting and 'transcription_status' not in meeting:
        meeting['transcription_status'] = meeting['transcript_status']
        
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

@router.post("/{meeting_id}/generate-summary", response_model=dict)
async def generate_meeting_summary_route(
    meeting_id: str = Path(..., description="ID unique de la réunion"),
    current_user: dict = Depends(get_current_user)
):
    """
    Génère un compte rendu de réunion en utilisant l'API Mistral.
    
    - **meeting_id**: Identifiant unique de la réunion
    
    Cette route déclenche la génération d'un compte rendu de réunion à partir
    de la transcription existante. La génération s'effectue de manière asynchrone.
    """
    # Vérifier que la réunion existe
    meeting = get_meeting(meeting_id, current_user["id"])
    
    if not meeting:
        raise HTTPException(
            status_code=404, 
            detail={
                "message": "Réunion non trouvée",
                "meeting_id": meeting_id,
                "reason": "Cette réunion a peut-être été supprimée",
                "type": "MEETING_NOT_FOUND"
            }
        )
    
    # Vérifier que la transcription est terminée
    if meeting.get("transcript_status") != "completed":
        raise HTTPException(
            status_code=400,
            detail={
                "message": "La transcription n'est pas terminée",
                "meeting_id": meeting_id,
                "reason": "La génération du compte rendu nécessite une transcription complète",
                "type": "TRANSCRIPTION_NOT_COMPLETED"
            }
        )
    
    # Démarrer la génération du compte rendu
    try:
        # Mettre à jour le statut pour indiquer que la génération est en cours
        update_meeting(meeting_id, current_user["id"], {"summary_status": "processing"})
        
        # Lancer le processus de génération du compte rendu
        process_meeting_summary(meeting_id, current_user["id"])
        
        # Récupérer la réunion mise à jour
        updated_meeting = get_meeting(meeting_id, current_user["id"])
        
        return {
            "message": "Génération du compte rendu en cours",
            "meeting": updated_meeting
        }
    except Exception as e:
        logger.error(f"Erreur lors du démarrage de la génération du compte rendu: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Erreur lors du démarrage de la génération du compte rendu",
                "error": str(e),
                "type": "SUMMARY_GENERATION_ERROR"
            }
        )

@router.get("/{meeting_id}/summary", response_model=dict)
async def get_meeting_summary(
    meeting_id: str = Path(..., description="ID unique de la réunion"),
    current_user: dict = Depends(get_current_user)
):
    """
    Récupère le compte rendu d'une réunion spécifique.
    
    - **meeting_id**: Identifiant unique de la réunion
    
    Retourne le compte rendu de la réunion et son statut.
    """
    # Vérifier que la réunion existe
    meeting = get_meeting(meeting_id, current_user["id"])
    
    if not meeting:
        raise HTTPException(
            status_code=404, 
            detail={
                "message": "Réunion non trouvée",
                "meeting_id": meeting_id,
                "reason": "Cette réunion a peut-être été supprimée",
                "type": "MEETING_NOT_FOUND"
            }
        )
    
    # Récupérer le compte rendu et son statut
    summary_text = meeting.get("summary_text")
    summary_status = meeting.get("summary_status")
    
    return {
        "meeting_id": meeting_id,
        "summary_text": summary_text,
        "summary_status": summary_status
    }

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
    # Vérifier que la réunion existe et appartient à l'utilisateur
    meeting = get_meeting(meeting_id, current_user["id"])
    
    if not meeting:
        raise HTTPException(status_code=404, detail="Réunion non trouvée")
    
    # Vérifier si un transcript_id existe déjà
    transcript_id = meeting.get("transcript_id")
    
    if transcript_id:
        # Si le statut est "completed", pas besoin de relancer
        if meeting.get("transcript_status") == "completed":
            return meeting
        
        # Vérifier le statut actuel sur AssemblyAI
        try:
            status, text, duration, speakers_count = await check_transcription_status(transcript_id)
            
            if status == "completed" and text:
                # Mettre à jour la base de données avec le texte de transcription
                update_data = {
                    "transcript_text": text,
                    "transcript_status": "completed",
                    "duration_seconds": duration,
                    "speakers_count": speakers_count
                }
                updated_meeting = update_meeting(meeting_id, current_user["id"], update_data)
                return updated_meeting
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du statut: {str(e)}")
            # Continuer pour relancer la transcription
    
    # Relancer la transcription
    file_url = meeting.get("file_url")
    
    if not file_url:
        raise HTTPException(
            status_code=400, 
            detail="URL du fichier manquante"
        )
    
    # Mettre à jour le statut
    update_meeting(meeting_id, current_user["id"], {"transcript_status": "processing"})
    
    # Lancer la transcription en arrière-plan
    transcribe_meeting(meeting_id, file_url, current_user["id"])
    
    # Obtenir la réunion mise à jour
    updated_meeting = get_meeting(meeting_id, current_user["id"])
    
    return updated_meeting

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
    
    # Si la transcription est en cours ou terminée, retourner les informations
    # Note: get_meeting() applique déjà normalize_transcript_format
    return {
        "transcript_text": meeting.get("transcript_text", ""),
        "transcript_status": meeting.get("transcript_status", "pending"),
        "duration_seconds": meeting.get("duration_seconds"),
        "speakers_count": meeting.get("speakers_count")
    }

@router.post("/validate-ids", response_model=dict)
async def validate_meeting_ids(
    meeting_ids: List[str],
    current_user: dict = Depends(get_current_user)
):
    """
    Valide une liste d'identifiants de réunions et retourne les IDs qui existent encore.
    
    - **meeting_ids**: Liste des identifiants de réunions à vérifier
    
    Utile pour nettoyer le cache côté frontend après suppression de meetings.
    """
    from ..db.database import get_db_connection
    
    logger.info(f"Validating {len(meeting_ids)} meeting IDs for user: {current_user['id']}")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Préparer la requête SQL pour vérifier plusieurs IDs à la fois
    placeholders = ','.join(['?'] * len(meeting_ids))
    
    # Ajouter l'ID de l'utilisateur à la liste des paramètres
    params = meeting_ids + [current_user["id"]]
    
    cursor.execute(
        f"SELECT id FROM meetings WHERE id IN ({placeholders}) AND user_id = ?", 
        params
    )
    
    existing_ids = [row["id"] for row in cursor.fetchall()]
    
    conn.close()
    
    # Calculer les IDs supprimés
    deleted_ids = [id for id in meeting_ids if id not in existing_ids]
    
    logger.info(f"Found {len(existing_ids)} existing and {len(deleted_ids)} deleted meeting IDs")
    
    return {
        "valid_ids": existing_ids,
        "invalid_ids": deleted_ids
    }
