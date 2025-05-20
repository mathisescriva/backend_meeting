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
import time

# Importer les fonctions du service AssemblyAI existant
from ..services.assemblyai import (
    upload_file_to_assemblyai,
    start_transcription,
    check_transcription_status,
    convert_to_wav
)

# Logger pour le du00e9bogage
logger = logging.getLogger("assemblyai-direct")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

router = APIRouter(prefix="/assemblyai-direct", tags=["AssemblyAI Direct"])

@router.post("/upload", response_model=dict, status_code=200)
async def assemblyai_direct_upload(
    file: UploadFile = File(..., description="Fichier audio u00e0 transcrire"),
    title: Optional[str] = Form(None),
    wait_for_result: Optional[bool] = Form(False),
    current_user: dict = Depends(get_current_user)
):
    """
    Tu00e9lu00e9charge un fichier audio directement vers AssemblyAI pour transcription.
    Cette route utilise les fonctions existantes du service AssemblyAI sans stocker les donnu00e9es dans PostgreSQL.
    
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
        
        # Convertir en WAV en utilisant la fonction existante
        try:
            wav_path = convert_to_wav(temp_path)
            logger.info(f"Fichier converti avec succu00e8s: {wav_path}")
        except Exception as e:
            logger.error(f"Erreur lors de la conversion du fichier: {str(e)}")
            # Fallback sur la conversion simple
            wav_path = temp_path + ".wav"
            subprocess.run(["ffmpeg", "-y", "-i", temp_path, "-acodec", "pcm_s16le", "-ar", "44100", wav_path], check=True)
            logger.info(f"Fichier converti avec la mu00e9thode de secours: {wav_path}")
        
        # Vu00e9rifier que le fichier WAV a u00e9tu00e9 cru00e9u00e9 correctement
        file_info = subprocess.run(["file", wav_path], capture_output=True, text=True)
        if "WAVE" not in file_info.stdout and "WAV" not in file_info.stdout:
            raise Exception(f"Le fichier n'a pas u00e9tu00e9 correctement converti en WAV: {file_info.stdout}")
        
        # Uploader le fichier vers AssemblyAI en utilisant la fonction existante
        # Note: cette u00e9tape peut u00eatre optionnelle avec le SDK AssemblyAI
        upload_url = upload_file_to_assemblyai(wav_path)
        logger.info(f"Fichier uploadu00e9 vers AssemblyAI: {upload_url}")
        
        # Du00e9marrer la transcription en utilisant la fonction existante
        transcript_id = start_transcription(wav_path)
        logger.info(f"Transcription du00e9marru00e9e: {transcript_id}")
        
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
                # Attendre que la transcription soit terminu00e9e (avec timeout)
                max_attempts = 60  # 5 minutes maximum (5 secondes * 60)
                for attempt in range(max_attempts):
                    result = check_transcription_status(transcript_id)
                    status = result.get("status")
                    
                    if status == "completed":
                        logger.info(f"Transcription {transcript_id} terminu00e9e avec succu00e8s")
                        # Ajouter les ru00e9sultats u00e0 la ru00e9ponse
                        response_data["status"] = "completed"
                        response_data["text"] = result.get("text")
                        response_data["summary"] = result.get("summary")
                        response_data["chapters"] = result.get("chapters")
                        response_data["entities"] = result.get("entities")
                        response_data["auto_highlights_result"] = result.get("auto_highlights_result")
                        break
                    elif status == "error":
                        logger.error(f"Erreur lors de la transcription {transcript_id}: {result.get('error')}")
                        response_data["status"] = "error"
                        response_data["error"] = result.get("error")
                        break
                    
                    logger.info(f"Transcription en cours... (tentative {attempt+1}/{max_attempts})")
                    time.sleep(5)  # Attendre 5 secondes entre chaque vu00e9rification
                
                if response_data["status"] == "processing":
                    logger.warning(f"Du00e9lai d'attente du00e9passu00e9 pour la transcription {transcript_id}")
                    response_data["warning"] = "Du00e9lai d'attente du00e9passu00e9, la transcription est toujours en cours"
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
            if 'wav_path' in locals() and os.path.exists(wav_path):
                os.unlink(wav_path)
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage des fichiers temporaires: {str(e)}")

@router.get("/status/{transcript_id}", response_model=dict, status_code=200)
async def check_transcription_status_route(
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
