from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form
from fastapi.security import OAuth2PasswordBearer
from ..core.security import get_current_user
from typing import Optional
import os
import uuid
import logging
from datetime import datetime
import subprocess
import tempfile
import threading
import requests
import json
import time

# Logger pour le du00e9bogage
logger = logging.getLogger("direct-assemblyai")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

router = APIRouter(prefix="/direct-assemblyai", tags=["Direct AssemblyAI"])

# Clu00e9 API AssemblyAI
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "a0b3f4e5d6c7b8a9e0d1c2b3a4e5f6a7")

# Fonctions pour interagir avec l'API AssemblyAI
def upload_file_to_assemblyai(file_path):
    """Uploade un fichier audio vers AssemblyAI"""
    logger.info(f"Upload du fichier {file_path} vers AssemblyAI")
    
    headers = {
        "authorization": ASSEMBLYAI_API_KEY
    }
    
    with open(file_path, "rb") as f:
        response = requests.post(
            "https://api.assemblyai.com/v2/upload",
            headers=headers,
            data=f
        )
    
    if response.status_code == 200:
        upload_url = response.json()["upload_url"]
        logger.info(f"Fichier uploadu00e9 avec succu00e8s, URL: {upload_url}")
        return upload_url
    else:
        logger.error(f"Erreur lors de l'upload: {response.status_code} - {response.text}")
        raise Exception(f"Erreur lors de l'upload vers AssemblyAI: {response.status_code} - {response.text}")

def start_transcription(audio_url):
    """Du00e9marre une transcription avec AssemblyAI"""
    logger.info(f"Du00e9marrage de la transcription pour l'URL: {audio_url}")
    
    headers = {
        "authorization": ASSEMBLYAI_API_KEY,
        "content-type": "application/json"
    }
    
    json_data = {
        "audio_url": audio_url,
        "speaker_labels": True,
        "auto_chapters": True,
        "entity_detection": True,
        "summarization": True,
        "summary_model": "informative",
        "summary_type": "bullets",
        "auto_highlights": True
    }
    
    response = requests.post(
        "https://api.assemblyai.com/v2/transcript",
        headers=headers,
        json=json_data
    )
    
    if response.status_code == 200:
        transcript_id = response.json()["id"]
        logger.info(f"Transcription du00e9marru00e9e avec succu00e8s, ID: {transcript_id}")
        return transcript_id
    else:
        logger.error(f"Erreur lors du du00e9marrage de la transcription: {response.status_code} - {response.text}")
        raise Exception(f"Erreur lors du du00e9marrage de la transcription: {response.status_code} - {response.text}")

