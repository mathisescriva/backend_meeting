import os
import sqlite3
import sys
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from app.services.assemblyai import transcribe_meeting, process_transcription, upload_file_to_assemblyai, start_transcription, check_transcription_status
from app.db.database import get_db_connection, release_db_connection
from app.db.queries import update_meeting
from app.core.config import Settings

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('transcription-checker')

# Récupérer les paramètres de configuration
settings = Settings()
BASE_DIR = Path(__file__).resolve().parent

def get_pending_and_stuck_transcriptions():
    """Récupère les transcriptions en attente et celles bloquées en processing depuis longtemps"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Récupérer les transcriptions en attente
        cursor.execute(
            "SELECT id, title, user_id, file_url, created_at, transcript_status FROM meetings WHERE transcript_status = 'pending'"
        )
        pending = [dict(row) for row in cursor.fetchall()]
        
        # Récupérer les transcriptions potentiellement bloquées (en processing depuis plus de 30 minutes)
        one_hour_ago = (datetime.utcnow() - timedelta(minutes=30)).isoformat()
        cursor.execute(
            "SELECT id, title, user_id, file_url, created_at, transcript_status FROM meetings WHERE transcript_status = 'processing' AND created_at < ?",
            (one_hour_ago,)
        )
        stuck = [dict(row) for row in cursor.fetchall()]
        
        return pending + stuck
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
    return True, file_url  # Fichier distant, on suppose qu'il existe

def process_transcription_direct(meeting_id, file_url, user_id):
    """Traite directement une transcription (sans thread) pour déboguer"""
    try:
        logger.info(f"=== DÉBUT TRAITEMENT DIRECT pour la réunion {meeting_id} ===")
        
        # Mettre à jour le statut en "processing" si ce n'est pas déjà le cas
        update_meeting(meeting_id, user_id, {"transcript_status": "processing"})
        
        if file_url.startswith("/uploads/"):
            file_path = BASE_DIR / file_url.lstrip('/')
            if not os.path.exists(file_path):
                alt_path = BASE_DIR / "uploads" / file_url.replace('/uploads/', '')
                if os.path.exists(alt_path):
                    file_path = alt_path
                    logger.info(f"Utilisation du chemin alternatif pour le fichier: {file_path}")
                else:
                    raise FileNotFoundError(f"Fichier audio introuvable: {file_path} et {alt_path}")
            
            logger.info(f"Fichier à transcrire : {file_path}")
            logger.info(f"Le fichier existe : {os.path.exists(file_path)}")
            logger.info(f"Taille du fichier : {os.path.getsize(file_path)} octets")
            
            # Vérifier si le fichier est complet et non corrompu
            try:
                import magic
                file_mime = magic.Magic(mime=True).from_file(str(file_path))
                logger.info(f"Type MIME du fichier: {file_mime}")
            except Exception as e:
                logger.error(f"Erreur lors de la vérification du type MIME: {str(e)}")
        
        # Utiliser les fonctions du service unifié
        if file_url.startswith("/uploads/"):
            logger.info("Étape 1: Upload du fichier vers AssemblyAI")
            try:
                upload_url = upload_file_to_assemblyai(str(file_path))
                logger.info(f"Fichier uploadé vers AssemblyAI: {upload_url}")
            except Exception as e:
                logger.error(f"Erreur lors de l'upload: {str(e)}")
                raise
        else:
            upload_url = file_url
            logger.info(f"Utilisation de l'URL distante: {file_url}")
        
        logger.info("Étape 2: Démarrer la transcription")
        try:
            transcript_id = start_transcription(upload_url, format_text=True)
            logger.info(f"Transcription lancée avec ID: {transcript_id}")
        except Exception as e:
            logger.error(f"Erreur lors du démarrage de la transcription: {str(e)}")
            raise
        
        logger.info("Étape 3: Vérifier le statut de la transcription")
        max_retries = 5  # Limiter pour le débogage
        retry_delay = 10  # secondes
        
        for attempt in range(max_retries):
            logger.info(f"Vérification du statut, tentative {attempt+1}/{max_retries}")
            
            try:
                transcript_response = check_transcription_status(transcript_id)
                status = transcript_response.get('status')
                logger.info(f"Statut de la transcription: {status}")
                
                if status in ['completed', 'error']:
                    logger.info(f"Transcription terminée avec statut: {status}")
                    logger.info(f"Réponse complète: {transcript_response}")
                    
                    if status == 'completed':
                        transcription_text = transcript_response.get('text', '')
                        utterances = transcript_response.get('utterances', [])
                        audio_duration = transcript_response.get('audio_duration', 0)
                        
                        speakers_set = set()
                        if utterances:
                            formatted_text = []
                            for utterance in utterances:
                                speaker = utterance.get('speaker', 'Unknown')
                                speakers_set.add(speaker)
                                text = utterance.get('text', '')
                                # Format uniforme: "Speaker A: texte" avec préfixe "Speaker"
                                formatted_text.append(f"Speaker {speaker}: {text}")
                            
                            transcription_text = "\n".join(formatted_text)
                        
                        speakers_count = len(speakers_set)
                        
                        # Garantir qu'il y a toujours au moins 1 locuteur
                        if speakers_count == 0:
                            speakers_count = 1
                            logger.warning("Aucun locuteur détecté, on force à 1")
                        
                        update_data = {
                            "transcript_text": transcription_text,
                            "transcript_status": "completed",
                            "duration_seconds": int(audio_duration) if audio_duration else 0,
                            "speakers_count": speakers_count
                        }
                        
                        update_meeting(meeting_id, user_id, update_data)
                        logger.info("Base de données mise à jour avec la transcription complète")
                    else:
                        error_message = transcript_response.get('error', 'Unknown error')
                        logger.error(f"Erreur de transcription: {error_message}")
                        update_meeting(meeting_id, user_id, {"transcript_status": "error"})
                    
                    return
            except Exception as e:
                logger.error(f"Erreur lors de la vérification du statut: {str(e)}")
            
            time.sleep(retry_delay)
        
        logger.warning(f"Nombre maximum de tentatives atteint")
        update_meeting(meeting_id, user_id, {"transcript_status": "timeout"})
        
    except Exception as e:
        logger.error(f"Erreur globale lors du traitement direct: {str(e)}")
        try:
            update_meeting(meeting_id, user_id, {"transcript_status": "error"})
        except Exception as db_error:
            logger.error(f"Erreur lors de la mise à jour de la base de données: {str(db_error)}")
    finally:
        logger.info(f"=== FIN TRAITEMENT DIRECT pour la réunion {meeting_id} ===")

def process_transcriptions(meeting_id=None):
    """Traite manuellement les transcriptions"""
    meetings = get_pending_and_stuck_transcriptions()
    
    if not meetings:
        logger.info("Aucune transcription en attente ou bloquée trouvée.")
        return
    
    logger.info(f"Trouvé {len(meetings)} transcriptions à traiter.")
    
    for meeting in meetings:
        # Si un ID spécifique est fourni, ne traiter que celui-là
        if meeting_id and meeting['id'] != meeting_id:
            continue
        
        logger.info(f"=== Traitement de la réunion {meeting['id']} - {meeting['title']} ===")
        logger.info(f"Statut actuel: {meeting.get('transcript_status', 'inconnu')}")
        logger.info(f"Date de création: {meeting['created_at']}")
        
        logger.info(f"Vérification du fichier pour la réunion {meeting['id']}: {meeting['file_url']}")
        exists, file_path = check_file_exists(meeting['file_url'])
        
        if not exists:
            logger.error(f"Fichier introuvable pour la réunion {meeting['id']}: {file_path}")
            # Marquer comme erreur
            update_meeting(meeting['id'], meeting['user_id'], {"transcript_status": "error"})
            continue
        
        try:
            # Lancer la transcription directement (sans thread)
            process_transcription_direct(meeting['id'], meeting['file_url'], meeting['user_id'])
        except Exception as e:
            logger.error(f"Erreur lors du traitement: {str(e)}")
            # Marquer comme erreur
            update_meeting(meeting['id'], meeting['user_id'], {"transcript_status": "error"})

if __name__ == "__main__":
    # Si un ID de réunion est fourni en argument
    meeting_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    if meeting_id:
        logger.info(f"Traitement de la transcription spécifique: {meeting_id}")
    else:
        logger.info("Traitement de toutes les transcriptions en attente ou bloquées")
    
    # Afficher les informations sur les répertoires
    logger.info(f"BASE_DIR: {BASE_DIR}")
    logger.info(f"UPLOADS_DIR: {settings.UPLOADS_DIR}")
    
    # Vérifier si le répertoire d'uploads existe
    if os.path.exists(settings.UPLOADS_DIR):
        logger.info(f"Le répertoire d'uploads existe: {settings.UPLOADS_DIR}")
        # Lister son contenu
        uploads_content = os.listdir(settings.UPLOADS_DIR)
        logger.info(f"Contenu du répertoire d'uploads: {uploads_content}")
    else:
        logger.error(f"Le répertoire d'uploads n'existe pas: {settings.UPLOADS_DIR}")
    
    process_transcriptions(meeting_id)
