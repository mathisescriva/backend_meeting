#!/usr/bin/env python3
"""
Test de transcription avec le SDK AssemblyAI officiel
"""

import os
import logging
import sys
from dotenv import load_dotenv
import assemblyai as aai

# Charger les variables d'environnement
load_dotenv()

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('assemblyai-sdk-test')

# Récupérer la clé API
api_key = os.getenv("ASSEMBLYAI_API_KEY")
if not api_key:
    logger.error("Clé API AssemblyAI non trouvée dans les variables d'environnement")
    sys.exit(1)

aai.settings.api_key = api_key

def transcribe_audio(audio_url):
    """
    Transcrit un fichier audio avec le SDK AssemblyAI et extrait les métadonnées
    """
    logger.info(f"Démarrage de la transcription pour: {audio_url}")
    
    # Configuration avec diarisation des locuteurs activée
    config = aai.TranscriptionConfig(
        speaker_labels=True,
        language_code="fr"  # Ou "en" selon vos besoins
    )
    
    try:
        # Lancer la transcription
        transcript = aai.Transcriber().transcribe(audio_url, config)
        
        # Vérifier le statut
        logger.info(f"Statut de la transcription: {transcript.status}")
        
        if transcript.status == "completed":
            # Extraire la durée audio
            audio_duration = transcript.audio_duration
            logger.info(f"Durée audio: {audio_duration} secondes")
            
            # Extraire et compter les locuteurs uniques
            speaker_count = 0
            unique_speakers = set()
            
            # Vérifier si les utterances existent
            if transcript.utterances:
                try:
                    for utterance in transcript.utterances:
                        if hasattr(utterance, 'speaker') and utterance.speaker:
                            unique_speakers.add(utterance.speaker)
                    
                    speaker_count = len(unique_speakers)
                    logger.info(f"Utterances trouvées: {len(transcript.utterances)}")
                    logger.info(f"Locuteurs uniques: {unique_speakers}")
                except Exception as e:
                    logger.error(f"Erreur lors du traitement des utterances: {str(e)}")
            else:
                logger.warning("Aucune utterance trouvée dans la transcription")
                
                # Essayer de trouver les speakers dans les mots s'ils sont disponibles
                if hasattr(transcript, 'words') and transcript.words:
                    try:
                        for word in transcript.words:
                            if hasattr(word, 'speaker') and word.speaker:
                                unique_speakers.add(word.speaker)
                        
                        speaker_count = len(unique_speakers)
                        logger.info(f"Speakers trouvés via les mots: {unique_speakers}")
                    except Exception as e:
                        logger.error(f"Erreur lors du traitement des mots: {str(e)}")
            
            # S'assurer qu'il y a au moins 1 locuteur
            if speaker_count == 0:
                speaker_count = 1
                logger.warning("Aucun locuteur détecté, on force à 1")
            
            logger.info(f"Nombre de locuteurs: {speaker_count}")
            
            # Afficher le texte transcrit
            logger.info("Texte transcrit:")
            logger.info(transcript.text)
            
            # Afficher les attributs disponibles pour le débogage
            logger.info("Attributs disponibles dans la transcription:")
            for attr in dir(transcript):
                if not attr.startswith('_'):
                    logger.info(f" - {attr}")
            
            # Formater le texte par locuteur si possible
            formatted_text = transcript.text
            utterances_data = []
            
            if transcript.utterances:
                try:
                    utterances_text = []
                    for utterance in transcript.utterances:
                        speaker = getattr(utterance, 'speaker', 'Unknown')
                        text = getattr(utterance, 'text', '')
                        # Format uniforme: "Speaker A: texte" avec préfixe "Speaker"
                        utterances_text.append(f"Speaker {speaker}: {text}")
                        utterances_data.append({"speaker": speaker, "text": text})
                    formatted_text = "\n".join(utterances_text)
                except Exception as e:
                    logger.warning(f"Erreur lors de la formatage des utterances: {str(e)}")
            
            # Retourner les données importantes
            return {
                "status": "completed",
                "text": formatted_text,
                "raw_text": transcript.text,
                "audio_duration": audio_duration,
                "speakers_count": speaker_count,
                "utterances": utterances_data,
                "id": transcript.id
            }
        else:
            logger.error(f"La transcription a échoué avec le statut: {transcript.status}")
            return {
                "status": "error",
                "error": f"Transcription failed with status: {transcript.status}"
            }
    
    except Exception as e:
        logger.error(f"Erreur lors de la transcription: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {"status": "error", "error": str(e)}

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_assemblyai_sdk.py <audio_url>")
        print("Example: python test_assemblyai_sdk.py https://example.com/audio.mp3")
        print("Example: python test_assemblyai_sdk.py /path/to/local/file.mp3")
        sys.exit(1)
    
    audio_url = sys.argv[1]
    
    # Si c'est un chemin local, vérifier qu'il existe
    if audio_url.startswith('/'):
        if not os.path.exists(audio_url):
            logger.error(f"Le fichier local n'existe pas: {audio_url}")
            sys.exit(1)
        
        logger.info(f"Fichier local trouvé: {audio_url}")
    
    result = transcribe_audio(audio_url)
    
    # Afficher le résultat final
    import json
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
