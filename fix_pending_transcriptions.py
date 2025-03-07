#!/usr/bin/env python3
"""
Script pour forcer la transcription des réunions en attente.
Ce script vérifie les réunions en statut 'pending' et tente de relancer leur transcription.
"""

import os
import sys
import sqlite3
from app.services.assemblyai import transcribe_meeting
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('fix_transcriptions')

def get_pending_meetings():
    """Récupère toutes les réunions en attente de transcription"""
    conn = sqlite3.connect('app.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id, user_id, file_url FROM meetings WHERE transcript_status='pending'")
        meetings = cursor.fetchall()
        return meetings
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des réunions en attente: {e}")
        return []
    finally:
        conn.close()

def restart_transcription(meeting_id, user_id, file_path):
    """Tente de redémarrer la transcription pour une réunion"""
    logger.info(f"Tentative de relance de la transcription pour la réunion {meeting_id}")
    
    try:
        # S'assurer que le chemin du fichier commence par /
        if not file_path.startswith('/'):
            file_path = '/' + file_path
            
        # Appeler la fonction de transcription
        transcribe_meeting(meeting_id, file_path, user_id)
        logger.info(f"Transcription relancée avec succès pour la réunion {meeting_id}")
        return True
    except Exception as e:
        logger.error(f"Échec de la relance pour la réunion {meeting_id}: {e}")
        return False

def main():
    logger.info("Démarrage de la vérification des transcriptions en attente...")
    
    # Récupérer toutes les réunions en attente
    pending_meetings = get_pending_meetings()
    logger.info(f"Nombre de réunions en attente: {len(pending_meetings)}")
    
    if not pending_meetings:
        logger.info("Aucune réunion en attente trouvée.")
        return
    
    # Tentative de relance pour chaque réunion
    success_count = 0
    for meeting in pending_meetings:
        meeting_id = meeting['id']
        user_id = meeting['user_id']
        file_path = meeting['file_url']
        
        logger.info(f"Traitement de la réunion {meeting_id} pour l'utilisateur {user_id}")
        logger.info(f"Fichier audio: {file_path}")
        
        if restart_transcription(meeting_id, user_id, file_path):
            success_count += 1
    
    logger.info(f"Traitement terminé. {success_count}/{len(pending_meetings)} réunions relancées avec succès.")

if __name__ == "__main__":
    main()
