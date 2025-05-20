import os
import requests
import logging
import json
import re
from dotenv import load_dotenv
from app.db.queries import get_meetings_by_status, update_meeting, get_meeting

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('transcript-retriever')

# Charger les variables d'environnement
load_dotenv()

# Ru00e9cupu00e9rer la clu00e9 API AssemblyAI
ASSEMBLYAI_API_KEY = os.getenv('ASSEMBLYAI_API_KEY')
if not ASSEMBLYAI_API_KEY:
    raise ValueError("La clu00e9 API AssemblyAI n'est pas du00e9finie dans les variables d'environnement")

# Configuration de l'API AssemblyAI
headers = {
    "authorization": ASSEMBLYAI_API_KEY,
    "content-type": "application/json"
}

def get_recent_transcripts():
    """Ru00e9cupu00e8re les transcriptions ru00e9centes depuis AssemblyAI"""
    url = "https://api.assemblyai.com/v2/transcript"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        transcripts = response.json().get('transcripts', [])
        logger.info(f"Ru00e9cupu00e9ration de {len(transcripts)} transcriptions ru00e9centes d'AssemblyAI")
        return transcripts
    else:
        logger.error(f"Erreur lors de la ru00e9cupu00e9ration des transcriptions: {response.status_code} - {response.text}")
        return []

def get_transcript_details(transcript_id):
    """Ru00e9cupu00e8re les du00e9tails d'une transcription spu00e9cifique depuis AssemblyAI"""
    url = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Erreur lors de la ru00e9cupu00e9ration des du00e9tails de la transcription {transcript_id}: {response.status_code} - {response.text}")
        return None