def check_transcription_status(transcript_id):
    """Vu00e9rifie le statut d'une transcription AssemblyAI"""
    logger.info(f"Vu00e9rification du statut de la transcription {transcript_id}")
    
    headers = {
        "authorization": ASSEMBLYAI_API_KEY
    }
    
    response = requests.get(
        f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        result = response.json()
        status = result["status"]
        logger.info(f"Statut de la transcription {transcript_id}: {status}")
        return result
    else:
        logger.error(f"Erreur lors de la vu00e9rification du statut: {response.status_code} - {response.text}")
        raise Exception(f"Erreur lors de la vu00e9rification du statut: {response.status_code} - {response.text}")

def wait_for_completion(transcript_id, max_attempts=60, delay=5):
    """Attend que la transcription soit terminu00e9e"""
    logger.info(f"Attente de la fin de la transcription {transcript_id}")
    
    for attempt in range(max_attempts):
        result = check_transcription_status(transcript_id)
        status = result["status"]
        
        if status == "completed":
            logger.info(f"Transcription {transcript_id} terminu00e9e avec succu00e8s")
            return result
        elif status == "error":
            logger.error(f"Erreur lors de la transcription {transcript_id}: {result.get('error')}")
            raise Exception(f"Erreur lors de la transcription: {result.get('error')}")
        
        logger.info(f"Transcription en cours... (tentative {attempt+1}/{max_attempts})")
        time.sleep(delay)
    
    logger.error(f"Du00e9lai d'attente du00e9passu00e9 pour la transcription {transcript_id}")
    raise Exception("Du00e9lai d'attente du00e9passu00e9 pour la transcription")

@router.post("/upload", response_model=dict, status_code=200)
async def direct_assemblyai_upload(
    file: UploadFile = File(..., description="Fichier audio u00e0 transcrire"),
    title: Optional[str] = Form(None),
    wait_for_result: Optional[bool] = Form(False),
    current_user: dict = Depends(get_current_user)
):
    """
    Tu00e9lu00e9charge un fichier audio directement vers AssemblyAI pour transcription.
    Cette route ne stocke pas les donnu00e9es dans la base de donnu00e9es PostgreSQL.
    
    - **file**: Fichier audio au format MP3 ou WAV
    - **title**: Titre optionnel de la ru00e9union (utilisera le nom du fichier par du00e9faut)
    - **wait_for_result**: Si True, attend que la transcription soit terminu00e9e avant de renvoyer le ru00e9sultat
    """
    # Vu00e9rification explicite de l'authentification pour u00e9viter les pertes de donnu00e9es
    if not current_user or "id" not in current_user:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Vous n'u00eates pas authentifiu00e9 ou votre session a expiru00e9",
                "action": "login"
            }
        )
    
    # Ru00e9cupu00e9rer l'ID utilisateur
    user_id = current_user['id']
    logger.info(f"Utilisation de l'ID utilisateur: {user_id}")
    
    try:
        # Utiliser le titre fourni ou le nom du fichier par du00e9faut
        if not title:
            title = file.filename
        
        # Sauvegarder le fichier temporairement
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".tmp")
        temp_path = temp_file.name
        temp_file.close()
        
        # u00c9crire le contenu du fichier uploadu00e9 dans le fichier temporaire
        with open(temp_path, "wb") as f:
            f.write(await file.read())
        
        # Convertir en WAV si nu00e9cessaire
        temp_output = temp_path + ".wav"
        subprocess.run(["ffmpeg", "-y", "-i", temp_path, "-acodec", "pcm_s16le", "-ar", "44100", temp_output], check=True)
        
        # Vu00e9rifier que le fichier WAV a u00e9tu00e9 cru00e9u00e9 correctement
        file_info = subprocess.run(["file", temp_output], capture_output=True, text=True)
        if "WAVE" not in file_info.stdout and "WAV" not in file_info.stdout:
            raise Exception(f"Le fichier n'a pas u00e9tu00e9 correctement converti en WAV: {file_info.stdout}")
        
        # Uploader le fichier vers AssemblyAI
        upload_url = upload_file_to_assemblyai(temp_output)
        
        # Du00e9marrer la transcription
        transcript_id = start_transcription(upload_url)
        
        # Pru00e9parer la ru00e9ponse
        response_data = {
            "title": title,
            "transcript_id": transcript_id,
            "status": "processing",
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Si l'utilisateur souhaite attendre le ru00e9sultat
        if wait_for_result:
            try:
                # Attendre que la transcription soit terminu00e9e
                result = wait_for_completion(transcript_id)
                
                # Ajouter les ru00e9sultats u00e0 la ru00e9ponse
                response_data["status"] = result["status"]
                response_data["text"] = result.get("text")
                response_data["summary"] = result.get("summary")
                response_data["chapters"] = result.get("chapters")
                response_data["entities"] = result.get("entities")
                response_data["auto_highlights_result"] = result.get("auto_highlights_result")
            except Exception as e:
                logger.error(f"Erreur lors de l'attente du ru00e9sultat: {str(e)}")
                response_data["error_waiting"] = str(e)
        
        return response_data
        
    except Exception as e:
        logger.error(f"Erreur lors de l'upload direct vers AssemblyAI: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        raise HTTPException(
            status_code=500,
            detail=f"Une erreur s'est produite lors de l'upload direct vers AssemblyAI: {str(e)}"
        )
    finally:
        # Nettoyage des fichiers temporaires
        try:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            if os.path.exists(temp_output):
                os.unlink(temp_output)
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage des fichiers temporaires: {str(e)}")

@router.get("/status/{transcript_id}", response_model=dict, status_code=200)
async def check_transcription(
    transcript_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Vu00e9rifie le statut d'une transcription AssemblyAI.
    
    - **transcript_id**: ID de la transcription u00e0 vu00e9rifier
    """
    try:
        result = check_transcription_status(transcript_id)
        return result
    except Exception as e:
        logger.error(f"Erreur lors de la vu00e9rification du statut: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Une erreur s'est produite lors de la vu00e9rification du statut: {str(e)}"
        )
