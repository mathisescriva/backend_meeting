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
import sqlite3

# Logger pour le du00e9bogage
logger = logging.getLogger("working-upload")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

router = APIRouter(prefix="/working", tags=["Working Upload"])

@router.post("/upload", response_model=dict, status_code=200)
async def working_upload_meeting(
    file: UploadFile = File(..., description="Fichier audio u00e0 transcrire"),
    title: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Tu00e9lu00e9charge un fichier audio et cru00e9e une nouvelle ru00e9union avec transcription.
    Cette route utilise SQLite pour contourner les probu00e8mes avec PostgreSQL.
    
    - **file**: Fichier audio au format MP3 ou WAV
    - **title**: Titre optionnel de la ru00e9union (utilisera le nom du fichier par du00e9faut)
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
    logger.info(f"Utilisation de l'ID utilisateur: {user_id} (type: {type(user_id)})")
    
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
        
        # Cru00e9er le dossier de destination s'il n'existe pas
        user_upload_dir = os.path.join("uploads", str(user_id))
        os.makedirs(user_upload_dir, exist_ok=True)
        
        # Gu00e9nu00e9rer un nom de fichier unique
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_tmp{next(tempfile._get_candidate_names())}.wav"
        final_path = os.path.join(user_upload_dir, filename)
        
        # Copier le fichier WAV vers sa destination finale
        with open(temp_output, "rb") as src, open(final_path, "wb") as dst:
            dst.write(src.read())
        
        # Cru00e9er l'entru00e9e dans la base de donnu00e9es avec le statut appropriu00e9
        file_url = f"/{final_path}"
        
        # Utiliser SQLite pour stocker les donnu00e9es
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "app.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Gu00e9nu00e9rer un ID unique pour la ru00e9union
        meeting_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        
        # Insu00e9rer la ru00e9union dans SQLite
        cursor.execute(
            """
            INSERT INTO meetings (
                id, user_id, title, file_url, 
                transcript_status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                meeting_id, 
                user_id, 
                title, 
                file_url, 
                "processing", 
                created_at
            )
        )
        
        # Valider la transaction
        conn.commit()
        
        # Ru00e9cupu00e9rer la ru00e9union cru00e9u00e9e
        cursor.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,))
        meeting_data = cursor.fetchone()
        
        # Fermer la connexion
        cursor.close()
        conn.close()
        
        # Convertir les donnu00e9es en dictionnaire
        meeting = dict(meeting_data)
        
        # Lancer la transcription de maniu00e8re asynchrone
        from ..services.assemblyai import process_transcription
        logger.info(f"Lancement de la transcription pour la ru00e9union {meeting['id']}")
        try:
            # Cru00e9er un thread et exu00e9cuter immu00e9diatement la transcription
            transcription_thread = threading.Thread(
                target=process_transcription,
                args=(meeting["id"], file_url, user_id)
            )
            transcription_thread.daemon = False  # Permet au thread de continuer mu00eame si le serveur s'arru00eate
            transcription_thread.start()
            
            logger.info(f"Transcription lancu00e9e directement pour la ru00e9union {meeting['id']}")
        except Exception as e:
            logger.error(f"Erreur lors du lancement de la transcription: {str(e)}")
            # Ne pas faire u00e9chouer la requu00eate, juste logger l'erreur
        
        return meeting
        
    except Exception as e:
        logger.error(f"Erreur lors de l'upload: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Une erreur s'est produite lors de l'upload: {str(e)}"
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
