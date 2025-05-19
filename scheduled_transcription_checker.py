#!/usr/bin/env python3
"""
Script de vérification périodique des transcriptions
À exécuter via cron ou un autre planificateur de tâches

Exemple de configuration cron (vérification toutes les 15 minutes):
*/15 * * * * cd /chemin/vers/MeetingTranscriberBackend && python scheduled_transcription_checker.py >> logs/transcription_checker.log 2>&1
"""

import sqlite3
import requests
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("scheduled-checker")

# Paramètres
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "app.db"
ASSEMBLYAI_API_KEY = "3419005ee6924e08a14235043cabcd4e"
MAX_RETRIES = 3  # Nombre maximal de tentatives en cas d'erreur
RETRY_DELAY = 5  # Délai entre les tentatives (secondes)

def get_db_connection():
    """Obtenir une connexion à la base de données"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_processing_meetings():
    """Récupérer toutes les réunions en cours de traitement"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, user_id, title, transcript_id, transcript_status, created_at FROM meetings WHERE transcript_status = 'processing'"
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def get_pending_meetings():
    """Récupérer toutes les réunions en attente de traitement"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, user_id, title, transcript_id, transcript_status, created_at FROM meetings WHERE transcript_status = 'pending'"
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def get_assemblyai_transcript_details(transcript_id):
    """Récupérer les détails d'une transcription AssemblyAI"""
    headers = {
        "authorization": ASSEMBLYAI_API_KEY
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            url = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Erreur lors de la récupération des détails de la transcription: {response.status_code} - {response.text}")
                if attempt < MAX_RETRIES - 1:
                    logger.info(f"Nouvelle tentative dans {RETRY_DELAY} secondes...")
                    time.sleep(RETRY_DELAY)
                else:
                    return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des détails de la transcription: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                logger.info(f"Nouvelle tentative dans {RETRY_DELAY} secondes...")
                time.sleep(RETRY_DELAY)
            else:
                return None
    
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
    """Mettre à jour une réunion dans la base de données"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Construire la requête SQL dynamiquement
        set_clause = ", ".join([f"{key} = ?" for key in update_data.keys()])
        values = list(update_data.values())
        values.append(meeting_id)  # Pour la clause WHERE
        
        query = f"UPDATE meetings SET {set_clause} WHERE id = ?"
        logger.info(f"Exécution de la requête: {query} avec les valeurs: {values}")
        
        cursor.execute(query, values)
        conn.commit()
        
        logger.info(f"Réunion {meeting_id} mise à jour avec succès")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour de la réunion {meeting_id}: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

def check_processing_meetings():
    """Vérifier et mettre à jour les réunions en cours de traitement"""
    processing_meetings = get_processing_meetings()
    logger.info(f"Réunions en cours de traitement: {len(processing_meetings)}")
    
    for meeting in processing_meetings:
        meeting_id = meeting['id']
        transcript_id = meeting['transcript_id']
        title = meeting['title']
        created_at = meeting.get('created_at', '')
        
        # Calculer l'âge de la transcription
        age_in_hours = 0
        if created_at:
            try:
                created_datetime = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                age = datetime.now() - created_datetime
                age_in_hours = age.total_seconds() / 3600
                logger.info(f"Âge de la transcription: {age_in_hours:.2f} heures")
            except Exception as e:
                logger.error(f"Erreur lors du calcul de l'âge: {str(e)}")
        
        logger.info(f"Vérification de la réunion {meeting_id} - {title}")
        
        # Si nous avons un ID de transcription, vérifier directement
        if transcript_id:
            logger.info(f"Vérification de la transcription {transcript_id}")
            transcript_data = get_assemblyai_transcript_details(transcript_id)
            
            if transcript_data:
                status = transcript_data.get('status')
                logger.info(f"Statut de la transcription {transcript_id}: {status}")
                
                if status == 'completed':
                    # Préparer les données de mise à jour
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
                    
                    # Mettre à jour la réunion dans la base de données
                    update_meeting_in_db(meeting_id, update_data)
                elif status == 'error':
                    error_message = transcript_data.get('error', 'Unknown error')
                    update_data = {
                        "transcript_status": "error",
                        "transcript_text": f"Erreur lors de la transcription: {error_message}"
                    }
                    update_meeting_in_db(meeting_id, update_data)
                elif status == 'processing':
                    # Si la transcription est en cours depuis trop longtemps, la marquer comme en erreur
                    if age_in_hours > 2:  # 2 heures est un délai raisonnable pour la plupart des transcriptions
                        logger.warning(f"Transcription {transcript_id} en cours depuis trop longtemps ({age_in_hours:.2f} heures)")
                        update_data = {
                            "transcript_status": "error",
                            "transcript_text": f"Transcription bloquée en état 'processing' pendant plus de {age_in_hours:.2f} heures"
                        }
                        update_meeting_in_db(meeting_id, update_data)
            else:
                logger.error(f"Impossible de récupérer les détails de la transcription {transcript_id}")
                
                # Si la transcription est en cours depuis trop longtemps, la marquer comme en erreur
                if age_in_hours > 2:
                    logger.warning(f"Transcription {transcript_id} en cours depuis trop longtemps ({age_in_hours:.2f} heures)")
                    update_data = {
                        "transcript_status": "error",
                        "transcript_text": f"Impossible de vérifier le statut de la transcription après {age_in_hours:.2f} heures"
                    }
                    update_meeting_in_db(meeting_id, update_data)

def main():
    """Fonction principale"""
    logger.info("=== Démarrage de la vérification périodique des transcriptions ===")
    
    try:
        # Vérifier les réunions en cours de traitement
        check_processing_meetings()
        
        # Vérifier les réunions en attente (à implémenter si nécessaire)
        # check_pending_meetings()
        
        logger.info("Vérification terminée avec succès")
    except Exception as e:
        logger.error(f"Erreur lors de la vérification des transcriptions: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    logger.info("=== Fin de la vérification périodique des transcriptions ===")

if __name__ == "__main__":
    main()
