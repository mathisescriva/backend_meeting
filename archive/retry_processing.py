#!/usr/bin/env python3
"""
Script pour relancer manuellement le traitement d'une réunion bloquée.
"""

import sys
import logging
from app.db.queries import get_meeting, update_meeting
from app.services.assemblyai import _process_transcription

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('retry-processing')

def retry_transcription(meeting_id, user_id):
    """Relance le traitement d'une réunion spécifique"""
    logger.info(f"Récupération des informations de la réunion {meeting_id}")
    meeting = get_meeting(meeting_id, user_id)
    
    if not meeting:
        logger.error(f"Réunion {meeting_id} non trouvée pour l'utilisateur {user_id}")
        return False
    
    status = meeting.get('transcript_status')
    logger.info(f"Statut actuel de la réunion: {status}")
    
    file_url = meeting.get('file_url')
    if not file_url:
        logger.error(f"URL du fichier manquante pour la réunion {meeting_id}")
        return False
    
    logger.info(f"Mise à jour du statut à 'processing'")
    update_meeting(meeting_id, user_id, {"transcript_status": "processing"})
    
    logger.info(f"Relancement du traitement de transcription pour {meeting_id}")
    _process_transcription(meeting_id, file_url, user_id)
    
    logger.info(f"Traitement terminé pour {meeting_id}")
    return True

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python retry_processing.py <meeting_id> <user_id>")
        sys.exit(1)
    
    meeting_id = sys.argv[1]
    user_id = sys.argv[2]
    
    logger.info(f"Tentative de retraitement de la réunion {meeting_id} pour l'utilisateur {user_id}")
    success = retry_transcription(meeting_id, user_id)
    
    if success:
        logger.info("Retraitement terminé")
    else:
        logger.error("Échec du retraitement")
        sys.exit(1)
