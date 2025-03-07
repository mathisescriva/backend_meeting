"""
Service simplifié pour l'upload et la transcription de réunions
"""

import os
import asyncio
import requests
import time
import logging
import traceback
from pathlib import Path
from datetime import datetime
import mimetypes
import subprocess
import threading
from fastapi import UploadFile

from ..core.config import settings
from ..db.queries import update_meeting, create_meeting, get_pending_transcriptions

# Configuration du logging
logger = logging.getLogger("meeting-transcriber")

# API endpoints et clé
ASSEMBLY_AI_API_KEY = settings.ASSEMBLYAI_API_KEY
ASSEMBLY_AI_API_URL = 'https://api.assemblyai.com/v2'

async def upload_and_transcribe(
    file: UploadFile,
    user_id: str, 
    title: str = None
):
    """
    Upload un fichier audio, crée une réunion et démarre la transcription.
    
    Args:
        file: Fichier audio uploadé
        user_id: ID de l'utilisateur
        title: Titre de la réunion (optionnel)
        
    Returns:
        dict: Données de la réunion créée
    """
    if not title:
        title = file.filename
    
    try:
        # 1. Sauvegarder le fichier audio
        user_upload_dir = os.path.join("uploads", str(user_id))
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
        meeting = create_meeting(meeting_data, user_id)
        logger.info(f"Réunion créée avec le statut 'processing': {meeting['id']}")
        
        # 3. Lancer la transcription en arrière-plan immédiatement
        thread = threading.Thread(
            target=process_transcription,
            args=(meeting["id"], file_path, user_id)
        )
        thread.daemon = False
        thread.start()
        logger.info(f"Transcription lancée immédiatement pour la réunion {meeting['id']}")
        
        return meeting
    
    except Exception as e:
        logger.error(f"Erreur lors de l'upload et de la transcription: {str(e)}")
        logger.error(traceback.format_exc())
        raise e

