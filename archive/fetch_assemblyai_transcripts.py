import os
import requests
import logging
import json
from dotenv import load_dotenv
from app.db.queries import get_meetings_by_status, update_meeting, get_meeting
from app.services.assemblyai import process_completed_transcript
import assemblyai as aai

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('transcript-fetcher')

# Charger les variables d'environnement
load_dotenv()

# Récupérer la clé API AssemblyAI
ASSEMBLYAI_API_KEY = os.getenv('ASSEMBLYAI_API_KEY')
if not ASSEMBLYAI_API_KEY:
    raise ValueError("La clé API AssemblyAI n'est pas définie dans les variables d'environnement")

# Configuration de l'API AssemblyAI
headers = {
    "authorization": ASSEMBLYAI_API_KEY,
    "content-type": "application/json"
}

def get_recent_transcripts():
    """Récupère les transcriptions récentes depuis AssemblyAI"""
    url = "https://api.assemblyai.com/v2/transcript"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        transcripts = response.json().get('transcripts', [])
        logger.info(f"Récupération de {len(transcripts)} transcriptions récentes d'AssemblyAI")
        return transcripts
    else:
        logger.error(f"Erreur lors de la récupération des transcriptions: {response.status_code} - {response.text}")
        return []

def get_transcript_details(transcript_id):
    """Récupère les détails d'une transcription spécifique depuis AssemblyAI"""
    url = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Erreur lors de la récupération des détails de la transcription {transcript_id}: {response.status_code} - {response.text}")
        return None

def extract_filename_from_url(url):
    """Extrait le nom de fichier d'une URL"""
    if not url:
        return None
    
    # Supprimer les paramètres d'URL s'il y en a
    url = url.split('?')[0]
    
    # Récupérer le dernier segment de l'URL
    filename = url.split('/')[-1]
    
    return filename

def find_matching_meeting_by_filename(filename, meetings):
    """Trouve une réunion correspondant au nom de fichier"""
    if not filename:
        return None
    
    for meeting in meetings:
        meeting_filename = extract_filename_from_url(meeting.get('file_url'))
        if meeting_filename and filename in meeting_filename:
            return meeting
    
    return None

def update_meeting_with_transcript(meeting_id, user_id, transcript_data):
    """Met à jour une réunion avec les données de transcription"""
    try:
        # Créer un objet Transcript compatible avec process_completed_transcript
        class TranscriptObject:
            def __init__(self, data):
                self.id = data.get('id')
                self.status = data.get('status')
                self.text = data.get('text')
                self.audio_duration = data.get('audio_duration')
                self.utterances = []
                
                # Traiter les utterances si disponibles
                utterances_data = data.get('utterances', [])
                for utterance in utterances_data:
                    self.utterances.append(UtteranceObject(utterance))
        
        class UtteranceObject:
            def __init__(self, data):
                self.speaker = data.get('speaker')
                self.text = data.get('text')
        
        # Créer l'objet transcript
        transcript = TranscriptObject(transcript_data)
        
        # Traiter la transcription terminée
        process_completed_transcript(meeting_id, user_id, transcript)
        
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour de la réunion {meeting_id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def fetch_and_update_transcripts():
    """Récupère les transcriptions récentes et met à jour les réunions correspondantes"""
    try:
        # Récupérer toutes les réunions avec statut 'completed' ou 'processing'
        completed_meetings = get_meetings_by_status('completed')
        processing_meetings = get_meetings_by_status('processing')
        all_meetings = completed_meetings + processing_meetings
        
        logger.info(f"Réunions complétées: {len(completed_meetings)}")
        logger.info(f"Réunions en cours: {len(processing_meetings)}")
        
        # Récupérer les transcriptions récentes d'AssemblyAI
        recent_transcripts = get_recent_transcripts()
        
        # Pour chaque transcription récente
        for transcript in recent_transcripts:
            transcript_id = transcript.get('id')
            status = transcript.get('status')
            audio_url = transcript.get('audio_url')
            
            logger.info(f"Transcription {transcript_id} - Statut: {status} - URL: {audio_url}")
            
            # Si la transcription est complétée
            if status == 'completed':
                # Extraire le nom de fichier de l'URL audio
                filename = extract_filename_from_url(audio_url)
                logger.info(f"Nom de fichier extrait: {filename}")
                
                # Trouver la réunion correspondante
                matching_meeting = find_matching_meeting_by_filename(filename, all_meetings)
                
                if matching_meeting:
                    meeting_id = matching_meeting.get('id')
                    user_id = matching_meeting.get('user_id')
                    current_status = matching_meeting.get('transcript_status')
                    
                    logger.info(f"Réunion correspondante trouvée: {meeting_id} - Statut actuel: {current_status}")
                    
                    # Si la réunion est en cours de traitement ou si le texte est vide
                    if current_status == 'processing' or not matching_meeting.get('transcript_text') or matching_meeting.get('transcript_text') == 'Cette transcription a été marquée comme complétée manuellement.':
                        # Récupérer les détails complets de la transcription
                        transcript_details = get_transcript_details(transcript_id)
                        
                        if transcript_details and transcript_details.get('status') == 'completed':
                            logger.info(f"Mise à jour de la réunion {meeting_id} avec la transcription {transcript_id}")
                            if update_meeting_with_transcript(meeting_id, user_id, transcript_details):
                                logger.info(f"Réunion {meeting_id} mise à jour avec succès")
                            else:
                                logger.error(f"Échec de la mise à jour de la réunion {meeting_id}")
                else:
                    logger.warning(f"Aucune réunion correspondante trouvée pour le fichier {filename}")
        
        logger.info("Traitement terminé")
    except Exception as e:
        logger.error(f"Erreur lors du traitement des transcriptions: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info("Démarrage de la récupération des transcriptions AssemblyAI")
    fetch_and_update_transcripts()
    logger.info("Récupération terminée")
