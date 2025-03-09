#!/usr/bin/env python3
"""
Script pour tester la réponse de l'API AssemblyAI et le traitement des métadonnées
"""

import sys
import os
import logging
import json
import requests
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

# Récupérer la clé API depuis les variables d'environnement
ASSEMBLYAI_API_KEY = os.environ.get("ASSEMBLYAI_API_KEY")

if not ASSEMBLYAI_API_KEY:
    print("ERREUR: La clé API AssemblyAI n'est pas définie dans le fichier .env")
    sys.exit(1)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('api-debugger')

def check_api_response(transcript_id):
    """
    Récupère et affiche la réponse brute de l'API AssemblyAI
    pour analyser les données de métadonnées
    """
    try:
        endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
        
        headers = {
            "authorization": ASSEMBLYAI_API_KEY,
            "content-type": "application/json"
        }
        
        logger.info(f"Requête à AssemblyAI pour la transcription {transcript_id}")
        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()
        
        # Récupérer la réponse sous forme de dictionnaire
        result = response.json()
        
        # Enregistrer la réponse brute dans un fichier pour analyse
        with open(f"transcript_{transcript_id}.json", "w") as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Réponse sauvegardée dans transcript_{transcript_id}.json")
        
        # Vérifier et afficher les métadonnées importantes
        logger.info(f"Status: {result.get('status')}")
        
        # Vérifier les métadonnées d'intérêt
        audio_duration = result.get('audio_duration')
        logger.info(f"Audio Duration brute: {audio_duration}")
        
        if audio_duration is not None:
            try:
                audio_duration = int(float(audio_duration))
                logger.info(f"Audio Duration convertie: {audio_duration}")
            except (ValueError, TypeError):
                logger.warning(f"Impossible de convertir la durée audio: {audio_duration}")
        
        # Vérifier le nombre de locuteurs
        speakers_count = result.get('speaker_count')
        logger.info(f"Speaker Count directement de l'API: {speakers_count}")
        
        # Si pas disponible directement, calculer à partir des utterances
        if speakers_count is None:
            utterances = result.get('utterances', [])
            speakers_set = set()
            
            if utterances:
                for utterance in utterances:
                    speaker = utterance.get('speaker')
                    if speaker:
                        speakers_set.add(speaker)
                
                speakers_count = len(speakers_set)
                logger.info(f"Speaker Count calculé à partir des utterances: {speakers_count}")
            else:
                # Essayer de calculer à partir des mots
                words = result.get('words', [])
                speaker_ids = set()
                
                for word in words:
                    if 'speaker' in word:
                        speaker_ids.add(word['speaker'])
                
                if speaker_ids:
                    speakers_count = len(speaker_ids)
                    logger.info(f"Speaker Count calculé à partir des mots: {speakers_count}")
                else:
                    logger.warning("Impossible de calculer le nombre de locuteurs")
        
        # Afficher des statistiques sur les utterances et mots
        utterances = result.get('utterances', [])
        words = result.get('words', [])
        
        logger.info(f"Nombre d'utterances: {len(utterances)}")
        logger.info(f"Nombre de mots: {len(words)}")
        
        # Afficher un échantillon des données pour vérification
        if utterances:
            logger.info("Exemple d'utterance:")
            logger.info(json.dumps(utterances[0], indent=2))
        
        if words:
            logger.info("Exemple de mot:")
            logger.info(json.dumps(words[0], indent=2))
        
    except Exception as e:
        logger.error(f"Erreur lors de la vérification de l'API: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_api_response.py <transcript_id>")
        sys.exit(1)
    
    transcript_id = sys.argv[1]
    check_api_response(transcript_id)

if __name__ == "__main__":
    main()
