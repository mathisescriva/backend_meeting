#!/usr/bin/env python3
"""
Script pour corriger les métadonnées manquantes de réunions déjà transcrites
"""

import sys
import logging
import json
import os
import traceback
import requests
from app.db.queries import update_meeting, get_meetings_by_user
from app.core.config import settings

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('metadata-fixer')

def get_transcript_metadata(transcript_id):
    """Récupère les métadonnées d'une transcription depuis AssemblyAI"""
    try:
        endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
        
        headers = {
            "authorization": settings.ASSEMBLYAI_API_KEY,
            "content-type": "application/json"
        }
        
        logger.info(f"Requête à AssemblyAI pour la transcription {transcript_id}")
        response = requests.get(endpoint, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Erreur API: {response.status_code} - {response.text}")
            return None, None
            
        result = response.json()
        
        # Extraire la durée audio
        audio_duration = result.get('audio_duration')
        if audio_duration is not None:
            try:
                audio_duration = int(float(audio_duration))
            except (ValueError, TypeError):
                logger.warning(f"Impossible de convertir la durée audio: {audio_duration}")
                audio_duration = 0
        else:
            audio_duration = 0
            logger.warning("La durée audio est None, remplacée par 0")
        
        # Extraire le nombre de locuteurs
        speakers_count = result.get('speaker_count')
        
        # Si non disponible directement, calculer à partir des utterances
        if speakers_count is None:
            utterances = result.get('utterances', [])
            speakers_set = set()
            
            if utterances:
                for utterance in utterances:
                    speaker = utterance.get('speaker')
                    if speaker:
                        speakers_set.add(speaker)
            
                speakers_count = len(speakers_set)
            else:
                # Essayer de calculer à partir des mots
                words = result.get('words', [])
                speaker_ids = set()
                
                for word in words:
                    if 'speaker' in word:
                        speaker_ids.add(word['speaker'])
            
                if speaker_ids:
                    speakers_count = len(speaker_ids)
    
        # Convertir en entier si possible
        if speakers_count is not None:
            try:
                speakers_count = int(speakers_count)
            except (ValueError, TypeError):
                logger.warning(f"Impossible de convertir le nombre de locuteurs: {speakers_count}")
                speakers_count = 1
    
        # Garantir qu'il y a toujours au moins 1 locuteur
        if speakers_count is None or speakers_count == 0:
            speakers_count = 1
            logger.warning("Aucun locuteur détecté ou None, on force à 1")
        
        return audio_duration, speakers_count
    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des métadonnées: {str(e)}")
        return None, None

def fix_meeting_metadata(meeting_id, user_id, transcript_id=None):
    """Corrige les métadonnées d'une réunion spécifique"""
    try:
        logger.info(f"Correction des métadonnées pour la réunion {meeting_id}")
        
        # Si l'ID de transcription n'est pas fourni, essayer de l'extraire du texte
        if transcript_id is None:
            logger.info("ID de transcription non fourni, tentative d'extraction...")
            # Cette partie dépend de la façon dont vous stockez l'ID de transcription
            # Pour l'exemple, nous supposons qu'il n'est pas disponible
            logger.error("ID de transcription non disponible")
            return False
        
        # Récupérer les métadonnées
        audio_duration, speakers_count = get_transcript_metadata(transcript_id)
        
        if audio_duration is None and speakers_count is None:
            logger.error("Impossible de récupérer les métadonnées")
            return False
        
        logger.info(f"Métadonnées récupérées: durée={audio_duration}, locuteurs={speakers_count}")
        
        # Préparer les données à mettre à jour
        update_data = {}
        if audio_duration is not None:
            update_data["duration_seconds"] = audio_duration
        if speakers_count is not None:
            update_data["speakers_count"] = speakers_count
        
        if not update_data:
            logger.warning("Aucune métadonnée à mettre à jour")
            return False
        
        # Mettre à jour la réunion
        success = update_meeting(meeting_id, user_id, update_data)
        
        if success:
            logger.info(f"Métadonnées mises à jour pour la réunion {meeting_id}")
            return True
        else:
            logger.error(f"Échec de la mise à jour pour la réunion {meeting_id}")
            return False
    
    except Exception as e:
        logger.error(f"Erreur lors de la correction des métadonnées: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def fix_user_meetings(user_id, transcript_id_mapping=None):
    """Corrige les métadonnées pour toutes les réunions d'un utilisateur"""
    try:
        # Si aucun mapping n'est fourni, juste informer l'utilisateur qu'il en faut un
        if transcript_id_mapping is None:
            logger.warning("Aucun mapping d'ID de transcription fourni, impossible de corriger les métadonnées")
            logger.info("Créez un mapping de cette forme:")
            logger.info("transcript_id_mapping = {")
            logger.info("    'meeting_id_1': 'transcript_id_1',")
            logger.info("    'meeting_id_2': 'transcript_id_2',")
            logger.info("}")
            return
        
        # Récupérer toutes les réunions de l'utilisateur
        meetings = get_meetings_by_user(user_id)
        
        if not meetings:
            logger.info(f"Aucune réunion trouvée pour l'utilisateur {user_id}")
            return
        
        logger.info(f"Correction des métadonnées pour {len(meetings)} réunions")
        
        count_success = 0
        count_error = 0
        
        for meeting in meetings:
            meeting_id = meeting['id']
            
            # Vérifier si l'ID de transcription est disponible pour cette réunion
            if meeting_id in transcript_id_mapping:
                transcript_id = transcript_id_mapping[meeting_id]
                
                logger.info(f"Traitement de la réunion {meeting_id} avec transcription {transcript_id}")
                
                if fix_meeting_metadata(meeting_id, user_id, transcript_id):
                    count_success += 1
                else:
                    count_error += 1
            else:
                logger.warning(f"Aucun ID de transcription trouvé pour la réunion {meeting_id}")
                count_error += 1
        
        logger.info(f"Résultat final: {count_success} réussites, {count_error} échecs")
    
    except Exception as e:
        logger.error(f"Erreur globale lors de la correction des métadonnées: {str(e)}")
        logger.error(traceback.format_exc())

def main():
    if len(sys.argv) < 3:
        print("Usage: python fix_metadata.py <meeting_id> <user_id> [transcript_id]")
        sys.exit(1)
    
    meeting_id = sys.argv[1]
    user_id = sys.argv[2]
    transcript_id = sys.argv[3] if len(sys.argv) > 3 else None
    
    fix_meeting_metadata(meeting_id, user_id, transcript_id)

if __name__ == "__main__":
    main()
