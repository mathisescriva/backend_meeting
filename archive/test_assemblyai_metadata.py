#!/usr/bin/env python3
"""
Script pour tester les métadonnées renvoyées par l'API AssemblyAI
"""
import requests
import json
import os
import sys
import logging
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test-assemblyai')

# Clé API AssemblyAI
API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
if not API_KEY:
    logger.error("La variable d'environnement ASSEMBLYAI_API_KEY n'est pas définie")
    sys.exit(1)

def get_transcript_metadata(transcript_id):
    """Récupérer les métadonnées d'une transcription."""
    endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
    
    headers = {
        "authorization": API_KEY,
        "content-type": "application/json"
    }
    
    try:
        logger.info(f"Récupération des métadonnées pour la transcription {transcript_id}")
        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        # Afficher la réponse complète
        logger.info(f"Réponse complète de l'API: {json.dumps(result, indent=2)}")
        
        # Extraire les métadonnées pertinentes
        metadata = {
            "status": result.get("status"),
            "text": result.get("text", "")[:50] + "..." if result.get("text") else "",  # Tronquer le texte
            "audio_duration": result.get("audio_duration"),
            "audio_url": result.get("audio_url"),
            "words_count": len(result.get("words", [])),
            "confidence": result.get("confidence"),
            "language": result.get("language"),
        }
        
        # Vérifier si des locuteurs sont détectés
        utterances = result.get("utterances", [])
        speaker_ids = set()
        for utterance in utterances:
            if "speaker" in utterance:
                speaker_ids.add(utterance["speaker"])
        
        metadata["speakers_count"] = len(speaker_ids) if speaker_ids else None
        
        logger.info(f"Métadonnées extraites: {json.dumps(metadata, indent=2)}")
        
        return metadata
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des métadonnées: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        logger.error("Usage: python test_assemblyai_metadata.py <transcript_id>")
        sys.exit(1)
    
    transcript_id = sys.argv[1]
    get_transcript_metadata(transcript_id)
