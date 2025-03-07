#!/usr/bin/env python3
"""
Script amélioré pour traiter les réunions en attente sans utiliser de threads.
Ce script contourne le problème de SQLite avec les threads en exécutant tout dans le thread principal.
"""

import os
import sys
import sqlite3
import requests
import time
import logging
from pathlib import Path
import subprocess

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('fix_transcriptions')

# Chemin de base pour les uploads (ajuster selon votre configuration)
BASE_UPLOADS_DIR = Path(__file__).resolve().parent / "uploads"

# Clé API AssemblyAI (à remplacer par votre clé)
# Nous récupérons la clé depuis le fichier .env
import os
from dotenv import load_dotenv
load_dotenv()
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "")
ASSEMBLYAI_API_URL = 'https://api.assemblyai.com/v2'

def get_pending_meetings():
    """Récupère toutes les réunions en attente de transcription"""
    conn = sqlite3.connect('app.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id, user_id, file_url FROM meetings WHERE transcript_status='pending'")
        meetings = cursor.fetchall()
        return [dict(meeting) for meeting in meetings]  # Convertir en dictionnaires
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des réunions en attente: {e}")
        return []
    finally:
        conn.close()

def update_meeting_status(meeting_id, user_id, status, text=None, duration=None, speakers=None):
    """Met à jour le statut d'une réunion dans la base de données"""
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    try:
        update_data = {"transcript_status": status}
        if text is not None:
            update_data["transcript_text"] = text
        if duration is not None:
            update_data["duration_seconds"] = duration
        if speakers is not None:
            update_data["speakers_count"] = speakers
            
        # Construire la requête SQL
        set_clause = ", ".join([f"{key} = ?" for key in update_data.keys()])
        params = list(update_data.values()) + [meeting_id, user_id]
        
        sql = f"""
        UPDATE meetings 
        SET {set_clause} 
        WHERE id = ? AND user_id = ?
        """
        
        cursor.execute(sql, params)
        conn.commit()
        
        if cursor.rowcount > 0:
            logger.info(f"Statut de la réunion {meeting_id} mis à jour à '{status}'")
            return True
        else:
            logger.warning(f"Aucune mise à jour pour la réunion {meeting_id}")
            return False
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du statut: {e}")
        return False
    finally:
        conn.close()

def upload_file_to_assemblyai(file_path):
    """Télécharge un fichier sur le serveur d'AssemblyAI"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Fichier introuvable: {file_path}")
        
    logger.info(f"Upload du fichier: {file_path}")
    
    headers = {
        'authorization': ASSEMBLYAI_API_KEY
    }
    
    with open(file_path, 'rb') as f:
        response = requests.post(
            'https://api.assemblyai.com/v2/upload',
            headers=headers,
            data=f
        )
    
    if response.status_code == 200:
        upload_url = response.json()['upload_url']
        logger.info(f"Fichier uploadé avec succès: {upload_url}")
        return upload_url
    else:
        logger.error(f"Erreur lors de l'upload: {response.status_code} {response.text}")
        raise Exception(f"Erreur lors de l'upload: {response.status_code}")

def start_transcription(audio_url):
    """Démarre une transcription sur AssemblyAI"""
    headers = {
        "authorization": ASSEMBLYAI_API_KEY,
        "content-type": "application/json"
    }
    
    json_data = {
        "audio_url": audio_url,
        "speaker_labels": True,
        "language_code": "fr"
    }
    
    response = requests.post(
        "https://api.assemblyai.com/v2/transcript",
        json=json_data,
        headers=headers
    )
    
    if response.status_code == 200:
        transcript_id = response.json()['id']
        logger.info(f"Transcription démarrée avec ID: {transcript_id}")
        return transcript_id
    else:
        logger.error(f"Erreur lors du démarrage de la transcription: {response.status_code} {response.text}")
        raise Exception(f"Erreur lors du démarrage de la transcription: {response.status_code}")

def get_transcription_status(transcript_id):
    """Vérifie le statut d'une transcription"""
    headers = {
        "authorization": ASSEMBLYAI_API_KEY
    }
    
    response = requests.get(
        f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Erreur lors de la vérification du statut: {response.status_code} {response.text}")
        raise Exception(f"Erreur lors de la vérification du statut: {response.status_code}")

def process_transcription(meeting_id, user_id, file_url):
    """Traite une transcription de bout en bout sans thread"""
    try:
        logger.info(f"Traitement de la réunion {meeting_id} pour l'utilisateur {user_id}")
        logger.info(f"Fichier audio: {file_url}")
        
        # Mettre à jour le statut à "processing"
        update_meeting_status(meeting_id, user_id, "processing")
        
        # Construire le chemin complet du fichier
        if file_url.startswith('/'):
            file_url = file_url[1:]  # Enlever le / initial si présent
        file_path = os.path.join(os.path.dirname(__file__), file_url)
        
        logger.info(f"Chemin complet du fichier: {file_path}")
        
        # Vérifier que le fichier existe
        if not os.path.exists(file_path):
            error_msg = f"Fichier audio introuvable: {file_path}"
            logger.error(error_msg)
            update_meeting_status(meeting_id, user_id, "error", text=error_msg)
            return False
        
        # Upload vers AssemblyAI
        try:
            upload_url = upload_file_to_assemblyai(file_path)
        except Exception as e:
            logger.error(f"Erreur lors de l'upload: {e}")
            update_meeting_status(meeting_id, user_id, "error", text=f"Erreur lors de l'upload: {str(e)}")
            return False
            
        # Démarrer la transcription
        try:
            transcript_id = start_transcription(upload_url)
        except Exception as e:
            logger.error(f"Erreur lors du démarrage de la transcription: {e}")
            update_meeting_status(meeting_id, user_id, "error", text=f"Erreur lors du démarrage de la transcription: {str(e)}")
            return False
            
        # Attendre et vérifier le résultat
        max_retries = 10  # Limiter pour le test, augmenter en production
        retry_delay = 10  # secondes
        
        for attempt in range(max_retries):
            logger.info(f"Vérification du statut, tentative {attempt+1}/{max_retries}")
            
            try:
                transcript_response = get_transcription_status(transcript_id)
                status = transcript_response.get('status')
                
                logger.info(f"Statut de la transcription: {status}")
                
                if status == 'completed':
                    # Transcription réussie
                    transcription_text = transcript_response.get('text', '')
                    
                    # Récupérer les informations sur les interlocuteurs si disponibles
                    utterances = transcript_response.get('utterances', [])
                    
                    # Extraire la durée de l'audio (en secondes)
                    audio_duration = transcript_response.get('audio_duration', 0)
                    
                    # Calculer le nombre unique de speakers
                    speakers_set = set()
                    if utterances:
                        # Formater le texte avec les interlocuteurs
                        formatted_text = []
                        for utterance in utterances:
                            speaker = utterance.get('speaker', 'Unknown')
                            speakers_set.add(speaker)
                            text = utterance.get('text', '')
                            formatted_text.append(f"Speaker {speaker}: {text}")
                        
                        transcription_text = "\n".join(formatted_text)
                    
                    speakers_count = len(speakers_set)
                    
                    logger.info(f"Durée audio: {audio_duration} secondes, Nombre de participants: {speakers_count}")
                    
                    # Mettre à jour la base de données
                    update_meeting_status(
                        meeting_id, 
                        user_id, 
                        "completed", 
                        text=transcription_text,
                        duration=int(audio_duration) if audio_duration else None,
                        speakers=speakers_count if speakers_count > 0 else None
                    )
                    
                    logger.info(f"Transcription terminée avec succès pour la réunion {meeting_id}")
                    return True
                    
                elif status == 'error':
                    # Erreur de transcription
                    error_message = transcript_response.get('error', 'Unknown error')
                    logger.error(f"Erreur de transcription: {error_message}")
                    
                    update_meeting_status(meeting_id, user_id, "error", text=f"Erreur de transcription: {error_message}")
                    return False
                
                # Si le statut est "queue" ou "processing", attendre et réessayer
                time.sleep(retry_delay)
                
            except Exception as e:
                logger.error(f"Erreur lors de la vérification du statut: {e}")
                
        # Si on arrive ici, c'est que le temps est écoulé
        update_meeting_status(meeting_id, user_id, "timeout")
        logger.warning(f"Timeout pour la transcription de la réunion {meeting_id}")
        return False
        
    except Exception as e:
        logger.error(f"Erreur non gérée lors du traitement de la réunion {meeting_id}: {e}")
        update_meeting_status(meeting_id, user_id, "error", text=f"Erreur non gérée: {str(e)}")
        return False

def main():
    logger.info("Démarrage de la correction des transcriptions en attente...")
    
    # Récupérer toutes les réunions en attente
    pending_meetings = get_pending_meetings()
    logger.info(f"Nombre de réunions en attente: {len(pending_meetings)}")
    
    if not pending_meetings:
        logger.info("Aucune réunion en attente trouvée.")
        return
        
    # Traiter chaque réunion
    success_count = 0
    for meeting in pending_meetings:
        meeting_id = meeting['id']
        user_id = meeting['user_id']
        file_url = meeting['file_url']
        
        if process_transcription(meeting_id, user_id, file_url):
            success_count += 1
            
    logger.info(f"Traitement terminé. {success_count}/{len(pending_meetings)} réunions transcrites avec succès.")

if __name__ == "__main__":
    main()
