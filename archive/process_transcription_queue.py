#!/usr/bin/env python3
"""
Script pour traiter la queue de transcription.
À exécuter périodiquement pour reprendre les transcriptions interrompues.

Peut être configuré comme un service systemd ou avec cron :
* * * * * cd /path/to/app && python process_transcription_queue.py >> /path/to/logs/queue_processor.log 2>&1
"""

import os
import json
import logging
import time
from datetime import datetime, timedelta
from app.core.config import settings
from app.services.assemblyai import _process_transcription
from app.db.queries import get_meeting, update_meeting

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('queue-processor')

def process_queue():
    """Traite tous les fichiers dans le répertoire de queue"""
    queue_dir = os.path.join(settings.UPLOADS_DIR.parent, "queue")
    
    if not os.path.exists(queue_dir):
        logger.info(f"Le répertoire de queue n'existe pas encore: {queue_dir}")
        return
    
    queue_files = [f for f in os.listdir(queue_dir) if f.endswith('.json')]
    logger.info(f"Traitement de {len(queue_files)} fichiers dans la queue")
    
    for queue_file in queue_files:
        try:
            queue_file_path = os.path.join(queue_dir, queue_file)
            
            # Lire les données du fichier
            with open(queue_file_path, 'r') as f:
                data = json.load(f)
            
            meeting_id = data.get('meeting_id')
            file_url = data.get('file_url')
            user_id = data.get('user_id')
            created_at = data.get('created_at')
            
            # Vérifier l'ancienneté du fichier
            if created_at:
                created_datetime = datetime.fromisoformat(created_at)
                age = datetime.now() - created_datetime
                # Si le fichier a plus de 24h, considérer qu'il est obsolète
                if age > timedelta(hours=24):
                    logger.warning(f"Fichier de queue obsolète (>24h): {queue_file}")
                    os.remove(queue_file_path)
                    continue
            
            if not all([meeting_id, file_url, user_id]):
                logger.error(f"Données incomplètes dans le fichier de queue: {queue_file}")
                continue
            
            # Vérifier que la réunion existe et qu'elle est toujours en attente/processing
            meeting = get_meeting(meeting_id, user_id)
            if not meeting:
                logger.warning(f"La réunion {meeting_id} n'existe plus, suppression du fichier de queue")
                os.remove(queue_file_path)
                continue
            
            status = meeting.get('transcript_status')
            if status not in ['pending', 'processing']:
                logger.info(f"La réunion {meeting_id} a déjà le statut {status}, pas besoin de retraitement")
                os.remove(queue_file_path)
                continue
            
            logger.info(f"Traitement de la transcription pour la réunion {meeting_id} (statut actuel: {status})")
            
            # Mettre à jour le statut en "processing" si nécessaire
            if status == 'pending':
                update_meeting(meeting_id, user_id, {"transcript_status": "processing"})
            
            # Traiter la transcription
            _process_transcription(meeting_id, file_url, user_id)
            
            # Supprimer le fichier de queue
            os.remove(queue_file_path)
            logger.info(f"Transcription terminée pour {meeting_id}, fichier de queue supprimé")
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement du fichier {queue_file}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info("Démarrage du processeur de queue de transcription")
    process_queue()
    logger.info("Traitement de la queue terminé")
