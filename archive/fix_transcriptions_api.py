import requests
import json
import time
import os
import logging
from dotenv import load_dotenv
from app.db.queries import get_meetings_by_status, update_meeting, get_meeting
from app.services.assemblyai import process_completed_transcript

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
ASSEMBLY_AI_BASE_URL = "https://api.assemblyai.com/v2"

# Headers pour les requu00eates API
headers = {
    "Authorization": f"Bearer {ASSEMBLY_AI_API_KEY}",
    "Content-Type": "application/json"
}

def get_transcript_status(transcript_id):
    """Obtient le statut d'une transcription via l'API REST"""
    url = f"{ASSEMBLY_AI_BASE_URL}/transcript/{transcript_id}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Erreur lors de la ru00e9cupu00e9ration du statut: {response.status_code}")
        logger.error(response.text)
        return None

def get_recent_transcripts(limit=25):
    """Ru00e9cupu00e8re les transcriptions ru00e9centes via l'API REST"""
    url = f"{ASSEMBLY_AI_BASE_URL}/transcript"
    response = requests.get(url, headers=headers, params={"limit": limit})
    
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Erreur lors de la ru00e9cupu00e9ration des transcriptions ru00e9centes: {response.status_code}")
        logger.error(response.text)
        return []

def fix_processing_transcriptions():
    """Corrige les transcriptions bloquu00e9es en u00e9tat 'processing'"""
    # Ru00e9cupu00e9rer toutes les transcriptions en cours
    processing_meetings = get_meetings_by_status('processing')
    logger.info(f"Transcriptions en cours: {len(processing_meetings)}")
    
    if not processing_meetings:
        logger.info("Aucune transcription en cours trouvu00e9e")
        return
    
    # Ru00e9cupu00e9rer les transcriptions ru00e9centes d'AssemblyAI
    recent_transcripts = get_recent_transcripts(limit=25)
    logger.info(f"Ru00e9cupu00e9ration de {len(recent_transcripts['transcripts']) if isinstance(recent_transcripts, dict) and 'transcripts' in recent_transcripts else 0} transcriptions ru00e9centes d'AssemblyAI")
    
    # Traiter chaque transcription
    for meeting in processing_meetings:
        try:
            meeting_id = meeting['id']
            user_id = meeting['user_id']
            transcript_text = meeting.get('transcript_text', '')
            file_url = meeting.get('file_url', '')
            
            logger.info(f"Vu00e9rification de la ru00e9union {meeting_id}")
            logger.info(f"Texte actuel: {transcript_text}")
            logger.info(f"Fichier: {file_url}")
            
            # Mu00e9thode 1: Essayer d'extraire l'ID de transcription AssemblyAI du texte
            if transcript_text and 'ID:' in transcript_text:
                try:
                    # Extraire l'ID de transcription du texte
                    transcript_id = transcript_text.split('ID:')[-1].strip()
                    logger.info(f"ID de transcription AssemblyAI extrait: {transcript_id}")
                    
                    # Vu00e9rifier le statut de la transcription
                    transcript_data = get_transcript_status(transcript_id)
                    
                    if not transcript_data:
                        logger.error(f"Impossible de ru00e9cupu00e9rer les donnu00e9es de la transcription {transcript_id}")
                        continue
                    
                    logger.info(f"Statut de la transcription {transcript_id}: {transcript_data.get('status')}")
                    
                    if transcript_data.get('status') == "completed":
                        # Traiter la transcription terminu00e9e
                        logger.info(f"Transcription {transcript_id} terminu00e9e, mise u00e0 jour de la base de donnu00e9es")
                        
                        # Mettre u00e0 jour la base de donnu00e9es
                        update_meeting(meeting_id, user_id, {
                            "transcript_status": "completed",
                            "transcript_text": transcript_data.get('text', ''),
                            "duration_seconds": transcript_data.get('audio_duration'),
                            "speakers_count": len(set([u.get('speaker') for u in transcript_data.get('utterances', [])])) if transcript_data.get('utterances') else None
                        })
                        
                        logger.info(f"Mise u00e0 jour ru00e9ussie pour la ru00e9union {meeting_id}")
                    elif transcript_data.get('status') == "error":
                        # Gu00e9rer l'erreur
                        error_message = transcript_data.get('error', 'Unknown error')
                        logger.error(f"Erreur de transcription pour {meeting_id}: {error_message}")
                        update_meeting(meeting_id, user_id, {
                            "transcript_status": "error",
                            "transcript_text": f"Erreur lors de la transcription: {error_message}"
                        })
                    else:
                        # Toujours en cours
                        logger.info(f"Transcription {transcript_id} toujours en cours ({transcript_data.get('status')})")
                except Exception as e:
                    logger.error(f"Erreur lors de la vu00e9rification de la transcription: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
            else:
                logger.warning(f"Impossible d'extraire l'ID de transcription pour la ru00e9union {meeting_id}")
                
                # Mu00e9thode 2: Essayer de trouver la transcription par le nom du fichier
                if file_url and 'transcripts' in recent_transcripts:
                    file_name = os.path.basename(file_url)
                    logger.info(f"Recherche de transcription pour le fichier: {file_name}")
                    
                    for transcript in recent_transcripts['transcripts']:
                        if file_name in transcript.get('audio_url', ''):
                            logger.info(f"Transcription trouvu00e9e pour {file_name}: {transcript.get('id')}")
                            
                            # Mettre u00e0 jour l'ID de transcription dans la base de donnu00e9es
                            update_meeting(meeting_id, user_id, {
                                "transcript_text": f"Transcription en cours de traitement. ID: {transcript.get('id')}"
                            })
                            
                            logger.info(f"ID de transcription mis u00e0 jour pour la ru00e9union {meeting_id}")
                            break
                    else:
                        logger.warning(f"Aucune transcription trouvu00e9e pour le fichier {file_name}")
        except Exception as e:
            logger.error(f"Erreur lors du traitement de la ru00e9union {meeting.get('id', 'unknown')}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

def check_specific_transcription(meeting_id, user_id):
    """Vu00e9rifie le statut d'une transcription spu00e9cifique"""
    try:
        # Ru00e9cupu00e9rer les informations de la ru00e9union
        meeting = get_meeting(meeting_id, user_id)
        if not meeting:
            logger.error(f"Ru00e9union {meeting_id} non trouvu00e9e")
            return
        
        transcript_text = meeting.get('transcript_text', '')
        logger.info(f"Texte actuel: {transcript_text}")
        
        # Essayer d'extraire l'ID de transcription AssemblyAI du texte
        if transcript_text and 'ID:' in transcript_text:
            # Extraire l'ID de transcription du texte
            transcript_id = transcript_text.split('ID:')[-1].strip()
            logger.info(f"ID de transcription AssemblyAI extrait: {transcript_id}")
            
            # Vu00e9rifier le statut de la transcription
            transcript_data = get_transcript_status(transcript_id)
            
            if not transcript_data:
                logger.error(f"Impossible de ru00e9cupu00e9rer les donnu00e9es de la transcription {transcript_id}")
                return
            
            logger.info(f"Statut de la transcription {transcript_id}: {transcript_data.get('status')}")
            logger.info(f"Du00e9tails: {json.dumps(transcript_data, indent=2)}")
            
            if transcript_data.get('status') == "completed":
                # Traiter la transcription terminu00e9e
                logger.info(f"Transcription {transcript_id} terminu00e9e, mise u00e0 jour de la base de donnu00e9es")
                
                # Mettre u00e0 jour la base de donnu00e9es
                update_meeting(meeting_id, user_id, {
                    "transcript_status": "completed",
                    "transcript_text": transcript_data.get('text', ''),
                    "duration_seconds": transcript_data.get('audio_duration'),
                    "speakers_count": len(set([u.get('speaker') for u in transcript_data.get('utterances', [])])) if transcript_data.get('utterances') else None
                })
                
                logger.info(f"Mise u00e0 jour ru00e9ussie pour la ru00e9union {meeting_id}")
        else:
            logger.warning(f"Impossible d'extraire l'ID de transcription pour la ru00e9union {meeting_id}")
    except Exception as e:
        logger.error(f"Erreur lors de la vu00e9rification de la transcription: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 2:
        # Vu00e9rifier une transcription spu00e9cifique
        meeting_id = sys.argv[1]
        user_id = sys.argv[2]
        logger.info(f"Vu00e9rification de la transcription spu00e9cifique: {meeting_id} pour l'utilisateur {user_id}")
        check_specific_transcription(meeting_id, user_id)
    else:
        # Corriger toutes les transcriptions bloquu00e9es
        logger.info("Du00e9marrage de la correction des transcriptions bloquu00e9es")
        fix_processing_transcriptions()
        logger.info("Correction terminu00e9e")
