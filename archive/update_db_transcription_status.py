import sqlite3
import requests
import logging
import os
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("db-updater")

# Paramu00e8tres
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "app.db"
ASSEMBLYAI_API_KEY = "3419005ee6924e08a14235043cabcd4e"

def get_db_connection():
    """Obtenir une connexion u00e0 la base de donnu00e9es"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_processing_meetings():
    """Ru00e9cupu00e9rer toutes les ru00e9unions en cours de traitement"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, user_id, title, transcript_id, transcript_status FROM meetings WHERE transcript_status = 'processing'"
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

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

def update_meeting_in_db(meeting_id, update_data):
    """Mettre u00e0 jour une ru00e9union dans la base de donnu00e9es"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Construire la requ00eate SQL dynamiquement
        set_clause = ", ".join([f"{key} = ?" for key in update_data.keys()])
        values = list(update_data.values())
        values.append(meeting_id)  # Pour la clause WHERE
        
        query = f"UPDATE meetings SET {set_clause} WHERE id = ?"
        logger.info(f"Exu00e9cution de la requ00eate: {query} avec les valeurs: {values}")
        
        cursor.execute(query, values)
        conn.commit()
        
        logger.info(f"Ru00e9union {meeting_id} mise u00e0 jour avec succu00e8s")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la mise u00e0 jour de la ru00e9union {meeting_id}: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

def update_transcription_statuses():
    """Mettre u00e0 jour les statuts des transcriptions en cours"""
    # Ru00e9cupu00e9rer toutes les ru00e9unions en cours de traitement
    processing_meetings = get_processing_meetings()
    logger.info(f"Ru00e9unions en cours de traitement: {len(processing_meetings)}")
    
    # Pour chaque ru00e9union en cours de traitement
    for meeting in processing_meetings:
        meeting_id = meeting['id']
        transcript_id = meeting['transcript_id']
        title = meeting['title']
        
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
                    transcript_text = transcript_data.get('text', '')
                    audio_duration = transcript_data.get('audio_duration', 0)
                    
                    # Essayer de formater avec les locuteurs si disponibles
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
                    
                    update_data = {
                        "transcript_text": transcript_text,
                        "transcript_status": "completed",
                        "duration_seconds": int(audio_duration) if audio_duration else 0,
                        "speakers_count": speakers_count
                    }
                    
                    # Mettre u00e0 jour la ru00e9union dans la base de donnu00e9es
                    update_meeting_in_db(meeting_id, update_data)
                elif status == 'error':
                    error_message = transcript_data.get('error', 'Unknown error')
                    update_data = {
                        "transcript_status": "error",
                        "transcript_text": f"Erreur lors de la transcription: {error_message}"
                    }
                    update_meeting_in_db(meeting_id, update_data)

if __name__ == "__main__":
    logger.info("Du00e9marrage de la mise u00e0 jour des statuts de transcription")
    update_transcription_statuses()
    logger.info("Mise u00e0 jour terminu00e9e")
