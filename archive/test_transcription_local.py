import os
import sys
import time
import json
import requests
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test-transcription")

# URL de base de l'API
BASE_URL = "http://localhost:8000"

# Fonction pour s'authentifier
def login():
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            data={"username": "testing.admin@gilbert.fr", "password": "password123"}
        )
        if response.status_code == 200:
            token_data = response.json()
            return token_data.get("access_token")
        else:
            logger.error(f"Erreur d'authentification: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Exception lors de l'authentification: {str(e)}")
        return None

# Fonction pour uploader un fichier audio
def upload_meeting(token, file_path, title="Test Meeting"):
    try:
        headers = {"Authorization": f"Bearer {token}"}
        files = {"file": open(file_path, "rb")}
        data = {"title": title}
        
        response = requests.post(
            f"{BASE_URL}/simple/meetings/upload",
            headers=headers,
            files=files,
            data=data
        )
        
        if response.status_code == 200:
            meeting_data = response.json()
            logger.info(f"Réunion créée avec succès: {meeting_data['id']}")
            return meeting_data
        else:
            logger.error(f"Erreur lors de l'upload: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Exception lors de l'upload: {str(e)}")
        return None

# Fonction pour vérifier le statut d'une réunion
def check_meeting_status(token, meeting_id):
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{BASE_URL}/simple/meetings/{meeting_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            meeting_data = response.json()
            status = meeting_data.get("transcript_status")
            logger.info(f"Statut de la réunion {meeting_id}: {status}")
            return meeting_data
        else:
            logger.error(f"Erreur lors de la vérification: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Exception lors de la vérification: {str(e)}")
        return None

# Fonction principale
def main():
    # Chemin vers le fichier audio de test
    audio_file = "test_audio.mp3"
    if not os.path.exists(audio_file):
        logger.error(f"Le fichier audio {audio_file} n'existe pas")
        return
    
    # S'authentifier
    token = login()
    if not token:
        logger.error("Impossible de s'authentifier")
        return
    
    # Uploader le fichier audio
    meeting = upload_meeting(token, audio_file, "Test Transcription Local")
    if not meeting:
        logger.error("Impossible d'uploader le fichier audio")
        return
    
    meeting_id = meeting["id"]
    logger.info(f"Réunion créée avec l'ID: {meeting_id}")
    
    # Vérifier le statut de la réunion toutes les 10 secondes pendant 5 minutes maximum
    max_checks = 30  # 5 minutes (30 * 10 secondes)
    checks = 0
    
    while checks < max_checks:
        meeting_data = check_meeting_status(token, meeting_id)
        if not meeting_data:
            logger.error("Impossible de vérifier le statut de la réunion")
            break
        
        status = meeting_data.get("transcript_status")
        
        if status == "completed":
            logger.info("Transcription terminée avec succès!")
            logger.info(f"Texte de transcription: {meeting_data.get('transcript_text')[:200]}...")
            break
        elif status == "error":
            logger.error(f"Erreur de transcription: {meeting_data.get('transcript_text')}")
            break
        
        logger.info(f"En attente... Statut actuel: {status}")
        time.sleep(10)
        checks += 1
    
    if checks >= max_checks:
        logger.warning("Timeout: La transcription n'a pas été terminée dans le délai imparti")

if __name__ == "__main__":
    main()
