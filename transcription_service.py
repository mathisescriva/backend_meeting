#!/usr/bin/env python3
"""
Script de service de transcription automatique qui s'exécute en arrière-plan
pour traiter les réunions en attente (pending) ou bloquées en traitement (processing).

Exécutez ce script en parallèle du serveur principal pour garantir que
toutes les transcriptions sont traitées, même en cas de problème avec 
les threads de transcription du serveur principal.
"""

import os
import sys
import time
import logging
import sqlite3
import traceback
import magic
from pathlib import Path
from datetime import datetime, timedelta

# Configurer le logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('transcription-service')

# Initialiser la base de données
BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
DB_PATH = BASE_DIR / "app.db"

try:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    logger.info("Base de données initialisée avec succès")
except Exception as e:
    logger.error(f"Erreur lors de l'initialisation de la base de données: {e}")
    sys.exit(1)

# Importer les services après l'initialisation de BASE_DIR
sys.path.insert(0, str(BASE_DIR))
# Utiliser les versions synchrones au lieu des versions asynchrones
from app.services.assemblyai import _upload_file_to_assemblyai as upload_file_to_assemblyai
from app.services.assemblyai import _start_transcription_assemblyai as start_transcription
from app.services.assemblyai import _get_transcription_status_assemblyai as check_transcription_status
from app.core.config import settings

def get_pending_transcriptions(max_age_hours=24):
    """Récupère les transcriptions en attente qui ne sont pas trop anciennes"""
    cursor = conn.cursor()
    cutoff_date = datetime.now() - timedelta(hours=max_age_hours)
    cutoff_date_str = cutoff_date.strftime("%Y-%m-%dT%H:%M:%S")
    
    cursor.execute(
        "SELECT id, title, user_id, file_url, transcript_status, created_at FROM meetings " +
        "WHERE transcript_status IN ('pending', 'processing') AND created_at > ? " +
        "ORDER BY created_at ASC",
        (cutoff_date_str,)
    )
    
    meetings = cursor.fetchall()
    cursor.close()
    return [dict(meeting) for meeting in meetings]

