#!/usr/bin/env python3
"""
Script pour lister toutes les réunions dans la base de données
"""

import logging
from app.db.database import get_db_connection, release_db_connection

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('meeting-lister')

def list_all_meetings():
    """Liste toutes les réunions dans la base de données"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, title, user_id, transcript_status, created_at, 
                   duration_seconds, speakers_count
            FROM meetings
            ORDER BY created_at DESC
            LIMIT 20
        """)
        
        meetings = cursor.fetchall()
        
        if not meetings:
            logger.info("Aucune réunion trouvée dans la base de données")
            return
        
        logger.info(f"Total des réunions récentes: {len(meetings)}")
        
        for meeting in meetings:
            logger.info("---------------------------------------")
            logger.info(f"ID: {meeting['id']}")
            logger.info(f"Titre: {meeting['title']}")
            logger.info(f"Utilisateur: {meeting['user_id']}")
            logger.info(f"Statut: {meeting['transcript_status']}")
            logger.info(f"Créée le: {meeting['created_at']}")
            logger.info(f"Durée: {meeting['duration_seconds'] or 'Non définie'}")
            logger.info(f"Locuteurs: {meeting['speakers_count'] or 'Non défini'}")
            
    finally:
        release_db_connection(conn)

if __name__ == "__main__":
    list_all_meetings()
