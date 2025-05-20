from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form
from fastapi.security import OAuth2PasswordBearer
from ..core.security import get_current_user
from typing import Optional
import os
import uuid
import logging
import psycopg2
import psycopg2.extras
from datetime import datetime
import subprocess
import tempfile
import threading
from ..services.assemblyai import process_transcription

# Logger pour le débogage
logger = logging.getLogger("direct-upload")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

router = APIRouter(prefix="/direct", tags=["Direct Upload"])

@router.post("/upload", response_model=dict, status_code=200)
async def direct_upload_meeting(
    file: UploadFile = File(..., description="Fichier audio à transcrire"),
    title: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Télécharge un fichier audio et crée une nouvelle réunion avec transcription.
    Cette route utilise une connexion directe à PostgreSQL au lieu de SQLAlchemy.
    
    - **file**: Fichier audio au format MP3 ou WAV
    - **title**: Titre optionnel de la réunion (utilisera le nom du fichier par défaut)
    """
    # Vérification explicite de l'authentification pour éviter les pertes de données
    if not current_user or "id" not in current_user:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Vous n'êtes pas authentifié ou votre session a expiré",
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
        # Utiliser le titre fourni ou le nom du fichier par défaut
        if not title:
            title = file.filename
        
        # Sauvegarder le fichier temporairement
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".tmp")
        temp_path = temp_file.name
        temp_file.close()
        
        # Écrire le contenu du fichier uploadé dans le fichier temporaire
        with open(temp_path, "wb") as f:
            f.write(await file.read())
        
        # Convertir en WAV si nécessaire
        temp_output = temp_path + ".wav"
        subprocess.run(["ffmpeg", "-y", "-i", temp_path, "-acodec", "pcm_s16le", "-ar", "44100", temp_output], check=True)
        
        # Vérifier que le fichier WAV a été créé correctement
        file_info = subprocess.run(["file", temp_output], capture_output=True, text=True)
        if "WAVE" not in file_info.stdout and "WAV" not in file_info.stdout:
            raise Exception(f"Le fichier n'a pas été correctement converti en WAV: {file_info.stdout}")
        
        # Créer le dossier de destination s'il n'existe pas
        user_upload_dir = os.path.join("uploads", str(user_id))
        os.makedirs(user_upload_dir, exist_ok=True)
        
        # Générer un nom de fichier unique
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_tmp{next(tempfile._get_candidate_names())}.wav"
        final_path = os.path.join(user_upload_dir, filename)
        
        # Copier le fichier WAV vers sa destination finale
        with open(temp_output, "rb") as src, open(final_path, "wb") as dst:
            dst.write(src.read())
        
        # Créer l'entrée dans la base de données avec le statut approprié
        file_url = f"/{final_path}"
        
        # Connexion directe à PostgreSQL pour créer la réunion
        conn = None
        try:
            # Paramètres de connexion PostgreSQL
            db_params = {
                'dbname': os.getenv('POSTGRES_DB', 'postgres'),
                'user': os.getenv('POSTGRES_USER', 'postgres'),
                'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
                'host': os.getenv('POSTGRES_SERVER', 'localhost'),
                'port': os.getenv('POSTGRES_PORT', '5432')
            }
            
            # Établir la connexion à PostgreSQL
            conn = psycopg2.connect(**db_params)
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            # Générer un ID unique pour la réunion
            meeting_id = str(uuid.uuid4())
            created_at = datetime.utcnow()
            
            # Insérer la réunion dans la base de données
            # Afficher les valeurs avant insertion pour débogage
            logger.info(f"Valeurs pour insertion: meeting_id={meeting_id}, user_id={user_id} (type: {type(user_id)}), title={title}, file_url={file_url}")
            
            # Ne pas vérifier l'existence de l'utilisateur, utiliser directement l'ID utilisateur fourni par le token JWT
            # Cela permet d'éviter les problèmes de type de données entre SQLite et PostgreSQL
            logger.info(f"Utilisation directe de l'ID utilisateur: {user_id}")
            # Utiliser la mu00eame mu00e9thode que celle qui a fonctionnu00e9 dans notre script de du00e9bogage
            cursor.execute("""
                INSERT INTO meetings (id, user_id, title, file_url, transcript_status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, user_id, title, file_url, transcript_status, created_at
            """, (meeting_id, user_id, title, file_url, "processing", created_at))
            
            # Récupérer la réunion créée
            new_meeting = cursor.fetchone()
            conn.commit()
            
            # Convertir en dictionnaire
            meeting = dict(new_meeting)
            
            # Convertir datetime en chaîne ISO 8601
            if meeting['created_at'] and not isinstance(meeting['created_at'], str):
                meeting['created_at'] = meeting['created_at'].isoformat()
            
            # Lancer la transcription de manière asynchrone
            logger.info(f"Lancement de la transcription pour la réunion {meeting['id']}")
            try:
                # Créer un thread et exécuter immédiatement la transcription
                transcription_thread = threading.Thread(
                    target=process_transcription,
                    args=(meeting["id"], file_url, user_id)
                )
                transcription_thread.daemon = False  # Permet au thread de continuer même si le serveur s'arrête
                transcription_thread.start()
                
                logger.info(f"Transcription lancée directement pour la réunion {meeting['id']}")
            except Exception as e:
                logger.error(f"Erreur lors du lancement de la transcription: {str(e)}")
                # Ne pas faire échouer la requête, juste logger l'erreur
            
            return meeting
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Erreur lors de la création de la réunion: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()
                
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