def get_transcript_by_name(meeting_title):
    """Recherche une transcription par son nom dans les transcriptions ru00e9centes"""
    try:
        # Ru00e9cupu00e9rer les transcriptions ru00e9centes
        recent_transcripts = get_recent_transcripts()
        
        # Normaliser le titre de la ru00e9union pour la recherche
        normalized_title = meeting_title.lower()
        
        # Ru00e9cupu00e9rer les du00e9tails de chaque transcription pour voir s'il y a une correspondance
        for transcript in recent_transcripts:
            transcript_id = transcript.get('id')
            status = transcript.get('status')
            
            # Si la transcription est complu00e9tu00e9e, ru00e9cupu00e9rer ses du00e9tails
            if status == 'completed':
                details = get_transcript_details(transcript_id)
                
                if details:
                    # Ru00e9cupu00e9rer le nom du fichier audio
                    audio_url = details.get('audio_url', '')
                    file_name = os.path.basename(audio_url) if audio_url else ''
                    
                    # Ru00e9cupu00e9rer le texte de la transcription
                    text = details.get('text', '')
                    
                    # Afficher les informations pour du00e9bogage
                    logger.info(f"Transcription {transcript_id} - Fichier: {file_name}")
                    logger.info(f"Texte (premiers 100 caractu00e8res): {text[:100]}...")
                    
                    # Vu00e9rifier si le titre de la ru00e9union est contenu dans le nom du fichier
                    # ou si des mots-clu00e9s du titre sont pru00e9sents dans le texte
                    keywords = re.findall(r'\w+', normalized_title)
                    keywords = [k for k in keywords if len(k) > 3]  # Ignorer les mots trop courts
                    
                    text_matches = sum(1 for k in keywords if k.lower() in text.lower())
                    keyword_match_ratio = text_matches / len(keywords) if keywords else 0
                    
                    logger.info(f"Correspondance des mots-clu00e9s: {keyword_match_ratio:.2f} ({text_matches}/{len(keywords)})")
                    
                    # Si le titre est contenu dans le nom du fichier ou si au moins 30% des mots-clu00e9s sont pru00e9sents
                    if (normalized_title in file_name.lower() or 
                        any(k.lower() in file_name.lower() for k in keywords if len(k) > 3) or 
                        keyword_match_ratio >= 0.3):
                        logger.info(f"Correspondance trouvu00e9e pour {meeting_title}: {transcript_id}")
                        return details
        
        logger.warning(f"Aucune correspondance trouvu00e9e pour {meeting_title}")
        return None
    except Exception as e:
        logger.error(f"Erreur lors de la recherche de transcription pour {meeting_title}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def format_transcript_text(transcript_data):
    """Formate le texte de la transcription avec les locuteurs"""
    try:
        text = transcript_data.get('text', '')
        utterances = transcript_data.get('utterances', [])
        
        if not utterances:
            return text
        
        formatted_text = []
        for utterance in utterances:
            speaker = utterance.get('speaker', 'Unknown')
            utterance_text = utterance.get('text', '').strip()
            if speaker and utterance_text:
                formatted_text.append(f"Speaker {speaker}: {utterance_text}")
        
        return "\n".join(formatted_text) if formatted_text else text
    except Exception as e:
        logger.error(f"Erreur lors du formatage du texte: {str(e)}")
        return transcript_data.get('text', '')

def update_meeting_with_transcript(meeting_id, user_id, transcript_data):
    """Met u00e0 jour une ru00e9union avec les donnu00e9es de transcription"""
    try:
        # Extraire les donnu00e9es importantes
        status = transcript_data.get('status')
        audio_duration = transcript_data.get('audio_duration', 0)
        
        if status != 'completed':
            logger.warning(f"La transcription {transcript_data.get('id')} n'est pas complu00e9tu00e9e (statut: {status})")
            return False
        
        # Formater le texte avec les locuteurs
        formatted_text = format_transcript_text(transcript_data)
        
        # Compter les locuteurs uniques
        utterances = transcript_data.get('utterances', [])
        unique_speakers = set(u.get('speaker') for u in utterances if u.get('speaker'))
        speaker_count = len(unique_speakers) if unique_speakers else 1
        
        # Pru00e9parer les donnu00e9es de mise u00e0 jour
        update_data = {
            "transcript_text": formatted_text,
            "transcript_status": "completed",
            "duration_seconds": int(audio_duration),
            "speakers_count": speaker_count
        }
        
        # Mettre u00e0 jour la base de donnu00e9es
        logger.info(f"Mise u00e0 jour de la ru00e9union {meeting_id} avec la transcription {transcript_data.get('id')}")
        update_meeting(meeting_id, user_id, update_data)
        
        # Vu00e9rifier que la mise u00e0 jour a fonctionnu00e9
        updated_meeting = get_meeting(meeting_id, user_id)
        success = updated_meeting.get('transcript_status') == 'completed' and len(updated_meeting.get('transcript_text', '')) > 50
        
        if success:
            logger.info(f"Ru00e9union {meeting_id} mise u00e0 jour avec succu00e8s")
        else:
            logger.error(f"u00c9chec de la mise u00e0 jour de la ru00e9union {meeting_id}")
        
        return success
    except Exception as e:
        logger.error(f"Erreur lors de la mise u00e0 jour de la ru00e9union {meeting_id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def retrieve_and_update_meeting(meeting_id, user_id):
    """Ru00e9cupu00e8re et met u00e0 jour une ru00e9union spu00e9cifique"""
    try:
        # Ru00e9cupu00e9rer les informations de la ru00e9union
        meeting = get_meeting(meeting_id, user_id)
        if not meeting:
            logger.error(f"Ru00e9union {meeting_id} non trouvu00e9e")
            return False
        
        meeting_title = meeting.get('title', '')
        current_status = meeting.get('transcript_status')
        current_text = meeting.get('transcript_text', '')
        
        logger.info(f"Ru00e9union {meeting_id} - Titre: {meeting_title} - Statut: {current_status}")
        
        # Si la ru00e9union a du00e9ju00e0 une transcription complu00e8te, vu00e9rifier si elle doit u00eatre mise u00e0 jour
        if current_status == 'completed' and current_text and current_text != "Cette transcription a u00e9tu00e9 marquu00e9e comme complu00e9tu00e9e manuellement.":
            logger.info(f"La ru00e9union {meeting_id} a du00e9ju00e0 une transcription complu00e8te")
            return True
        
        # Rechercher la transcription par son nom
        transcript_data = get_transcript_by_name(meeting_title)
        
        if transcript_data:
            # Mettre u00e0 jour la ru00e9union avec la transcription
            return update_meeting_with_transcript(meeting_id, user_id, transcript_data)
        else:
            logger.warning(f"Aucune transcription trouvu00e9e pour la ru00e9union {meeting_id} ({meeting_title})")
            return False
    except Exception as e:
        logger.error(f"Erreur lors de la ru00e9cupu00e9ration et mise u00e0 jour de la ru00e9union {meeting_id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) == 3:
        meeting_id = sys.argv[1]
        user_id = sys.argv[2]
        logger.info(f"Ru00e9cupu00e9ration et mise u00e0 jour de la ru00e9union {meeting_id} pour l'utilisateur {user_id}")
        if retrieve_and_update_meeting(meeting_id, user_id):
            logger.info("Ru00e9cupu00e9ration et mise u00e0 jour ru00e9ussies")
        else:
            logger.error("Ru00e9cupu00e9ration et mise u00e0 jour u00e9chouu00e9es")
    else:
        logger.error("Usage: python retrieve_transcription_by_name.py <meeting_id> <user_id>")
