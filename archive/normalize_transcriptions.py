#!/usr/bin/env python3
"""
Script pour normaliser le format de toutes les transcriptions existantes dans la base de données.
A exécuter une seule fois pour convertir 'X: texte' en 'Speaker X: texte'
"""

import sqlite3
import re
import logging
import os
from app.core.config import settings

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("normalize-transcriptions")

def get_db_connection():
    """Établir une connexion à la base de données SQLite"""
    db_path = settings.DATABASE_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def normalize_transcript_format(text):
    """
    Normalise le format des transcriptions pour être cohérent
    Convertit tout format de transcription 'X: texte' 
    vers un format standard 'Speaker X: texte'
    """
    if not text:
        return text
        
    # Pattern pour détecter "X: " au début d'une ligne qui n'est pas précédé par "Speaker "
    pattern = r'(^|\n)(?!Speaker )([A-Z0-9]+): '
    replacement = r'\1Speaker \2: '
    
    # Remplacer "X: " par "Speaker X: "
    normalized_text = re.sub(pattern, replacement, text)
    
    return normalized_text

def normalize_all_transcriptions():
    """Normalise toutes les transcriptions dans la base de données"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Récupérer toutes les transcriptions
        cursor.execute("SELECT id, transcript_text FROM meetings WHERE transcript_text IS NOT NULL")
        meetings = cursor.fetchall()
        
        logger.info(f"Trouvé {len(meetings)} transcriptions à normaliser")
        
        normalized_count = 0
        unchanged_count = 0
        
        for meeting in meetings:
            meeting_id = meeting['id']
            original_text = meeting['transcript_text']
            
            if not original_text:
                logger.warning(f"Transcription vide pour la réunion {meeting_id}, ignorée")
                continue
                
            normalized_text = normalize_transcript_format(original_text)
            
            # Vérifier si le texte a été modifié
            if normalized_text != original_text:
                logger.info(f"Normalisation de la transcription pour la réunion {meeting_id}")
                cursor.execute(
                    "UPDATE meetings SET transcript_text = ? WHERE id = ?",
                    (normalized_text, meeting_id)
                )
                normalized_count += 1
            else:
                logger.info(f"Transcription déjà au format correct pour la réunion {meeting_id}")
                unchanged_count += 1
        
        # Valider les modifications
        conn.commit()
        
        logger.info(f"Migration terminée: {normalized_count} transcriptions normalisées, {unchanged_count} déjà au format correct")
        
    except Exception as e:
        logger.error(f"Erreur lors de la normalisation des transcriptions: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    logger.info("Démarrage de la normalisation des transcriptions...")
    normalize_all_transcriptions()
    logger.info("Terminé!")
