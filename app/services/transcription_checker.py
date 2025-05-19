import requests
import logging
from typing import Dict, Any, Optional

# Configuration du logging
logger = logging.getLogger("transcription-checker")

# Clé API AssemblyAI
ASSEMBLYAI_API_KEY = "3419005ee6924e08a14235043cabcd4e"

def check_and_update_transcription(meeting: Dict[str, Any]) -> Dict[str, Any]:
    """
    Vérifie le statut d'une transcription auprès d'AssemblyAI et met à jour les données de la réunion si nécessaire.
    
    Args:
        meeting: Dictionnaire contenant les données de la réunion
        
    Returns:
        Dictionnaire mis à jour avec le statut actuel de la transcription
    """
    # Si la réunion n'est pas en cours de traitement, pas besoin de vérifier
    if meeting.get('transcript_status') != 'processing':
        return meeting
    
    # Si nous n'avons pas d'ID de transcription, impossible de vérifier
    transcript_id = meeting.get('transcript_id')
    if not transcript_id:
        return meeting
    
    logger.info(f"Vérification de la transcription {transcript_id} pour la réunion {meeting.get('id')}")
    
    # Vérifier le statut auprès d'AssemblyAI
    transcript_data = get_assemblyai_transcript_details(transcript_id)
    if not transcript_data:
        return meeting
    
    status = transcript_data.get('status')
    logger.info(f"Statut de la transcription {transcript_id}: {status}")
    
    # Si la transcription est terminée, mettre à jour les données de la réunion
    if status == 'completed':
        logger.info(f"Transcription {transcript_id} terminée, mise à jour des données de la réunion")
        
        # Extraire le texte de la transcription
        transcript_text = transcript_data.get('text', '')
        
        # Formater avec les locuteurs si disponibles
        if 'utterances' in transcript_data and transcript_data['utterances']:
            try:
                transcript_text = format_transcript_text(transcript_data)
                
                # Calculer le nombre de locuteurs
                speakers_set = set()
                for utterance in transcript_data.get('utterances', []):
                    speakers_set.add(utterance.get('speaker', 'Unknown'))
                
                speakers_count = len(speakers_set) if speakers_set else 1
            except Exception as e:
                logger.error(f"Erreur lors du formatage du texte: {str(e)}")
                speakers_count = 1
        else:
            speakers_count = 1
        
        # Mettre à jour les données de la réunion
        meeting['transcript_status'] = 'completed'
        meeting['transcript_text'] = transcript_text
        meeting['duration_seconds'] = int(transcript_data.get('audio_duration', 0))
        meeting['speakers_count'] = speakers_count
        
        # Mettre à jour la base de données
        from ..db.queries import update_meeting
        update_meeting(meeting['id'], meeting['user_id'], {
            "transcript_status": "completed",
            "transcript_text": transcript_text,
            "duration_seconds": int(transcript_data.get('audio_duration', 0)),
            "speakers_count": speakers_count
        })
    
    # Si la transcription est en erreur, mettre à jour le statut
    elif status == 'error':
        logger.error(f"Erreur de transcription pour {transcript_id}: {transcript_data.get('error')}")
        
        error_message = transcript_data.get('error', 'Unknown error')
        meeting['transcript_status'] = 'error'
        meeting['transcript_text'] = f"Erreur lors de la transcription: {error_message}"
        
        # Mettre à jour la base de données
        from ..db.queries import update_meeting
        update_meeting(meeting['id'], meeting['user_id'], {
            "transcript_status": "error",
            "transcript_text": f"Erreur lors de la transcription: {error_message}"
        })
    
    return meeting

def get_assemblyai_transcript_details(transcript_id: str) -> Optional[Dict[str, Any]]:
    """Récupérer les détails d'une transcription AssemblyAI"""
    headers = {
        "authorization": ASSEMBLYAI_API_KEY
    }
    
    try:
        url = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Erreur lors de la récupération des détails de la transcription: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des détails de la transcription: {str(e)}")
        return None

def format_transcript_text(transcript_data: Dict[str, Any]) -> str:
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
