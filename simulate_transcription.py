#!/usr/bin/env python3
"""
Script pour simuler le traitement d'une transcription terminée et vérifier
la mise à jour des métadonnées dans la base de données.
"""

import sys
import logging
import json
import os
import traceback
from app.db.queries import update_meeting, get_meeting
from app.services.assemblyai import check_transcription_status

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('transcription-simulator')

def simulate_transcription(transcript_id, meeting_id, user_id):
    """Simule le traitement d'une transcription terminée"""
    try:
        logger.info(f"Simulation de traitement pour transcription ID: {transcript_id}")
        logger.info(f"Meeting ID: {meeting_id}, User ID: {user_id}")
        
        # Vérifier si la réunion existe
        meeting = get_meeting(meeting_id, user_id)
        if not meeting:
            logger.error(f"Réunion non trouvée: {meeting_id}")
            return
        
        logger.info(f"Réunion trouvée: {meeting['title']}")
        
        # Récupérer le statut de la transcription
        status, transcript_text, audio_duration, speakers_count = check_transcription_status(transcript_id)
        
        logger.info(f"Statut de la transcription: {status}")
        logger.info(f"Durée audio: {audio_duration}")
        logger.info(f"Nombre de locuteurs: {speakers_count}")
        
        if status == 'completed':
            # S'assurer que les valeurs sont correctes
            if audio_duration is None:
                audio_duration = 0
                logger.warning("La durée audio est None, remplacée par 0")
            
            if speakers_count is None or speakers_count == 0:
                speakers_count = 1
                logger.warning("Le nombre de locuteurs est None ou 0, remplacé par 1")
            
            # Mettre à jour la réunion
            update_data = {
                "transcript_status": status,
                "transcript_text": transcript_text,
                "duration_seconds": audio_duration,
                "speakers_count": speakers_count
            }
            
            logger.info(f"Données de mise à jour: {json.dumps(update_data, default=str)}")
            
            success = update_meeting(meeting_id, user_id, update_data)
            
            if success:
                logger.info("✅ Mise à jour réussie!")
                
                # Vérifier que les données ont bien été enregistrées
                updated_meeting = get_meeting(meeting_id, user_id)
                logger.info("Métadonnées après mise à jour:")
                logger.info(f"  Durée: {updated_meeting.get('duration_seconds')}")
                logger.info(f"  Locuteurs: {updated_meeting.get('speakers_count')}")
                
                if updated_meeting.get('duration_seconds') == audio_duration:
                    logger.info("✅ La durée a été correctement enregistrée")
                else:
                    logger.error(f"❌ La durée n'a pas été correctement enregistrée: {updated_meeting.get('duration_seconds')} != {audio_duration}")
                
                if updated_meeting.get('speakers_count') == speakers_count:
                    logger.info("✅ Le nombre de locuteurs a été correctement enregistré")
                else:
                    logger.error(f"❌ Le nombre de locuteurs n'a pas été correctement enregistré: {updated_meeting.get('speakers_count')} != {speakers_count}")
            else:
                logger.error("❌ Échec de la mise à jour!")
        else:
            logger.error(f"La transcription n'est pas terminée (statut: {status})")
    
    except Exception as e:
        logger.error(f"Erreur lors de la simulation: {str(e)}")
        logger.error(traceback.format_exc())

def main():
    if len(sys.argv) < 4:
        print("Usage: python simulate_transcription.py <transcript_id> <meeting_id> <user_id>")
        sys.exit(1)
    
    transcript_id = sys.argv[1]
    meeting_id = sys.argv[2]
    user_id = sys.argv[3]
    
    simulate_transcription(transcript_id, meeting_id, user_id)

if __name__ == "__main__":
    main()
