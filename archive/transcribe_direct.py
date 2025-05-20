#!/usr/bin/env python3
"""
Script pour transcrire un fichier audio directement avec le SDK AssemblyAI
et mettre à jour une réunion existante ou en créer une nouvelle.
"""

import os
import sys
import logging
import json
import uuid
from dotenv import load_dotenv
from app.db.database import get_db_connection, release_db_connection
from app.db.queries import update_meeting, get_meeting
from app.services.assemblyai import transcribe_with_sdk

# Charger les variables d'environnement
load_dotenv()

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('transcribe-direct')

def create_meeting(user_id, title, file_url):
    """Crée une nouvelle réunion dans la base de données"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        meeting_id = str(uuid.uuid4())
        
        cursor.execute(
            """
            INSERT INTO meetings (id, user_id, title, recording_url, transcript_status, created_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            """,
            (meeting_id, user_id, title, file_url, "pending")
        )
        
        conn.commit()
        logger.info(f"Nouvelle réunion créée: {meeting_id}")
        return meeting_id
    except Exception as e:
        logger.error(f"Erreur lors de la création de la réunion: {str(e)}")
        return None
    finally:
        release_db_connection(conn)

def transcribe_and_update(audio_url, meeting_id=None, user_id=None, title=None):
    """
    Transcrit un fichier audio et met à jour une réunion existante
    ou en crée une nouvelle si aucun meeting_id n'est fourni
    """
    try:
        # Vérifier si on doit créer une nouvelle réunion
        if meeting_id is None:
            if user_id is None or title is None:
                logger.error("Pour créer une nouvelle réunion, user_id et title sont requis")
                return False
                
            meeting_id = create_meeting(user_id, title, audio_url)
            if not meeting_id:
                logger.error("Échec de la création de la réunion")
                return False
                
            logger.info(f"Nouvelle réunion créée: {meeting_id}")
        else:
            # Vérifier que la réunion existe
            if user_id is None:
                logger.error("user_id est requis pour mettre à jour une réunion existante")
                return False
                
            meeting = get_meeting(meeting_id, user_id)
            if not meeting:
                logger.error(f"Réunion non trouvée: {meeting_id}")
                return False
                
            logger.info(f"Réunion existante trouvée: {meeting['title']}")
        
        # Mettre à jour le statut à "processing"
        update_meeting(meeting_id, user_id, {"transcript_status": "processing"})
        
        # Transcrire l'audio avec le SDK
        logger.info(f"Démarrage de la transcription pour {audio_url}")
        result = transcribe_with_sdk(audio_url)
        
        if result["status"] == "completed":
            # Mettre à jour la réunion avec les résultats
            update_data = {
                "transcript_status": "completed",
                "transcript_text": result["text"],
                "duration_seconds": result["audio_duration"],
                "speakers_count": result["speakers_count"]
            }
            
            success = update_meeting(meeting_id, user_id, update_data)
            
            if success:
                logger.info(f"Réunion {meeting_id} mise à jour avec succès")
                logger.info(f"Durée: {result['audio_duration']} secondes")
                logger.info(f"Locuteurs: {result['speakers_count']}")
                return True
            else:
                logger.error(f"Échec de la mise à jour de la réunion {meeting_id}")
                return False
        else:
            # En cas d'erreur
            error_msg = result.get("error", "Erreur inconnue")
            logger.error(f"Erreur de transcription: {error_msg}")
            
            # Mettre à jour le statut à "error"
            update_meeting(meeting_id, user_id, {
                "transcript_status": "error",
                "transcript_text": error_msg
            })
            return False
    
    except Exception as e:
        logger.error(f"Erreur lors de la transcription: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Mettre à jour le statut à "error" si possible
        if meeting_id and user_id:
            update_meeting(meeting_id, user_id, {
                "transcript_status": "error",
                "transcript_text": str(e)
            })
        return False

def main():
    if len(sys.argv) < 3:
        print("Usage: python transcribe_direct.py <audio_url> <user_id> [meeting_id] [title]")
        print("  Si meeting_id est fourni, la réunion existante sera mise à jour")
        print("  Si meeting_id n'est pas fourni, title est requis pour créer une nouvelle réunion")
        sys.exit(1)
    
    audio_url = sys.argv[1]
    user_id = sys.argv[2]
    
    meeting_id = None
    title = None
    
    if len(sys.argv) > 3:
        meeting_id = sys.argv[3]
    
    if len(sys.argv) > 4:
        title = sys.argv[4]
    
    if meeting_id is None and title is None:
        print("ERREUR: Si meeting_id n'est pas fourni, title est requis")
        sys.exit(1)
    
    # Lancer la transcription et la mise à jour
    success = transcribe_and_update(audio_url, meeting_id, user_id, title)
    
    if success:
        print("✅ Transcription et mise à jour réussies!")
        sys.exit(0)
    else:
        print("❌ Échec de la transcription ou de la mise à jour")
        sys.exit(1)

if __name__ == "__main__":
    main()
