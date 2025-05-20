import assemblyai as aai
from app.db.queries import get_meetings_by_status, update_meeting
from app.services.assemblyai import process_completed_transcript
from dotenv import load_dotenv
import os
import logging
import re

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('transcription-fixer')

# Charger les variables d'environnement
load_dotenv()

# Configuration pour AssemblyAI
ASSEMBLY_AI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
aai.settings.api_key = ASSEMBLY_AI_API_KEY

def fix_processing_transcriptions():
    """Corrige les transcriptions bloquées en état 'processing'"""
    # Récupérer toutes les transcriptions en cours
    processing_meetings = get_meetings_by_status('processing')
    logger.info(f"Transcriptions en cours: {len(processing_meetings)}")
    
    if not processing_meetings:
        logger.info("Aucune transcription en cours trouvée")
        return
    
    # Créer un transcripteur
    transcriber = aai.Transcriber()
    
    # Traiter chaque transcription
    for meeting in processing_meetings:
        try:
            meeting_id = meeting['id']
            user_id = meeting['user_id']
            transcript_text = meeting.get('transcript_text', '')
            
            logger.info(f"Vérification de la réunion {meeting_id}")
            logger.info(f"Texte actuel: {transcript_text}")
            
            # Essayer d'extraire l'ID de transcription AssemblyAI du texte
            if transcript_text and 'ID:' in transcript_text:
                try:
                    # Extraire l'ID de transcription du texte
                    transcript_id = transcript_text.split('ID:')[-1].strip()
                    logger.info(f"ID de transcription AssemblyAI extrait: {transcript_id}")
                    
                    # Vérifier le statut de la transcription avec l'API AssemblyAI
                    # Dans la version 0.37.0, nous devons utiliser Transcript.get_transcript
                    transcript = aai.Transcript.get_transcript(transcript_id)
                    logger.info(f"Statut de la transcription {transcript_id}: {transcript.status}")
                    
                    if transcript.status == "completed":
                        # Traiter la transcription terminée
                        logger.info(f"Transcription {transcript_id} terminée, mise à jour de la base de données")
                        process_completed_transcript(meeting_id, user_id, transcript)
                        logger.info(f"Mise à jour réussie pour la réunion {meeting_id}")
                    elif transcript.status == "error":
                        # Gérer l'erreur
                        error_message = getattr(transcript, 'error', 'Unknown error')
                        logger.error(f"Erreur de transcription pour {meeting_id}: {error_message}")
                        update_meeting(meeting_id, user_id, {
                            "transcript_status": "error",
                            "transcript_text": f"Erreur lors de la transcription: {error_message}"
                        })
                    else:
                        # Toujours en cours
                        logger.info(f"Transcription {transcript_id} toujours en cours ({transcript.status})")
                except Exception as e:
                    logger.error(f"Erreur lors de la vérification de la transcription: {str(e)}")
            else:
                logger.warning(f"Impossible d'extraire l'ID de transcription pour la réunion {meeting_id}")
        except Exception as e:
            logger.error(f"Erreur lors du traitement de la réunion {meeting.get('id', 'unknown')}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info("Démarrage de la correction des transcriptions bloquées")
    fix_processing_transcriptions()
    logger.info("Correction terminée")
