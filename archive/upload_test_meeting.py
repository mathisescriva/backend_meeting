#!/usr/bin/env python3
"""
Script pour tester le téléchargement d'une réunion et sa transcription automatique.
"""

import requests
import sys
import logging
import time
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('upload-test')

# Configuration
API_URL = "http://localhost:8000"
FILE_PATH = "/Users/mathisescriva/CascadeProjects/MeetingTranscriberBackend/uploads/2dafc076-4cbe-4000-b62e-60b8935746c4/20250306_171028_tmpji5whyxw.wav"
TITLE = "test_auto_" + str(int(time.time()))

def login():
    """Authentification pour récupérer un token"""
    login_url = f"{API_URL}/auth/login"
    
    # Utiliser le format d'application/x-www-form-urlencoded au lieu de JSON
    data = {
        "username": "test_new@example.com", 
        "password": "password123"
    }
    
    response = requests.post(login_url, data=data)
    
    if response.status_code == 200:
        result = response.json()
        logger.info("Authentification réussie")
        return result.get("access_token")
    else:
        logger.error(f"Erreur d'authentification: {response.text}")
        return None

def upload_meeting(file_path, title, token):
    """Télécharger une réunion et lancer sa transcription"""
    upload_url = f"{API_URL}/meetings/upload"
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    with open(file_path, "rb") as f:
        files = {
            "file": (Path(file_path).name, f, "audio/wav")
        }
        data = {
            "title": title
        }
        
        logger.info(f"Téléchargement du fichier {file_path} avec le titre '{title}'")
        response = requests.post(
            upload_url,
            headers=headers,
            files=files,
            data=data
        )
    
    if response.status_code == 200:
        result = response.json()
        logger.info(f"Réunion créée avec succès. ID: {result.get('id')}")
        return result
    else:
        logger.error(f"Erreur lors du téléchargement: {response.text}")
        return None

def check_meeting_status(meeting_id, token, max_attempts=10):
    """Vérifier le statut d'une réunion"""
    meeting_url = f"{API_URL}/meetings/{meeting_id}"
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    for attempt in range(1, max_attempts + 1):
        response = requests.get(meeting_url, headers=headers)
        
        if response.status_code == 200:
            meeting = response.json()
            status = meeting.get("transcript_status")
            logger.info(f"Statut de la transcription (tentative {attempt}/{max_attempts}): {status}")
            
            if status == "completed":
                return meeting
            elif status == "error":
                logger.error(f"Erreur de transcription: {meeting.get('transcript_text')}")
                return meeting
        else:
            logger.error(f"Erreur lors de la vérification: {response.text}")
        
        # Attendre avant la prochaine vérification
        wait_time = min(5 * attempt, 30)
        logger.info(f"Attente avant la prochaine vérification ({wait_time}s)")
        time.sleep(wait_time)
    
    logger.warning("Nombre maximum de tentatives atteint")
    return None

def main():
    """Fonction principale"""
    logger.info("Démarrage du test d'upload et de transcription")
    
    # Obtenir un nouveau token
    token = login()
    if not token:
        logger.error("Impossible de se connecter")
        return
    
    # Télécharger la réunion
    meeting = upload_meeting(FILE_PATH, TITLE, token)
    if not meeting:
        logger.error("Impossible de télécharger la réunion")
        return
    
    # Vérifier le statut
    meeting_id = meeting.get("id")
    final_meeting = check_meeting_status(meeting_id, token)
    
    if final_meeting:
        status = final_meeting.get("transcript_status")
        if status == "completed":
            logger.info("La transcription a été complétée avec succès")
            logger.info(f"Texte de la transcription: {final_meeting.get('transcript_text')[:100]}...")
        else:
            logger.warning(f"La transcription n'a pas été complétée. Statut final: {status}")
    else:
        logger.error("Impossible de vérifier le statut final de la transcription")

if __name__ == "__main__":
    main()
