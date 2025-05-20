import os
import requests
import logging
from dotenv import load_dotenv

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('transcript-checker')

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

def check_transcript_status(transcript_id):
    """Vu00e9rifie le statut d'une transcription spu00e9cifique"""
    url = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        transcript_data = response.json()
        status = transcript_data.get('status')
        logger.info(f"Statut de la transcription {transcript_id}: {status}")
        
        # Afficher plus de du00e9tails selon le statut
        if status == 'processing':
            percent_complete = transcript_data.get('percent_complete', 0)
            logger.info(f"Progression: {percent_complete}%")
        elif status == 'completed':
            audio_duration = transcript_data.get('audio_duration', 0)
            word_count = transcript_data.get('words', [])
            word_count = len(word_count) if isinstance(word_count, list) else 0
            logger.info(f"Duru00e9e audio: {audio_duration} secondes")
            logger.info(f"Nombre de mots: {word_count}")
            
            # Afficher un extrait du texte
            text = transcript_data.get('text', '')
            if text:
                preview = text[:200] + '...' if len(text) > 200 else text
                logger.info(f"Aperu00e7u du texte: {preview}")
        elif status == 'error':
            error = transcript_data.get('error', 'Unknown error')
            logger.error(f"Erreur: {error}")
        
        return transcript_data
    else:
        logger.error(f"Erreur lors de la ru00e9cupu00e9ration du statut: {response.status_code} - {response.text}")
        return None

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python check_transcript_status.py <transcript_id>")
        sys.exit(1)
    
    transcript_id = sys.argv[1]
    logger.info(f"Vu00e9rification du statut de la transcription {transcript_id}")
    check_transcript_status(transcript_id)
