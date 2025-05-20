import requests
import logging
import json
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("transcription-updater")

# Paramu00e8tres
API_URL = "http://localhost:8001"
USERNAME = "test@example.com"
PASSWORD = "password123"
ASSEMBLYAI_API_KEY = "3419005ee6924e08a14235043cabcd4e"

def get_auth_token():
    """Obtenir un token d'authentification"""
    login_data = {
        'username': USERNAME,
        'password': PASSWORD
    }
    login_response = requests.post(f"{API_URL}/auth/login", data=login_data)
    
    if login_response.status_code != 200:
        logger.error(f"Erreur de connexion: {login_response.status_code} - {login_response.text}")
        return None
    
    token = login_response.json()['access_token']
    logger.info("Connectu00e9 avec succu00e8s")
    return token

def get_all_meetings(token):
    """Ru00e9cupu00e9rer toutes les ru00e9unions"""
    headers = {
        'Authorization': f'Bearer {token}'
    }
    meetings_response = requests.get(f"{API_URL}/simple/meetings/", headers=headers)
    
    if meetings_response.status_code != 200:
        logger.error(f"Erreur lors de la ru00e9cupu00e9ration des ru00e9unions: {meetings_response.status_code} - {meetings_response.text}")
        return []
    
    return meetings_response.json()

