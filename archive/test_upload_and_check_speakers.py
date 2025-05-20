import requests
import os
import json
import time
import sys
import logging
import sqlite3
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("upload-and-check-speakers")

# Assurez-vous que le chemin du projet est dans sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from app.db.database import get_db_connection, release_db_connection

# Paramètres
BASE_URL = "http://127.0.0.1:8000"  # URL de base de l'API
EMAIL = "test@example.com"  # Email de test
PASSWORD = "password123"   # Mot de passe de test
TEST_AUDIO = "Audio7min.mp3"    # Fichier audio de test

def register_user():
    """Enregistre un utilisateur de test."""
    url = f"{BASE_URL}/auth/register"
    data = {
        "email": EMAIL,
        "password": PASSWORD,
        "full_name": "Test User"
    }
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            logger.info("Utilisateur enregistré avec succès")
            return response.json()
        else:
            logger.info(f"Erreur lors de l'enregistrement: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement: {str(e)}")
        return None

def login():
    """Se connecte avec l'utilisateur de test."""
    url = f"{BASE_URL}/auth/login"
    data = {
        "username": EMAIL,
        "password": PASSWORD
    }
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            token = response.json().get("access_token")
            logger.info(f"Connexion réussie, token: {token[:10]}...")
            return token
        else:
            logger.error(f"Erreur lors de la connexion: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Erreur lors de la connexion: {str(e)}")
        return None

def upload_meeting(token):
    """Upload une réunion de test."""
    url = f"{BASE_URL}/meetings/upload"
    headers = {"Authorization": f"Bearer {token}"}
    file_path = os.path.join(BASE_DIR, TEST_AUDIO)
    
    if not os.path.exists(file_path):
        logger.error(f"Fichier {file_path} non trouvé")
        return None
    
    logger.info(f"Upload du fichier {file_path}...")
    files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "audio/mpeg")}
    data = {"title": "Test réunion pour vérifier les locuteurs"}
    
    try:
        response = requests.post(url, headers=headers, files=files, data=data)
        if response.status_code == 200:
            meeting = response.json()
            logger.info(f"Réunion créée avec ID: {meeting.get('id')}")
            return meeting
        else:
            logger.error(f"Erreur lors de l'upload: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Erreur lors de l'upload: {str(e)}")
        return None

def check_meeting_status(token, meeting_id, max_retries=20, delay=30):
    """Vérifie périodiquement le statut de la transcription."""
    url = f"{BASE_URL}/meetings/{meeting_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    logger.info(f"Vérification du statut de la réunion {meeting_id}...")
    
    for i in range(max_retries):
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                meeting = response.json()
                status = meeting.get("transcript_status")
                logger.info(f"Statut actuel: {status} (essai {i+1}/{max_retries})")
                
                if status == "completed":
                    logger.info("Transcription terminée!")
                    return meeting
                elif status == "error":
                    logger.error("Erreur lors de la transcription")
                    return None
            else:
                logger.error(f"Erreur lors de la vérification: {response.status_code} - {response.text}")
                
            if i < max_retries - 1:
                logger.info(f"Attente de {delay} secondes avant la prochaine vérification...")
                time.sleep(delay)
                
        except Exception as e:
            logger.error(f"Erreur lors de la vérification: {str(e)}")
    
    logger.warning(f"Nombre maximum de tentatives atteint ({max_retries})")
    return None

def check_transcript_in_database(meeting_id, user_id):
    """Vérifie directement dans la base de données si la transcription contient des locuteurs."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, transcript_status, speakers_count, transcript_text FROM meetings WHERE id = ? AND user_id = ?",
            (meeting_id, user_id)
        )
        meeting = cursor.fetchone()
        
        if not meeting:
            logger.error(f"Réunion {meeting_id} non trouvée dans la base de données")
            return False
        
        logger.info(f"Informations de la réunion dans la base de données:")
        logger.info(f"  - Status: {meeting['transcript_status']}")
        logger.info(f"  - Nombre de locuteurs: {meeting['speakers_count']}")
        
        # Vérifier si la transcription contient des marqueurs de locuteurs
        transcript_text = meeting["transcript_text"] or ""
        contains_speaker_markers = "Speaker " in transcript_text
        logger.info(f"  - Contient des marqueurs de locuteurs: {contains_speaker_markers}")
        
        # Afficher les 200 premiers caractères de la transcription
        logger.info(f"  - Début de la transcription: {transcript_text[:200]}...")
        
        return contains_speaker_markers
    finally:
        release_db_connection(conn)

def run_test():
    """Exécute le test complet."""
    logger.info("=== DÉMARRAGE DU TEST ===")
    
    # Étape 1: Se connecter
    token = None
    try:
        token = login()
        if not token:
            logger.info("Tentative d'enregistrement de l'utilisateur...")
            register_user()
            token = login()
            
            if not token:
                logger.error("Impossible de se connecter, arrêt du test")
                return False
    except Exception as e:
        logger.error(f"Erreur lors de la connexion: {str(e)}")
        return False
    
    # Étape 2: Upload d'une réunion
    try:
        meeting = upload_meeting(token)
        if not meeting:
            logger.error("Échec de l'upload, arrêt du test")
            return False
        
        meeting_id = meeting.get("id")
        user_id = meeting.get("user_id")
        
        if not meeting_id or not user_id:
            logger.error("Informations de réunion incomplètes, arrêt du test")
            return False
    except Exception as e:
        logger.error(f"Erreur lors de l'upload: {str(e)}")
        return False
    
    # Étape 3: Attendre que la transcription soit terminée
    try:
        completed_meeting = check_meeting_status(token, meeting_id)
        if not completed_meeting:
            logger.error("La transcription n'a pas été complétée dans le délai imparti")
            return False
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du statut: {str(e)}")
        return False
    
    # Étape 4: Vérifier si la transcription contient des marqueurs de locuteurs
    try:
        has_speaker_markers = check_transcript_in_database(meeting_id, user_id)
        
        if has_speaker_markers:
            logger.info("✅ TEST RÉUSSI: La transcription contient bien des marqueurs de locuteurs")
            return True
        else:
            logger.error("❌ TEST ÉCHOUÉ: La transcription ne contient pas de marqueurs de locuteurs")
            return False
    except Exception as e:
        logger.error(f"Erreur lors de la vérification de la transcription: {str(e)}")
        return False

if __name__ == "__main__":
    success = run_test()
    
    if success:
        logger.info("=== TEST TERMINÉ AVEC SUCCÈS ===")
        sys.exit(0)
    else:
        logger.error("=== TEST TERMINÉ AVEC ÉCHEC ===")
        sys.exit(1)
