import assemblyai as aai
from app.db.queries import get_meetings_by_status, update_meeting
from app.services.assemblyai import process_completed_transcript
from dotenv import load_dotenv
import os
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('transcription-updater')

# Charger les variables d'environnement
load_dotenv()

# Configuration pour AssemblyAI
ASSEMBLY_AI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
aai.settings.api_key = ASSEMBLY_AI_API_KEY

def update_transcription_status():
    """Met u00e0 jour le statut des transcriptions en cours"""
    # Ru00e9cupu00e9rer toutes les transcriptions en cours
    processing_meetings = get_meetings_by_status('processing')
    logger.info(f"Transcriptions en cours: {len(processing_meetings)}")
    
    if not processing_meetings:
        logger.info("Aucune transcription en cours trouvu00e9e")
        return
    
    # Traiter chaque transcription
    for meeting in processing_meetings:
        try:
            meeting_id = meeting['id']
            user_id = meeting['user_id']
            transcript_text = meeting.get('transcript_text', '')
            
            logger.info(f"Vu00e9rification de la ru00e9union {meeting_id}")
            logger.info(f"Texte actuel: {transcript_text}")
            
            # Essayer d'extraire l'ID de transcription AssemblyAI du texte
            if transcript_text and 'ID:' in transcript_text:
                try:
                    # Extraire l'ID de transcription du texte
                    transcript_id = transcript_text.split('ID:')[-1].strip()
                    logger.info(f"ID de transcription AssemblyAI extrait: {transcript_id}")
                    
                    # Cru00e9er un transcripteur
                    transcriber = aai.Transcriber()
                    
                    # Ru00e9cupu00e9rer la transcription par son ID
                    # Selon la documentation, on utilise la mu00e9thode transcribe avec l'ID
                    transcript = transcriber.transcribe(transcript_id)
                    
                    logger.info(f"Statut de la transcription {transcript_id}: {transcript.status}")
                    
                    if transcript.status == aai.TranscriptStatus.completed:
                        # Traiter la transcription terminu00e9e
                        logger.info(f"Transcription {transcript_id} terminu00e9e, mise u00e0 jour de la base de donnu00e9es")
                        process_completed_transcript(meeting_id, user_id, transcript)
                        logger.info(f"Mise u00e0 jour ru00e9ussie pour la ru00e9union {meeting_id}")
                    elif transcript.status == aai.TranscriptStatus.error:
                        # Gu00e9rer l'erreur
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
                    logger.error(f"Erreur lors de la vu00e9rification de la transcription: {str(e)}")
                    logger.error(f"Du00e9tails: {e.__class__.__name__}: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
            else:
                logger.warning(f"Impossible d'extraire l'ID de transcription pour la ru00e9union {meeting_id}")
        except Exception as e:
            logger.error(f"Erreur lors du traitement de la ru00e9union {meeting.get('id', 'unknown')}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info("Du00e9marrage de la mise u00e0 jour des statuts de transcription")
    update_transcription_status()
    logger.info("Mise u00e0 jour terminu00e9e")
