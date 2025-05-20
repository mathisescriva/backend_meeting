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
from ..services.assemblyai import process_transcription
from ..core.config import settings

# Logger pour le du00e9bogage
logger = logging.getLogger("psycopg2-upload")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

router = APIRouter(prefix="/psycopg2", tags=["PostgreSQL Direct Upload"])

# Fonction pour obtenir une connexion PostgreSQL
def get_postgres_connection():
    try:
        conn = psycopg2.connect(
            dbname=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            host=settings.POSTGRES_SERVER,
            port=settings.POSTGRES_PORT
        )
        return conn
    except Exception as e:
        logger.error(f"Erreur de connexion u00e0 PostgreSQL: {str(e)}")
        raise e

@router.post("/upload", response_model=dict, status_code=200)
async def psycopg2_upload_meeting(
    file: UploadFile = File(..., description="Fichier audio u00e0 transcrire"),
    title: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Tu00e9lu00e9charge un fichier audio et cru00e9e une nouvelle ru00e9union avec transcription.
    Cette route utilise directement psycopg2 pour interagir avec la base de donnu00e9es PostgreSQL.
    
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
        # Vérifier si l'ID est déjà un entier ou une chaîne
        if isinstance(current_user['id'], int):
            user_id = current_user['id']
        else:
            user_id = int(current_user['id'])
        logger.info(f"Utilisation de l'ID utilisateur (converti en entier): {user_id} (type: {type(user_id)})")
    except (ValueError, TypeError):
        logger.error(f"L'ID utilisateur {current_user['id']} n'est pas un entier valide")
        raise HTTPException(
            status_code=400,
            detail=f"L'ID utilisateur n'est pas un entier valide"
        )
    
    # Vu00e9rifier que l'utilisateur existe dans la base de donnu00e9es
    conn = None
    cursor = None
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        # Vu00e9rifier si l'utilisateur existe - approche alternative
        logger.info(f"Vu00e9rification de l'existence de l'utilisateur avec ID: {user_id} (type: {type(user_id)})")
        
        # Ru00e9cupu00e9rer tous les utilisateurs pour du00e9bogage
        cursor.execute("SELECT id, email FROM users")
        all_users = cursor.fetchall()
        logger.info(f"Utilisateurs dans la base de donnu00e9es: {all_users}")
        
        # Vu00e9rifier manuellement si l'utilisateur existe
        user_exists = False
        for db_user in all_users:
            logger.info(f"Comparaison: DB user ID {db_user[0]} (type: {type(db_user[0])}) avec user_id {user_id} (type: {type(user_id)})")
            
            # Essayer de comparer les IDs en convertissant les deux en string pour u00e9viter les probu00e8mes de type
            try:
                # Essayer d'abord une comparaison directe
                if db_user[0] == user_id:
                    user_exists = True
                    logger.info(f"Utilisateur trouvu00e9 avec ID {user_id} (comparaison directe)")
                    break
                    
                # Ensuite, essayer de comparer les deux en tant que string
                if str(db_user[0]) == str(user_id):
                    user_exists = True
                    logger.info(f"Utilisateur trouvu00e9 avec ID {user_id} (comparaison string)")
                    break
                    
                # Enfin, essayer de comparer en convertissant en entier si possible
                if isinstance(db_user[0], int) and db_user[0] == user_id:
                    user_exists = True
                    logger.info(f"Utilisateur trouvu00e9 avec ID {user_id} (comparaison entier)")
                    break
            except Exception as e:
                logger.error(f"Erreur lors de la comparaison des IDs: {str(e)}")
        
        if not user_exists:
            logger.error(f"L'utilisateur avec l'ID {user_id} n'existe pas dans la base de donnu00e9es")
            raise HTTPException(
                status_code=404,
                detail=f"L'utilisateur avec l'ID {user_id} n'existe pas dans la base de donnu00e9es"
            )
        
        logger.info(f"L'utilisateur avec l'ID {user_id} existe dans la base de donnu00e9es")
    except Exception as e:
        logger.error(f"Erreur lors de la vu00e9rification de l'utilisateur: {str(e)}")
        if conn:
            conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la vu00e9rification de l'utilisateur: {str(e)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
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
        meeting_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        # Insu00e9rer la ru00e9union directement avec psycopg2
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        # Afficher la structure de la table meetings pour du00e9bogage
        cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'meetings'
        ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        logger.info("Structure de la table meetings:")
        for col in columns:
            logger.info(f"  {col[0]}: {col[1]}")
        
        # Insu00e9rer uniquement les colonnes essentielles
        cursor.execute("""
        INSERT INTO meetings (id, user_id, title, file_url, transcript_status, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, user_id, title, file_url, transcript_status, created_at
        """, (meeting_id, user_id, title, file_url, "processing", created_at))
        
        # Ru00e9cupu00e9rer les donnu00e9es de la ru00e9union insu00e9ru00e9e
        meeting_data = cursor.fetchone()
        conn.commit()
        
        # Convertir les donnu00e9es en dictionnaire
        meeting = {
            "id": meeting_data[0],
            "user_id": meeting_data[1],
            "title": meeting_data[2],
            "file_url": meeting_data[3],
            "transcript_status": meeting_data[4],
            "created_at": meeting_data[5].isoformat() if meeting_data[5] else None
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
        if 'conn' in locals() and conn:
            conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Une erreur s'est produite lors de l'upload: {str(e)}"
        )
    finally:
        # Fermer la connexion PostgreSQL
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()
        
        # Nettoyage des fichiers temporaires
        try:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            if os.path.exists(temp_output):
                os.unlink(temp_output)
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage des fichiers temporaires: {str(e)}")
