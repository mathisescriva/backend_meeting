import os
import sys
import logging
from pathlib import Path
import json
import argparse

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("direct-transcription-test")

# Assurez-vous que le chemin du projet est dans sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from app.services.assemblyai import upload_file_to_assemblyai, start_transcription, check_transcription_status
from app.db.database import get_db_connection, release_db_connection
from app.db.queries import update_meeting, get_meeting, normalize_transcript_format

# Valeurs par défaut
DEFAULT_MEETING_ID = "fef3831e-be19-47f6-b0fb-c7360d9ede3b"
DEFAULT_USER_ID = "4abe545a-7a8f-4c02-9758-d44db6045ed5"

def test_direct_transcription(meeting_id, user_id, force_reprocess=False):
    try:
        # Récupérer les informations de la réunion
        meeting = get_meeting(meeting_id, user_id)
        if not meeting:
            logger.error(f"Réunion {meeting_id} non trouvée pour l'utilisateur {user_id}")
            return
        
        logger.info(f"Informations de la réunion: {meeting}")
        file_url = meeting.get('file_url')
        
        # Vérifier le statut actuel
        current_status = meeting.get('transcript_status')
        if current_status == 'completed' and not force_reprocess:
            logger.info(f"La transcription est déjà complète. Utilisez force_reprocess=True pour forcer le retraitement.")
            return
        
        # Vérifier si le fichier existe
        if file_url.startswith("/uploads/"):
            file_path = BASE_DIR / file_url.lstrip('/')
            logger.info(f"Chemin du fichier: {file_path}")
            
            if not os.path.exists(file_path):
                logger.error(f"Fichier non trouvé: {file_path}")
                return
            
            logger.info(f"Le fichier existe et sa taille est: {os.path.getsize(file_path)} bytes")
            
            # Mettre à jour le statut en "processing"
            update_meeting(meeting_id, user_id, {"transcript_status": "processing"})
            
            # Étape 1: Upload du fichier vers AssemblyAI
            logger.info("Étape 1: Upload du fichier vers AssemblyAI")
            upload_url = upload_file_to_assemblyai(str(file_path))
            logger.info(f"Fichier uploadé à: {upload_url}")
            
            # Étape 2: Démarrer la transcription (avec speaker_labels=True)
            logger.info("Étape 2: Démarrage de la transcription avec diarisation")
            transcript_id = start_transcription(upload_url, format_text=True)
            logger.info(f"Transcription lancée avec ID: {transcript_id}")
            
            # Étape 3: Vérifier périodiquement le statut
            logger.info("Étape 3: Vérification du statut")
            MAX_CHECKS = 30
            INTERVAL_SECONDS = 10
            
            for check in range(MAX_CHECKS):
                logger.info(f"Vérification {check+1}/{MAX_CHECKS}...")
                status_response = check_transcription_status(transcript_id)
                status = status_response.get('status')
                logger.info(f"Statut: {status}")
                
                if status == 'completed':
                    # Transcription terminée avec succès
                    logger.info("Transcription terminée!")
                    
                    # Vérifier les utterances
                    utterances = status_response.get('utterances')
                    logger.info(f"Présence d'utterances: {utterances is not None and len(utterances) > 0}")
                    logger.info(f"Type de utterances: {type(utterances)}")
                    logger.info(f"Nombre d'utterances: {len(utterances) if utterances else 0}")
                    
                    # Formater la transcription avec les locuteurs
                    speakers_set = set()
                    formatted_text = ""
                    
                    if utterances and len(utterances) > 0:
                        formatted_lines = []
                        for utterance in utterances:
                            speaker = utterance.get('speaker', 'Unknown')
                            speakers_set.add(speaker)
                            text_segment = utterance.get('text', '')
                            # Format: "Speaker A: texte"
                            formatted_lines.append(f"Speaker {speaker}: {text_segment}")
                        
                        formatted_text = "\n".join(formatted_lines)
                        logger.info(f"Transcription formatée avec {len(speakers_set)} locuteurs")
                        
                        # Afficher les 3 premières utterances
                        for i, line in enumerate(formatted_lines[:3]):
                            logger.info(f"Utterance {i+1}: {line[:100]}...")
                    else:
                        # Pas d'utterances, utiliser le texte brut
                        raw_text = status_response.get('text', '')
                        formatted_text = f"Speaker A: {raw_text}"
                        speakers_set.add('A')
                        logger.info("Pas d'utterances, texte brut utilisé avec Speaker A")
                    
                    # Normaliser le format du texte avant l'update
                    formatted_text = normalize_transcript_format(formatted_text)
                    
                    # Mettre à jour la base de données
                    speakers_count = len(speakers_set)
                    logger.info(f"Mise à jour de la base de données avec {speakers_count} locuteurs")
                    
                    update_data = {
                        "transcript_text": formatted_text,
                        "transcript_status": "completed",
                        "speakers_count": speakers_count
                    }
                    
                    update_result = update_meeting(meeting_id, user_id, update_data)
                    logger.info(f"Mise à jour de la base de données: {'Succès' if update_result else 'Échec'}")
                    
                    # Vérifier que la mise à jour a été effectuée
                    updated_meeting = get_meeting(meeting_id, user_id)
                    if updated_meeting:
                        logger.info(f"Statut après mise à jour: {updated_meeting.get('transcript_status')}")
                        logger.info(f"Nombre de locuteurs: {updated_meeting.get('speakers_count')}")
                        logger.info(f"Taille du texte: {len(updated_meeting.get('transcript_text', ''))}")
                        logger.info(f"Début de la transcription: {updated_meeting.get('transcript_text', '')[:200]}...")
                    
                    return True
                
                elif status == 'error':
                    # Erreur lors de la transcription
                    error_message = status_response.get('error', 'Unknown error')
                    logger.error(f"Erreur de transcription: {error_message}")
                    update_meeting(meeting_id, user_id, {"transcript_status": "error"})
                    return False
                
                # Attendre avant la prochaine vérification
                if check < MAX_CHECKS - 1:
                    logger.info(f"Attente de {INTERVAL_SECONDS} secondes...")
                    import time
                    time.sleep(INTERVAL_SECONDS)
            
            logger.warning(f"Nombre maximum de vérifications ({MAX_CHECKS}) atteint sans complétion")
            return False
    
    except Exception as e:
        logger.error(f"Erreur: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("=== DÉMARRAGE DU TEST DE TRANSCRIPTION DIRECTE ===")
    
    # Parser les arguments de ligne de commande
    parser = argparse.ArgumentParser(description='Test de transcription directe')
    parser.add_argument('--meeting_id', type=str, default=DEFAULT_MEETING_ID,
                        help=f'ID de la réunion à traiter (défaut: {DEFAULT_MEETING_ID})')
    parser.add_argument('--user_id', type=str, default=DEFAULT_USER_ID,
                        help=f'ID de l\'utilisateur (défaut: {DEFAULT_USER_ID})')
    parser.add_argument('--force', action='store_true',
                        help='Forcer le retraitement même si la transcription est déjà complète')
    
    args = parser.parse_args()
    
    # Exécuter avec les paramètres passés
    test_direct_transcription(args.meeting_id, args.user_id, force_reprocess=args.force)
    
    logger.info("=== FIN DU TEST ===")