def update_meeting_status(meeting_id, user_id, status, text=None):
    """Met à jour le statut et le texte de transcription d'une réunion"""
    cursor = conn.cursor()
    try:
        update_data = {"transcript_status": status}
        if text is not None:
            update_data["transcript_text"] = text
            
        placeholders = ", ".join([f"{k} = ?" for k in update_data.keys()])
        values = list(update_data.values())
        
        cursor.execute(
            f"UPDATE meetings SET {placeholders} WHERE id = ? AND user_id = ?",
            (*values, meeting_id, user_id)
        )
        conn.commit()
        logger.info(f"Statut de la réunion {meeting_id} mis à jour: {status}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du statut: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()

def process_transcription(meeting):
    """Traite une transcription en attente"""
    meeting_id = meeting['id']
    user_id = meeting['user_id']
    file_url = meeting['file_url']
    
    logger.info(f"=== Traitement de la réunion {meeting_id} - {meeting['title']} ===")
    logger.info(f"Statut actuel: {meeting['transcript_status']}")
    logger.info(f"Date de création: {meeting['created_at']}")
    
    # Vérifier le fichier
    if file_url.startswith("/uploads/"):
        file_path = UPLOADS_DIR.parent / file_url.lstrip('/')
        logger.info(f"Vérification du fichier: {file_path}, Existe: {os.path.exists(file_path)}")
        
        if not os.path.exists(file_path):
            logger.error(f"Fichier introuvable: {file_path}")
            update_meeting_status(
                meeting_id, 
                user_id, 
                "error", 
                "Le fichier audio est introuvable."
            )
            return False
            
        # Vérifier le type MIME
        try:
            file_mime = magic.Magic(mime=True).from_file(str(file_path))
            logger.info(f"Type MIME du fichier: {file_mime}")
            
            if not file_mime.startswith("audio/"):
                logger.error(f"Le fichier n'est pas un fichier audio valide: {file_mime}")
                update_meeting_status(
                    meeting_id, 
                    user_id, 
                    "error", 
                    f"Le fichier n'est pas un fichier audio valide. Type détecté: {file_mime}"
                )
                return False
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du type MIME: {e}")
    
    try:
        # Si déjà en processing, attendre un peu plus longtemps avant de reprendre
        if meeting['transcript_status'] == 'processing':
            # Si en processing depuis plus d'une heure, on considère que c'est bloqué
            created_time = datetime.fromisoformat(meeting['created_at'])
            if datetime.now() - created_time > timedelta(hours=1):
                logger.warning(f"La transcription est bloquée en processing depuis plus d'une heure")
            else:
                logger.info(f"La transcription est déjà en processing, on passe à la suivante")
                return True
        
        # Marquer comme en traitement
        update_meeting_status(meeting_id, user_id, "processing")
        
        # Upload du fichier vers AssemblyAI
        logger.info(f"Upload du fichier: {file_path}")
        upload_url = upload_file_to_assemblyai(str(file_path))
        logger.info(f"Fichier uploadé: {upload_url}")
        
        # Démarrer la transcription
        logger.info("Démarrage de la transcription")
        transcript_id = start_transcription(upload_url)
        logger.info(f"Transcription démarrée avec ID: {transcript_id}")
        
        # Vérifier le statut en boucle
        max_attempts = 30
        for attempt in range(1, max_attempts + 1):
            logger.info(f"Vérification du statut, tentative {attempt}/{max_attempts}")
            
            # Récupérer le statut de la transcription
            transcript_response = check_transcription_status(transcript_id)
            status = transcript_response.get('status')
            
            if status == "completed":
                # Récupérer le texte avec mise en forme par interlocuteur
                transcript_text = transcript_response.get('text', '')
                
                # Si des informations par interlocuteur sont disponibles
                utterances = transcript_response.get('utterances', [])
                if utterances:
                    transcript_text = ""
                    for utterance in utterances:
                        speaker = utterance.get('speaker', 'Speaker')
                        text = utterance.get('text', '')
                        if text:
                            transcript_text += f"{speaker}: {text}\n"
                
                logger.info("Transcription terminée avec succès")
                update_meeting_status(meeting_id, user_id, "completed", transcript_text)
                return True
            elif status == "error":
                error_message = transcript_response.get('error', 'Unknown error')
                logger.error(f"Transcription terminée avec erreur: {error_message}")
                update_meeting_status(meeting_id, user_id, "error", f"Erreur lors de la transcription: {error_message}")
                return False
            
            # Attendre plus longtemps entre les tentatives
            wait_time = min(10 * attempt, 60)  # Augmente progressivement, plafonne à 60s
            logger.info(f"En attente de transcription, statut actuel: {status}. Nouvelle vérification dans {wait_time}s")
            time.sleep(wait_time)
        
        # Si on arrive ici, c'est que la transcription prend trop de temps
        logger.warning("Transcription trop longue, marquée comme erreur")
        update_meeting_status(
            meeting_id, 
            user_id, 
            "error", 
            "La transcription a pris trop de temps et a été interrompue."
        )
        return False
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement de la transcription: {str(e)}")
        logger.error(traceback.format_exc())
        update_meeting_status(
            meeting_id, 
            user_id, 
            "error", 
            f"Erreur lors du traitement: {str(e)}"
        )
        return False

def main(single_run=False, check_interval=60):
    """Fonction principale qui vérifie régulièrement les transcriptions en attente"""
    logger.info("Démarrage du service de transcription")
    
    try:
        while True:
            # Récupérer les transcriptions en attente
            pending_transcriptions = get_pending_transcriptions()
            logger.info(f"Trouvé {len(pending_transcriptions)} transcriptions en attente")
            
            # Traiter chaque transcription
            for meeting in pending_transcriptions:
                try:
                    process_transcription(meeting)
                except Exception as e:
                    logger.error(f"Erreur lors du traitement de la réunion {meeting['id']}: {str(e)}")
                    logger.error(traceback.format_exc())
            
            # Si mode single_run, sortir après un cycle
            if single_run:
                logger.info("Mode single-run, arrêt du service")
                break
                
            # Attendre avant la prochaine vérification
            logger.info(f"En attente de nouvelles transcriptions ({check_interval}s)")
            time.sleep(check_interval)
            
    except KeyboardInterrupt:
        logger.info("Arrêt du service de transcription")
    except Exception as e:
        logger.error(f"Erreur non gérée: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        conn.close()
        
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Service de transcription automatique")
    parser.add_argument("--single-run", action="store_true", help="Exécuter une seule fois puis s'arrêter")
    parser.add_argument("--interval", type=int, default=60, help="Intervalle entre les vérifications (secondes)")
    
    args = parser.parse_args()
    
    main(single_run=args.single_run, check_interval=args.interval)