def process_transcription(meeting_id, file_path, user_id):
    """
    Traite la transcription d'un fichier audio.
    
    Args:
        meeting_id: ID de la réunion
        file_path: Chemin vers le fichier audio
        user_id: ID de l'utilisateur
    """
    try:
        logger.info(f"Démarrage du processus de transcription pour {meeting_id}")
        
        # 1. Uploader le fichier vers AssemblyAI
        try:
            upload_url = upload_file_to_assemblyai(file_path)
            logger.info(f"Fichier uploadé: {upload_url}")
        except Exception as upload_error:
            logger.error(f"Erreur lors de l'upload vers AssemblyAI: {str(upload_error)}")
            update_meeting(meeting_id, user_id, {
                "transcript_status": "error",
                "transcript_text": f"Erreur lors de l'upload vers AssemblyAI: {str(upload_error)}"
            })
            return
        
        # 2. Démarrer la transcription
        try:
            transcript_id = start_transcription(upload_url)
            logger.info(f"Transcription démarrée: {transcript_id}")
        except Exception as start_error:
            logger.error(f"Erreur lors du démarrage de la transcription: {str(start_error)}")
            update_meeting(meeting_id, user_id, {
                "transcript_status": "error",
                "transcript_text": f"Erreur lors du démarrage de la transcription: {str(start_error)}"
            })
            return
        
        # 3. Vérifier le statut jusqu'à ce que la transcription soit terminée
        max_attempts = 60  # 30 minutes maximum (60 * 30 secondes)
        for attempt in range(1, max_attempts + 1):
            logger.info(f"Vérification du statut, tentative {attempt}/{max_attempts}")
            
            status, text = check_transcription_status(transcript_id)
            logger.info(f"Statut de la transcription: {status}")
            
            if status == "completed":
                # Transcription terminée avec succès
                update_meeting(meeting_id, user_id, {
                    "transcript_status": "completed",
                    "transcript_text": text
                })
                logger.info(f"Transcription terminée avec succès pour {meeting_id}")
                return
            
            if status == "error":
                # Erreur lors de la transcription
                update_meeting(meeting_id, user_id, {
                    "transcript_status": "error",
                    "transcript_text": text or "Erreur lors de la transcription"
                })
                logger.error(f"Erreur lors de la transcription pour {meeting_id}: {text}")
                return
            
            # Attendre avant la prochaine vérification
            time.sleep(30)
        
        # Si on arrive ici, c'est que la transcription a pris trop de temps
        update_meeting(meeting_id, user_id, {
            "transcript_status": "error",
            "transcript_text": "La transcription a pris trop de temps"
        })
        logger.error(f"Timeout lors de la transcription pour {meeting_id}")
    
    except Exception as e:
        logger.error(f"Erreur lors de la transcription pour {meeting_id}: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Mettre à jour le statut en cas d'erreur
        try:
            update_meeting(meeting_id, user_id, {
                "transcript_status": "error",
                "transcript_text": f"Erreur lors de la transcription: {str(e)}"
            })
        except Exception as db_error:
            logger.error(f"Erreur lors de la mise à jour de la base de données: {str(db_error)}")

def upload_file_to_assemblyai(file_path):
    """
    Upload un fichier vers AssemblyAI de manière synchrone.
    
    Args:
        file_path: Chemin vers le fichier à uploader
        
    Returns:
        str: URL du fichier uploadé
    """
    logger.info(f"Upload du fichier vers AssemblyAI: {file_path}")
    
    headers = {
        "authorization": ASSEMBLY_AI_API_KEY
    }
    
    with open(file_path, "rb") as f:
        response = requests.post(
            f"{ASSEMBLY_AI_API_URL}/upload",
            headers=headers,
            data=f
        )
    
    if response.status_code != 200:
        error_msg = f"Erreur lors de l'upload du fichier: {response.text}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    upload_url = response.json().get("upload_url")
    if not upload_url:
        error_msg = "URL d'upload non trouvée dans la réponse"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    return upload_url

def start_transcription(audio_url):
    """
    Démarre une transcription sur AssemblyAI.
    
    Args:
        audio_url: URL du fichier audio à transcrire
        
    Returns:
        str: ID de la transcription
    """
    logger.info(f"Démarrage de la transcription pour {audio_url}")
    
    headers = {
        "authorization": ASSEMBLY_AI_API_KEY,
        "content-type": "application/json"
    }
    
    json_data = {
        "audio_url": audio_url,
        "language_code": "fr",
        "speaker_labels": True
    }
    
    response = requests.post(
        f"{ASSEMBLY_AI_API_URL}/transcript",
        headers=headers,
        json=json_data
    )
    
    if response.status_code != 200:
        error_msg = f"Erreur lors du démarrage de la transcription: {response.text}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    transcript_id = response.json().get("id")
    if not transcript_id:
        error_msg = "ID de transcription non trouvé dans la réponse"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    return transcript_id

def check_transcription_status(transcript_id):
    """
    Vérifie le statut d'une transcription.
    
    Args:
        transcript_id: ID de la transcription
        
    Returns:
        tuple: (status, text) - statut de la transcription et texte si disponible
    """
    logger.info(f"Vérification du statut de la transcription {transcript_id}")
    
    headers = {
        "authorization": ASSEMBLY_AI_API_KEY
    }
    
    response = requests.get(
        f"{ASSEMBLY_AI_API_URL}/transcript/{transcript_id}",
        headers=headers
    )
    
    if response.status_code != 200:
        error_msg = f"Erreur lors de la vérification du statut: {response.text}"
        logger.error(error_msg)
        return "error", error_msg
    
    result = response.json()
    status = result.get("status")
    
    if status == "completed":
        # Récupérer le texte par intervenant si disponible
        utterances = result.get("utterances", [])
        if utterances:
            text = ""
            for utterance in utterances:
                speaker = utterance.get("speaker", "Speaker")
                utterance_text = utterance.get("text", "")
                text += f"{speaker}: {utterance_text}\n"
        else:
            # Sinon, récupérer le texte simple
            text = result.get("text", "")
        
        return "completed", text
    
    if status == "error":
        error = result.get("error", "Erreur inconnue")
        return "error", error
    
    # Si le statut n'est ni completed ni error, retourner le statut sans texte
    return status, None

def process_pending_transcriptions():
    """
    Traite toutes les transcriptions en attente.
    À exécuter au démarrage de l'application.
    """
    pending_meetings = get_pending_transcriptions()
    if not pending_meetings:
        logger.info("Aucune transcription en attente à traiter")
        return
    
    logger.info(f"Traitement de {len(pending_meetings)} transcription(s) en attente")
    for meeting in pending_meetings:
        file_path = meeting.get("file_url", "").lstrip("/")
        if not os.path.exists(file_path):
            logger.error(f"Fichier introuvable pour la réunion {meeting['id']}: {file_path}")
            update_meeting(meeting["id"], meeting["user_id"], {
                "transcript_status": "error",
                "transcript_text": f"Fichier introuvable: {file_path}"
            })
            continue
        
        # Lancer la transcription
        thread = threading.Thread(
            target=process_transcription,
            args=(meeting["id"], file_path, meeting["user_id"])
        )
        thread.daemon = False
        thread.start()
        logger.info(f"Transcription lancée pour la réunion en attente {meeting['id']}")
