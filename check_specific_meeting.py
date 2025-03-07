import os
import sqlite3
import sys
import logging
import json
import time
import requests
from pathlib import Path
from app.db.database import get_db_connection, release_db_connection
from app.db.queries import update_meeting
from app.core.config import Settings

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('meeting-checker')

# Récupérer les paramètres de configuration
settings = Settings()
BASE_DIR = Path(__file__).resolve().parent

def get_meeting_details(meeting_id):
    """Récupère les détails d'un meeting spécifique"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, user_id, file_url, created_at, transcript_status FROM meetings WHERE id = ?",
            (meeting_id,)
        )
        meeting = cursor.fetchone()
        if meeting:
            return dict(meeting)
        return None
    finally:
        release_db_connection(conn)

def check_file_exists(file_url):
    """Vérifie si le fichier audio existe"""
    if file_url.startswith('/uploads/'):
        file_path = BASE_DIR / file_url.lstrip('/')
        exists = os.path.exists(file_path)
        logger.info(f"Vérification du fichier: {file_path}, Existe: {exists}")
        
        # Si le fichier n'existe pas, essayons d'autres chemins possibles
        if not exists:
            alt_path = BASE_DIR / "uploads" / file_url.replace('/uploads/', '')
            alt_exists = os.path.exists(alt_path)
            logger.info(f"Chemin alternatif: {alt_path}, Existe: {alt_exists}")
            
            if alt_exists:
                return True, alt_path
                
        return exists, file_path
    return True, file_url

def reset_transcription(meeting_id, user_id):
    """Réinitialise le statut de transcription à 'pending' pour réessayer"""
    try:
        update_meeting(meeting_id, user_id, {"transcript_status": "pending"})
        logger.info(f"Statut de transcription réinitialisé pour la réunion {meeting_id}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la réinitialisation du statut: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_specific_meeting.py <meeting_id> [reset]")
        sys.exit(1)
        
    meeting_id = sys.argv[1]
    should_reset = len(sys.argv) > 2 and sys.argv[2].lower() == "reset"
    
    meeting = get_meeting_details(meeting_id)
    if not meeting:
        logger.error(f"Réunion non trouvée: {meeting_id}")
        sys.exit(1)
    
    logger.info(f"=== Détails de la réunion {meeting_id} ===")
    logger.info(f"Titre: {meeting.get('title')}")
    logger.info(f"Utilisateur: {meeting.get('user_id')}")
    logger.info(f"Statut: {meeting.get('transcript_status')}")
    logger.info(f"Date de création: {meeting.get('created_at')}")
    
    file_exists, file_path = check_file_exists(meeting.get('file_url', ''))
    if not file_exists:
        logger.error(f"Le fichier audio n'existe pas: {meeting.get('file_url')}")
        
        # Si le fichier n'existe pas et que nous voulons réinitialiser, marquer comme erreur
        if should_reset:
            update_meeting(meeting_id, meeting.get('user_id'), {"transcript_status": "error"})
            logger.info("La transcription a été marquée comme erreur car le fichier n'existe pas.")
    else:
        logger.info(f"Le fichier audio existe: {file_path}")
        file_size = os.path.getsize(file_path)
        logger.info(f"Taille du fichier: {file_size} octets")
        
        try:
            import magic
            file_mime = magic.Magic(mime=True).from_file(str(file_path))
            logger.info(f"Type MIME du fichier: {file_mime}")
            
            # Si le fichier est trop petit ou n'est pas un fichier audio valide
            if file_size < 1000 or not file_mime.startswith('audio/'):
                logger.error(f"Le fichier ne semble pas être un fichier audio valide. Type MIME: {file_mime}, Taille: {file_size}")
                if should_reset:
                    update_meeting(meeting_id, meeting.get('user_id'), {"transcript_status": "error"})
                    logger.info("La transcription a été marquée comme erreur car le fichier n'est pas valide.")
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du type MIME: {str(e)}")
    
    # Réinitialiser la transcription si demandé et si le fichier est valide
    if should_reset and file_exists and file_size >= 1000:
        if reset_transcription(meeting_id, meeting.get('user_id')):
            logger.info("La transcription a été réinitialisée. Vous pouvez maintenant relancer le processus.")
        else:
            logger.error("Échec de la réinitialisation de la transcription.")
