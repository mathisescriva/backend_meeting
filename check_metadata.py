#!/usr/bin/env python3
"""
Script de diagnostic pour vérifier les métadonnées des réunions transcrites
"""

import sys
import logging
from app.db.database import get_db_connection, release_db_connection
from app.db.queries import get_meeting
import json

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('metadata-checker')

def check_meeting_metadata(meeting_id, user_id="1"):
    """Vérifie les métadonnées d'une réunion spécifique"""
    logger.info(f"Vérification des métadonnées pour la réunion {meeting_id}")
    
    meeting = get_meeting(meeting_id, user_id)
    
    if not meeting:
        logger.error(f"Réunion non trouvée: {meeting_id}")
        return
    
    # Afficher toutes les métadonnées
    logger.info(f"Métadonnées complètes: {json.dumps(meeting, indent=2)}")
    
    # Vérifier les métadonnées spécifiques
    logger.info(f"Statut de transcription: {meeting.get('transcript_status')}")
    
    duration = meeting.get('duration_seconds')
    if duration is not None:
        logger.info(f"Durée audio: {duration} secondes")
    else:
        logger.error("La durée audio n'est pas définie!")
    
    speakers = meeting.get('speakers_count')
    if speakers is not None:
        logger.info(f"Nombre de locuteurs: {speakers}")
    else:
        logger.error("Le nombre de locuteurs n'est pas défini!")
    
    # Vérifier la structure de la table
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Récupérer les infos sur la table
        cursor.execute("PRAGMA table_info(meetings)")
        columns = cursor.fetchall()
        
        has_duration = False
        has_speakers = False
        
        for col in columns:
            if col[1] == 'duration_seconds':
                has_duration = True
                logger.info("La colonne 'duration_seconds' existe dans la table")
            elif col[1] == 'speakers_count':
                has_speakers = True
                logger.info("La colonne 'speakers_count' existe dans la table")
        
        if not has_duration:
            logger.error("La colonne 'duration_seconds' n'existe PAS dans la table!")
        if not has_speakers:
            logger.error("La colonne 'speakers_count' n'existe PAS dans la table!")
        
    finally:
        release_db_connection(conn)

def main():
    if len(sys.argv) < 2:
        print("Usage: python check_metadata.py <meeting_id> [user_id]")
        sys.exit(1)
    
    meeting_id = sys.argv[1]
    user_id = sys.argv[2] if len(sys.argv) > 2 else "1"
    
    check_meeting_metadata(meeting_id, user_id)

if __name__ == "__main__":
    main()
