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
logger = logging.getLogger('transcription-updater')

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

def update_meeting_with_transcript_id(meeting_id, user_id, transcript_id):
    """Met à jour une réunion avec l'ID de transcription spécifié"""
    try:
        # Récupérer les détails de la transcription
        transcript_data = get_transcript_details(transcript_id)
        
        if not transcript_data:
            logger.error(f"Impossible de récupérer les détails de la transcription {transcript_id}")
            return False
        
        # Extraire les données importantes
        status = transcript_data.get('status')
        audio_duration = transcript_data.get('audio_duration', 0)
        
        if status != 'completed':
            logger.warning(f"La transcription {transcript_id} n'est pas complétée (statut: {status})")
            return False
        
        # Formater le texte avec les locuteurs
        formatted_text = format_transcript_text(transcript_data)
        
        # Compter les locuteurs uniques
        utterances = transcript_data.get('utterances', [])
        unique_speakers = set(u.get('speaker') for u in utterances if u.get('speaker'))
        speaker_count = len(unique_speakers) if unique_speakers else 1
        
        # Préparer les données de mise à jour
        update_data = {
            "transcript_text": formatted_text,
            "transcript_status": "completed",
            "duration_seconds": int(audio_duration),
            "speakers_count": speaker_count
        }
        
        # Mettre à jour la base de données
        logger.info(f"Mise à jour de la réunion {meeting_id} avec la transcription {transcript_id}")
        update_meeting(meeting_id, user_id, update_data)
        
        # Vérifier que la mise à jour a fonctionné
        updated_meeting = get_meeting(meeting_id, user_id)
        success = updated_meeting.get('transcript_status') == 'completed' and len(updated_meeting.get('transcript_text', '')) > 50
        
        if success:
            logger.info(f"Réunion {meeting_id} mise à jour avec succès")
        else:
            logger.error(f"Échec de la mise à jour de la réunion {meeting_id}")
        
        return success
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour de la réunion {meeting_id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def list_available_transcripts():
    """Liste toutes les transcriptions disponibles dans AssemblyAI"""
    try:
        # Récupérer les transcriptions récentes
        recent_transcripts = get_recent_transcripts()
        
        logger.info(f"Transcriptions disponibles: {len(recent_transcripts)}")
        
        # Afficher les informations de chaque transcription
        for i, transcript in enumerate(recent_transcripts, 1):
            transcript_id = transcript.get('id')
            status = transcript.get('status')
            created_at = transcript.get('created_at')
            
            logger.info(f"Transcription {i}:")
            logger.info(f"  ID: {transcript_id}")
            logger.info(f"  Statut: {status}")
            logger.info(f"  Créée le: {created_at}")
            
            # Si la transcription est complétée, récupérer plus de détails
            if status == 'completed':
                details = get_transcript_details(transcript_id)
                if details:
                    audio_url = details.get('audio_url', '')
                    text_preview = details.get('text', '')[:100] + '...' if details.get('text', '') else ''
                    
                    logger.info(f"  URL audio: {audio_url}")
                    logger.info(f"  Texte (aperçu): {text_preview}")
            
            logger.info("---")
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des transcriptions: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

def list_meetings_to_update():
    """Liste toutes les réunions qui pourraient nécessiter une mise à jour"""
    try:
        # Récupérer toutes les réunions avec statut 'completed'
        completed_meetings = get_meetings_by_status('completed')
        
        logger.info(f"Réunions complétées: {len(completed_meetings)}")
        
        # Afficher les informations de chaque réunion
        for i, meeting in enumerate(completed_meetings, 1):
            meeting_id = meeting.get('id')
            user_id = meeting.get('user_id')
            title = meeting.get('title')
            file_url = meeting.get('file_url')
            transcript_text = meeting.get('transcript_text', '')
            
            # Vérifier si le texte est celui d'une complétion forcée
            is_forced = transcript_text == "Cette transcription a été marquée comme complétée manuellement."
            
            logger.info(f"Réunion {i}:")
            logger.info(f"  ID: {meeting_id}")
            logger.info(f"  Utilisateur: {user_id}")
            logger.info(f"  Titre: {title}")
            logger.info(f"  Fichier: {file_url}")
            logger.info(f"  Complétion forcée: {'Oui' if is_forced else 'Non'}")
            
            if not is_forced:
                text_preview = transcript_text[:100] + '...' if len(transcript_text) > 100 else transcript_text
                logger.info(f"  Texte (aperçu): {text_preview}")
            
            logger.info("---")
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des réunions: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) == 1:
        # Afficher l'aide
        print("Usage:")
        print("  python update_transcription_content.py list_transcripts  # Liste toutes les transcriptions disponibles")
        print("  python update_transcription_content.py list_meetings    # Liste toutes les réunions à mettre à jour")
        print("  python update_transcription_content.py update <meeting_id> <user_id> <transcript_id>  # Met à jour une réunion avec une transcription spécifique")
    elif sys.argv[1] == "list_transcripts":
        # Lister toutes les transcriptions disponibles
        logger.info("Liste des transcriptions disponibles:")
        list_available_transcripts()
    elif sys.argv[1] == "list_meetings":
        # Lister toutes les réunions à mettre à jour
        logger.info("Liste des réunions à mettre à jour:")
        list_meetings_to_update()
    elif sys.argv[1] == "update" and len(sys.argv) == 5:
        # Mettre à jour une réunion avec une transcription spécifique
        meeting_id = sys.argv[2]
        user_id = sys.argv[3]
        transcript_id = sys.argv[4]
        
        logger.info(f"Mise à jour de la réunion {meeting_id} avec la transcription {transcript_id}")
        if update_meeting_with_transcript_id(meeting_id, user_id, transcript_id):
            logger.info("Mise à jour réussie")
        else:
            logger.error("Mise à jour échouée")
    else:
        logger.error("Arguments invalides")
