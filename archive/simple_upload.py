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
from ..services.assemblyai import process_transcription
from ..db.sqlalchemy_database_simple import SessionLocal, Meeting

# Logger pour le du00e9bogage
logger = logging.getLogger("simple-upload")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

router = APIRouter(prefix="/simple", tags=["Simple Upload"])

# Du00e9pendance pour obtenir une session de base de donnu00e9es
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/upload", response_model=dict, status_code=200)
async def simple_upload_meeting(
    file: UploadFile = File(..., description="Fichier audio u00e0 transcrire"),
    title: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
    db: SessionLocal = Depends(get_db)
):
    """
    Tu00e9lu00e9charge un fichier audio et cru00e9e une nouvelle ru00e9union avec transcription.
    Cette route utilise un modu00e8le SQLAlchemy simplifiu00e9 avec la base de donnu00e9es PostgreSQL.
    
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
    
    # Convertir l'ID utilisateur en entier pour PostgreSQL
    try:
        user_id = int(current_user['id'])
        logger.info(f"Utilisation de l'ID utilisateur (converti en entier): {user_id} (type: {type(user_id)})")
    except ValueError:
        logger.error(f"L'ID utilisateur {current_user['id']} n'est pas un entier valide")
        raise HTTPException(
            status_code=400,
            detail=f"L'ID utilisateur n'est pas un entier valide"
        )
    
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
        
        # Cru00e9er la ru00e9union avec SQLAlchemy
        meeting_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        # Cru00e9er un nouvel objet Meeting avec le modu00e8le simplifiu00e9
        new_meeting = Meeting(
            id=meeting_id,
            user_id=user_id,
            title=title,
            file_url=file_url,
            transcript_status="processing",
            created_at=created_at
        )
        
        # Ajouter la ru00e9union u00e0 la session et valider
        db.add(new_meeting)
        db.commit()
        db.refresh(new_meeting)
        
        # Convertir l'objet Meeting en dictionnaire
        meeting = {
            "id": new_meeting.id,
            "user_id": new_meeting.user_id,
            "title": new_meeting.title,
            "file_url": new_meeting.file_url,
            "transcript_status": new_meeting.transcript_status,
            "created_at": new_meeting.created_at.isoformat() if new_meeting.created_at else None
        }
        
        # Lancer la transcription de maniu00e8re asynchrone
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