def get_assemblyai_transcriptions():
    """Ru00e9cupu00e9rer toutes les transcriptions ru00e9centes d'AssemblyAI"""
    headers = {
        "authorization": ASSEMBLYAI_API_KEY
    }
    
    try:
        url = "https://api.assemblyai.com/v2/transcript"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            transcripts = response.json().get('transcripts', [])
            logger.info(f"Ru00e9cupu00e9ration de {len(transcripts)} transcriptions ru00e9centes d'AssemblyAI")
            return transcripts
        else:
            logger.error(f"Erreur lors de la ru00e9cupu00e9ration des transcriptions: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        logger.error(f"Erreur lors de la ru00e9cupu00e9ration des transcriptions ru00e9centes: {str(e)}")
        return []

def get_assemblyai_transcript_details(transcript_id):
    """Ru00e9cupu00e9rer les du00e9tails d'une transcription AssemblyAI"""
    headers = {
        "authorization": ASSEMBLYAI_API_KEY
    }
    
    try:
        url = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Erreur lors de la ru00e9cupu00e9ration des du00e9tails de la transcription: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Erreur lors de la ru00e9cupu00e9ration des du00e9tails de la transcription: {str(e)}")
        return None

def update_meeting_status(token, meeting_id, user_id, update_data):
    """Mettre u00e0 jour le statut d'une ru00e9union"""
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    update_url = f"{API_URL}/simple/meetings/{meeting_id}"
    response = requests.put(update_url, headers=headers, json=update_data)
    
    if response.status_code == 200:
        logger.info(f"Ru00e9union {meeting_id} mise u00e0 jour avec succu00e8s")
        return True
    else:
        logger.error(f"Erreur lors de la mise u00e0 jour de la ru00e9union {meeting_id}: {response.status_code} - {response.text}")
        return False

def format_transcript_text(transcript_data):
    """Formater le texte de la transcription avec les locuteurs"""
    text = transcript_data.get('text', '')
    utterances = transcript_data.get('utterances', [])
    
    if not utterances:
        return text
    
    formatted_text = []
    for utterance in utterances:
        speaker = utterance.get('speaker', 'Unknown')
        utterance_text = utterance.get('text', '')
        formatted_text.append(f"Speaker {speaker}: {utterance_text}")
    
    return "\n".join(formatted_text)

def force_update_transcriptions():
    """Forcer la mise u00e0 jour des transcriptions en cours"""
    # Connexion u00e0 l'API
    token = get_auth_token()
    if not token:
        return
    
    # Ru00e9cupu00e9rer toutes les ru00e9unions
    meetings = get_all_meetings(token)
    logger.info(f"Ru00e9cupu00e9ration de {len(meetings)} ru00e9unions")
    
    # Ru00e9cupu00e9rer toutes les transcriptions ru00e9centes d'AssemblyAI
    assemblyai_transcripts = get_assemblyai_transcriptions()
    
    # Filtrer les ru00e9unions en cours de traitement
    processing_meetings = [m for m in meetings if m.get('transcript_status') == 'processing']
    logger.info(f"Ru00e9unions en cours de traitement: {len(processing_meetings)}")
    
    # Pour chaque ru00e9union en cours de traitement
    for meeting in processing_meetings:
        meeting_id = meeting.get('id')
        user_id = meeting.get('user_id')
        transcript_id = meeting.get('transcript_id')
        title = meeting.get('title', '')
        
        logger.info(f"Vu00e9rification de la ru00e9union {meeting_id} - {title}")
        
        # Si nous avons un ID de transcription, vu00e9rifier directement
        if transcript_id:
            logger.info(f"Vu00e9rification de la transcription {transcript_id}")
            transcript_data = get_assemblyai_transcript_details(transcript_id)
            
            if transcript_data:
                status = transcript_data.get('status')
                logger.info(f"Statut de la transcription {transcript_id}: {status}")
                
                if status == 'completed':
                    # Pru00e9parer les donnu00e9es de mise u00e0 jour
                    transcript_text = format_transcript_text(transcript_data)
                    audio_duration = transcript_data.get('audio_duration', 0)
                    
                    # Calculer le nombre de locuteurs
                    speakers_set = set()
                    for utterance in transcript_data.get('utterances', []):
                        speakers_set.add(utterance.get('speaker', 'Unknown'))
                    
                    speakers_count = len(speakers_set) if speakers_set else 1
                    
                    update_data = {
                        "transcript_text": transcript_text,
                        "transcript_status": "completed",
                        "duration_seconds": int(audio_duration) if audio_duration else 0,
                        "speakers_count": speakers_count
                    }
                    
                    # Mettre u00e0 jour la ru00e9union
                    update_meeting_status(token, meeting_id, user_id, update_data)
                elif status == 'error':
                    error_message = transcript_data.get('error', 'Unknown error')
                    update_data = {
                        "transcript_status": "error",
                        "transcript_text": f"Erreur lors de la transcription: {error_message}"
                    }
                    update_meeting_status(token, meeting_id, user_id, update_data)
        
        # Si nous n'avons pas d'ID ou si la vu00e9rification directe a u00e9chouu00e9, essayer de trouver par correspondance
        else:
            logger.info(f"Recherche de transcription pour la ru00e9union {meeting_id} - {title}")
            
            # Parcourir les transcriptions ru00e9centes d'AssemblyAI
            for transcript in assemblyai_transcripts:
                if transcript.get('status') == 'completed':
                    # Ru00e9cupu00e9rer les du00e9tails complets
                    transcript_id = transcript.get('id')
                    transcript_data = get_assemblyai_transcript_details(transcript_id)
                    
                    if not transcript_data:
                        continue
                    
                    # Vu00e9rifier si le nom du fichier correspond
                    audio_url = transcript_data.get('audio_url', '')
                    audio_filename = audio_url.split('/')[-1] if audio_url else ''
                    
                    if title in audio_filename or audio_filename in title:
                        logger.info(f"Correspondance trouvu00e9e pour {title}: {transcript_id}")
                        
                        # Pru00e9parer les donnu00e9es de mise u00e0 jour
                        transcript_text = format_transcript_text(transcript_data)
                        audio_duration = transcript_data.get('audio_duration', 0)
                        
                        # Calculer le nombre de locuteurs
                        speakers_set = set()
                        for utterance in transcript_data.get('utterances', []):
                            speakers_set.add(utterance.get('speaker', 'Unknown'))
                        
                        speakers_count = len(speakers_set) if speakers_set else 1
                        
                        update_data = {
                            "transcript_id": transcript_id,
                            "transcript_text": transcript_text,
                            "transcript_status": "completed",
                            "duration_seconds": int(audio_duration) if audio_duration else 0,
                            "speakers_count": speakers_count
                        }
                        
                        # Mettre u00e0 jour la ru00e9union
                        update_meeting_status(token, meeting_id, user_id, update_data)
                        break

if __name__ == "__main__":
    logger.info("Du00e9marrage de la mise u00e0 jour forcu00e9e des transcriptions")
    force_update_transcriptions()
    logger.info("Mise u00e0 jour terminu00e9e")
