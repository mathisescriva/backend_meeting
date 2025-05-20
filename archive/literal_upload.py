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
import psycopg2
import psycopg2.extras
from ..services.assemblyai import process_transcription

# Logger pour le du00e9bogage
logger = logging.getLogger("literal-upload")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

router = APIRouter(prefix="/literal", tags=["Literal Upload"])

# Fonction pour obtenir une connexion PostgreSQL
def get_postgres_connection():
    # Ru00e9cupu00e9rer les variables d'environnement pour la connexion PostgreSQL
    db_params = {
        'dbname': os.getenv('POSTGRES_DB', 'meeting_transcriber'),
        'user': os.getenv('POSTGRES_USER', 'meeting_transcriber_user'),
        'password': os.getenv('POSTGRES_PASSWORD', 'rlpb7cswwmJ5egbYXW3U1FF78g9kN308'),
        'host': os.getenv('POSTGRES_SERVER', 'dpg-d0lfghogjchc73f1mvjg-a.oregon-postgres.render.com'),
        'port': os.getenv('POSTGRES_PORT', '5432')
    }
    
    # Cru00e9er une connexion PostgreSQL
    conn = psycopg2.connect(**db_params)
    return conn

@router.post("/upload", response_model=dict, status_code=200)
async def literal_upload_meeting(
    file: UploadFile = File(..., description="Fichier audio u00e0 transcrire"),
    title: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Tu00e9lu00e9charge un fichier audio et cru00e9e une nouvelle ru00e9union avec transcription.
    Cette route utilise des requu00eates SQL directes avec des valu00e9urs litu00e9rales.
    
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
    
    # Convertir l'ID utilisateur en entier
    try:
        user_id_int = int(user_id)
        logger.info(f"ID utilisateur converti en entier: {user_id_int}")
    except (ValueError, TypeError):
        logger.error(f"Impossible de convertir l'ID utilisateur {user_id} en entier")
        raise HTTPException(
            status_code=400,
            detail="L'ID utilisateur doit u00eatre un entier valide"
        )
    
    # Connexion u00e0 PostgreSQL
    conn = None
    cursor = None
    
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
        user_upload_dir = os.path.join("uploads", str(user_id_int))
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
        
        # Obtenir une connexion PostgreSQL
        conn = get_postgres_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Vu00e9rifier si l'utilisateur existe avec une requu00eate litu00e9rale
        logger.info(f"Vu00e9rification de l'existence de l'utilisateur avec ID {user_id_int}")
        
        # Utiliser une requu00eate directe avec CAST explicite
        cursor.execute("SELECT COUNT(*) FROM users WHERE CAST(id AS TEXT) = CAST(%s AS TEXT)", (user_id_int,))
        user_exists = cursor.fetchone()[0]
        
        if not user_exists:
            logger.error(f"L'utilisateur avec l'ID {user_id_int} n'existe pas dans la base de donnu00e9es")
            raise HTTPException(
                status_code=404,
                detail=f"L'utilisateur avec l'ID {user_id_int} n'existe pas dans la base de donnu00e9es"
            )
        
        # Gu00e9nu00e9rer un ID unique pour la ru00e9union
        meeting_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        # Insu00e9rer la ru00e9union dans PostgreSQL avec des valu00e9urs litu00e9rales
        logger.info(f"Insertion de la ru00e9union {meeting_id} pour l'utilisateur {user_id_int}")
        
        # Utiliser une requu00eate SQL brute avec des valu00e9urs litu00e9rales
        query = f"""
        INSERT INTO meetings (
            id, user_id, title, file_url, 
            transcript_status, created_at
        ) VALUES (
            '{meeting_id}', 
            {user_id_int}, 
            '{title.replace("'", "''")}', 
            '{file_url.replace("'", "''")}', 
            'processing', 
            '{created_at.isoformat()}'
        )
        RETURNING *
        """
        
        logger.info(f"Exu00e9cution de la requu00eate: {query}")
        cursor.execute(query)
        
        # Ru00e9cupu00e9rer la ru00e9union cru00e9u00e9e
        meeting = cursor.fetchone()
        
        # Valider la transaction
        conn.commit()
        
        # Convertir la ru00e9union en dictionnaire
        meeting_dict = dict(meeting)
        
        # Lancer la transcription de maniu00e8re asynchrone
        logger.info(f"Lancement de la transcription pour la ru00e9union {meeting_dict['id']}")
        try:
            # Cru00e9er un thread et exu00e9cuter immu00e9diatement la transcription
            transcription_thread = threading.Thread(
                target=process_transcription,
                args=(meeting_dict["id"], file_url, user_id_int)
            )
            transcription_thread.daemon = False  # Permet au thread de continuer mu00eame si le serveur s'arru00eate
            transcription_thread.start()
            
            logger.info(f"Transcription lancu00e9e directement pour la ru00e9union {meeting_dict['id']}")
        except Exception as e:
            logger.error(f"Erreur lors du lancement de la transcription: {str(e)}")
            # Ne pas faire u00e9chouer la requu00eate, juste logger l'erreur
        
        return meeting_dict
        
    except Exception as e:
        logger.error(f"Erreur lors de l'upload: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Annuler la transaction si nu00e9cessaire
        if conn and not conn.closed:
            conn.rollback()
        
        raise HTTPException(
            status_code=500,
            detail=f"Une erreur s'est produite lors de l'upload: {str(e)}"
        )
    finally:
        # Fermer le curseur et la connexion
        if cursor:
            cursor.close()
        if conn and not conn.closed:
            conn.close()
        
        # Nettoyage des fichiers temporaires
        try:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            if os.path.exists(temp_output):
                os.unlink(temp_output)
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage des fichiers temporaires: {str(e)}")
