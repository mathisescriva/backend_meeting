#!/usr/bin/env python3
"""
Script pour vérifier le schéma de la base de données
"""

import logging
from app.db.database import get_db_connection, release_db_connection

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('schema-checker')

def check_db_schema():
    """Vérifie le schéma de la base de données"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Récupérer les informations sur la table meetings
        cursor.execute("PRAGMA table_info(meetings)")
        columns = cursor.fetchall()
        
        logger.info("Structure de la table 'meetings':")
        for col in columns:
            logger.info(f"- {col['name']} ({col['type']})")
        
        # Vérifier si les colonnes spécifiques existent
        has_duration = any(col['name'] == 'duration_seconds' for col in columns)
        has_speakers = any(col['name'] == 'speakers_count' for col in columns)
        
        if has_duration:
            logger.info("✅ La colonne 'duration_seconds' existe dans la table")
        else:
            logger.error("❌ La colonne 'duration_seconds' n'existe PAS dans la table!")
            
        if has_speakers:
            logger.info("✅ La colonne 'speakers_count' existe dans la table")
        else:
            logger.error("❌ La colonne 'speakers_count' n'existe PAS dans la table!")
    finally:
        release_db_connection(conn)

if __name__ == "__main__":
    check_db_schema()
