import assemblyai as aai
from app.db.queries import get_meetings_by_status, update_meeting
from app.services.assemblyai import process_completed_transcript
from dotenv import load_dotenv
import os
import logging
import re
from pathlib import Path

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

def update_all_processing_transcriptions():
    """Met à jour toutes les transcriptions en cours de traitement"""
    # Récupérer toutes les transcriptions en cours
    processing_meetings = get_meetings_by_status('processing')
    logger.info(f"Transcriptions en cours: {len(processing_meetings)}")
    
    if not processing_meetings:
        logger.info("Aucune transcription en cours trouvée")
        return
    
    # Créer un transcriber pour réutilisation
    transcriber = aai.Transcriber()
    
    # Récupérer toutes les transcriptions récentes d'AssemblyAI
    try:
        # Récupérer les 25 dernières transcriptions
        recent_transcripts = transcriber.list_transcripts(limit=25)
        logger.info(f"Récupération de {len(recent_transcripts)} transcriptions récentes d'AssemblyAI")
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des transcriptions récentes: {str(e)}")
        recent_transcripts = []
    
    # Traiter chaque transcription
    for meeting in processing_meetings:
        try:
            meeting_id = meeting['id']
            user_id = meeting['user_id']
            transcript_text = meeting.get('transcript_text', '')
            file_url = meeting.get('file_url', '')
            
            logger.info(f"Vérification de la réunion {meeting_id}")
            logger.info(f"Texte actuel: {transcript_text}")
            logger.info(f"Fichier: {file_url}")
            
            # Méthode 1: Essayer d'extraire l'ID de transcription AssemblyAI du texte
            transcript_id = None
            if transcript_text and 'ID:' in transcript_text:
                try:
                    # Extraire l'ID de transcription du texte
                    transcript_id = transcript_text.split('ID:')[-1].strip()
                    logger.info(f"ID de transcription AssemblyAI extrait: {transcript_id}")
                    
                    # Vérifier le statut de la transcription
                    transcript = transcriber.get_by_id(transcript_id)
                    logger.info(f"Statut de la transcription {transcript_id}: {transcript.status}")
                    
                    if transcript.status == aai.TranscriptStatus.completed:
                        # Traiter la transcription terminée
                        logger.info(f"Transcription {transcript_id} terminée, mise à jour de la base de données")
                        process_completed_transcript(meeting_id, user_id, transcript)
                        logger.info(f"Mise à jour réussie pour la réunion {meeting_id}")
                        continue  # Passer à la réunion suivante
                    elif transcript.status == aai.TranscriptStatus.error:
                        # Gérer l'erreur
                        error_message = getattr(transcript, 'error', 'Unknown error')
                        logger.error(f"Erreur de transcription pour {meeting_id}: {error_message}")
                        update_meeting(meeting_id, user_id, {
                            "transcript_status": "error",
                            "transcript_text": f"Erreur lors de la transcription: {error_message}"
                        })
                        continue  # Passer à la réunion suivante
                    else:
                        # Toujours en cours
                        logger.info(f"Transcription {transcript_id} toujours en cours ({transcript.status})")
                        continue  # Passer à la réunion suivante
                except Exception as e:
                    logger.error(f"Erreur lors de la vérification de la transcription par ID: {str(e)}")
                    # Continuer avec la méthode 2
            
            # Méthode 2: Essayer de trouver la transcription par le nom du fichier dans les transcriptions récentes
            if file_url and recent_transcripts:
                # Extraire le nom du fichier sans le chemin complet
                file_name = Path(file_url).name
                logger.info(f"Recherche de transcription pour le fichier: {file_name}")
                
                # Chercher dans les transcriptions récentes
                for recent_transcript in recent_transcripts:
                    # Vérifier si le nom du fichier est dans l'URL de la transcription
                    if hasattr(recent_transcript, 'audio_url') and file_name in recent_transcript.audio_url:
                        logger.info(f"Transcription trouvée pour {file_name}: {recent_transcript.id}")
                        
                        # Vérifier le statut
                        if recent_transcript.status == aai.TranscriptStatus.completed:
                            logger.info(f"Transcription {recent_transcript.id} terminée, mise à jour de la base de données")
                            process_completed_transcript(meeting_id, user_id, recent_transcript)
                            logger.info(f"Mise à jour réussie pour la réunion {meeting_id}")
                            break
                        elif recent_transcript.status == aai.TranscriptStatus.error:
                            error_message = getattr(recent_transcript, 'error', 'Unknown error')
                            logger.error(f"Erreur de transcription pour {meeting_id}: {error_message}")
                            update_meeting(meeting_id, user_id, {
                                "transcript_status": "error",
                                "transcript_text": f"Erreur lors de la transcription: {error_message}"
                            })
                            break
                        else:
                            logger.info(f"Transcription {recent_transcript.id} toujours en cours ({recent_transcript.status})")
                            # Mettre à jour l'ID de transcription dans la base de données pour les futures vérifications
                            update_meeting(meeting_id, user_id, {
                                "transcript_status": "processing",
                                "transcript_text": f"Transcription en cours de traitement. ID: {recent_transcript.id}"
                            })
                            break
                else:
                    logger.warning(f"Aucune transcription trouvée pour le fichier {file_name}")
            else:
                logger.warning(f"Impossible de trouver une transcription pour la réunion {meeting_id}")
        except Exception as e:
            logger.error(f"Erreur lors du traitement de la réunion {meeting.get('id', 'unknown')}: {str(e)}")
            logger.error(f"Détails: {e.__class__.__name__}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info("Du00e9marrage de la mise u00e0 jour des transcriptions en cours")
    update_all_processing_transcriptions()
    logger.info("Mise u00e0 jour terminu00e9e")
