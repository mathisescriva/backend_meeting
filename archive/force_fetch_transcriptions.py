import os
import requests
import logging
import json
import re
import time
from dotenv import load_dotenv
from app.db.queries import get_meetings_by_user, update_meeting, get_meeting, get_meetings_by_status

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('force-fetch')

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

def get_all_transcripts():
    """Récupère toutes les transcriptions disponibles depuis AssemblyAI"""
    all_transcripts = []
    page = 0
    page_size = 100
    
    while True:
        url = f"https://api.assemblyai.com/v2/transcript?page={page}&page_size={page_size}"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            transcripts = data.get('transcripts', [])
            
            if not transcripts:
                break
                
            all_transcripts.extend(transcripts)
            logger.info(f"Récupération de {len(transcripts)} transcriptions (page {page+1})")
            
            # Si nous avons moins de transcriptions que la taille de page, c'est la dernière page
            if len(transcripts) < page_size:
                break
                
            page += 1
            # Petite pause pour éviter de surcharger l'API
            time.sleep(0.5)
        else:
            logger.error(f"Erreur lors de la récupération des transcriptions: {response.status_code} - {response.text}")
            break
    
    logger.info(f"Total des transcriptions récupérées: {len(all_transcripts)}")
    return all_transcripts

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

def find_matching_transcript(meeting, all_transcripts):
    """Trouve la transcription correspondante pour une réunion"""
    try:
        meeting_title = meeting.get('title', '').lower()
        file_url = meeting.get('file_url', '')
        file_name = os.path.basename(file_url) if file_url else ''
        
        # Extraire les mots-clés du titre pour la recherche
        keywords = re.findall(r'\w+', meeting_title)
        keywords = [k for k in keywords if len(k) > 3]  # Ignorer les mots trop courts
        
        best_match = None
        best_match_score = 0
        
        for transcript in all_transcripts:
            if transcript.get('status') != 'completed':
                continue
                
            # Récupérer les détails complets de la transcription
            transcript_id = transcript.get('id')
            details = get_transcript_details(transcript_id)
            
            if not details or details.get('status') != 'completed':
                continue
                
            # Extraire le texte et l'URL audio
            text = details.get('text', '').lower()
            audio_url = details.get('audio_url', '').lower()
            audio_filename = os.path.basename(audio_url) if audio_url else ''
            
            # Calculer un score de correspondance
            score = 0
            
            # 1. Correspondance directe du nom de fichier
            if file_name and audio_filename and (file_name in audio_filename or audio_filename in file_name):
                score += 10
            
            # 2. Correspondance des mots-clés dans le texte
            for keyword in keywords:
                if keyword in text:
                    score += 1
            
            # Normaliser le score par rapport au nombre de mots-clés
            if keywords:
                keyword_score = score / len(keywords)
            else:
                keyword_score = 0
            
            # Enregistrer le meilleur match
            if score > best_match_score:
                best_match_score = score
                best_match = details
                logger.info(f"Nouveau meilleur match pour {meeting.get('id')}: {transcript_id} (score: {score})")
        
        return best_match
    except Exception as e:
        logger.error(f"Erreur lors de la recherche de transcription pour {meeting.get('id')}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def update_meeting_with_transcript(meeting_id, user_id, transcript_data):
    """Met à jour une réunion avec les données de transcription"""
    try:
        # Extraire les données importantes
        status = transcript_data.get('status')
        audio_duration = transcript_data.get('audio_duration', 0)
        
        if status != 'completed':
            logger.warning(f"La transcription {transcript_data.get('id')} n'est pas complétée (statut: {status})")
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
        logger.info(f"Mise à jour de la réunion {meeting_id} avec la transcription {transcript_data.get('id')}")
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

def force_fetch_all_transcriptions():
    """Force la récupération de toutes les transcriptions pour toutes les réunions"""
    try:
        # Récupérer les réunions avec différents statuts
        completed_meetings = get_meetings_by_status('completed')
        processing_meetings = get_meetings_by_status('processing')
        pending_meetings = get_meetings_by_status('pending')
        error_meetings = get_meetings_by_status('error')
        
        # Combiner toutes les réunions
        all_meetings = completed_meetings + processing_meetings + pending_meetings + error_meetings
        logger.info(f"Récupération de {len(all_meetings)} réunions (complétées: {len(completed_meetings)}, en cours: {len(processing_meetings)}, en attente: {len(pending_meetings)}, en erreur: {len(error_meetings)})")
        
        # Déduplication des réunions (au cas où certaines apparaissent dans plusieurs listes)
        unique_meetings = {}
        for meeting in all_meetings:
            meeting_id = meeting.get('id')
            if meeting_id not in unique_meetings:
                unique_meetings[meeting_id] = meeting
        
        all_meetings = list(unique_meetings.values())
        logger.info(f"Après déduplication: {len(all_meetings)} réunions uniques")
        
        # Récupérer toutes les transcriptions d'AssemblyAI
        all_transcripts = get_all_transcripts()
        
        # Pour chaque réunion, trouver la transcription correspondante et mettre à jour
        updated_count = 0
        for meeting in all_meetings:
            meeting_id = meeting.get('id')
            user_id = meeting.get('user_id')
            title = meeting.get('title')
            status = meeting.get('transcript_status')
            
            logger.info(f"Traitement de la réunion {meeting_id} ({title}) - Statut actuel: {status}")
            
            # Trouver la transcription correspondante
            matching_transcript = find_matching_transcript(meeting, all_transcripts)
            
            if matching_transcript:
                # Mettre à jour la réunion avec la transcription
                if update_meeting_with_transcript(meeting_id, user_id, matching_transcript):
                    updated_count += 1
            else:
                logger.warning(f"Aucune transcription correspondante trouvée pour la réunion {meeting_id} ({title})")
        
        logger.info(f"Mise à jour terminée. {updated_count}/{len(all_meetings)} réunions mises à jour.")
    except Exception as e:
        logger.error(f"Erreur lors de la récupération forcée des transcriptions: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

def force_fetch_single_meeting(meeting_id, user_id):
    """Force la récupération de la transcription pour une réunion spécifique"""
    try:
        # Récupérer les informations de la réunion
        meeting = get_meeting(meeting_id, user_id)
        if not meeting:
            logger.error(f"Réunion {meeting_id} non trouvée")
            return False
        
        logger.info(f"Récupération forcée pour la réunion {meeting_id} ({meeting.get('title')})")
        
        # Récupérer toutes les transcriptions d'AssemblyAI
        all_transcripts = get_all_transcripts()
        
        # Trouver la transcription correspondante
        matching_transcript = find_matching_transcript(meeting, all_transcripts)
        
        if matching_transcript:
            # Mettre à jour la réunion avec la transcription
            return update_meeting_with_transcript(meeting_id, user_id, matching_transcript)
        else:
            logger.warning(f"Aucune transcription correspondante trouvée pour la réunion {meeting_id}")
            return False
    except Exception as e:
        logger.error(f"Erreur lors de la récupération forcée de la transcription: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) == 1:
        # Forcer la récupération de toutes les transcriptions
        logger.info("Récupération forcée de toutes les transcriptions")
        force_fetch_all_transcriptions()
    elif len(sys.argv) == 3:
        # Forcer la récupération d'une transcription spécifique
        meeting_id = sys.argv[1]
        user_id = sys.argv[2]
        logger.info(f"Récupération forcée de la transcription pour la réunion {meeting_id}")
        if force_fetch_single_meeting(meeting_id, user_id):
            logger.info("Récupération forcée réussie")
        else:
            logger.error("Récupération forcée échouée")
    else:
        print("Usage:")
        print("  python force_fetch_transcriptions.py                  # Force la récupération de toutes les transcriptions")
        print("  python force_fetch_transcriptions.py <meeting_id> <user_id>  # Force la récupération d'une transcription spécifique")
