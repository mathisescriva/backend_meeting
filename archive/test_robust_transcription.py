import requests
import time
import os
import sys
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test-transcription")

# Paramètres
API_URL = "http://localhost:8001"
USERNAME = "test@example.com"
PASSWORD = "password123"
MAX_CHECKS = 20  # Nombre maximal de vérifications
CHECK_INTERVAL = 15  # Intervalle entre les vérifications (secondes)

def test_transcription(audio_file_path):
    """Test complet du processus de transcription"""
    # Vérifier que le fichier existe
    if not os.path.exists(audio_file_path):
        logger.error(f"Le fichier {audio_file_path} n'existe pas")
        return False
    
    # 1. Connexion à l'API
    logger.info("Connexion à l'API...")
    login_data = {
        'username': USERNAME,
        'password': PASSWORD
    }
    login_response = requests.post(f"{API_URL}/auth/login", data=login_data)
    
    if login_response.status_code != 200:
        logger.error(f"Erreur de connexion: {login_response.status_code} - {login_response.text}")
        return False
    
    token = login_response.json()['access_token']
    logger.info("Connecté avec succès")
    
    # 2. Upload du fichier audio
    logger.info(f"Upload du fichier: {os.path.basename(audio_file_path)}")
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    with open(audio_file_path, 'rb') as f:
        files = {'file': (os.path.basename(audio_file_path), f)}
        upload_response = requests.post(f"{API_URL}/simple/meetings/upload", headers=headers, files=files)
    
    if upload_response.status_code != 200:
        logger.error(f"Erreur d'upload: {upload_response.status_code} - {upload_response.text}")
        return False
    
    meeting_id = upload_response.json().get('id')
    logger.info(f"Réunion créée avec succès, ID: {meeting_id}")
    
    # 3. Vérification périodique du statut
    for check_num in range(1, MAX_CHECKS + 1):
        logger.info(f"\nVérification {check_num}/{MAX_CHECKS}")
        logger.info(f"Vérification du statut de la réunion {meeting_id}")
        
        meeting_response = requests.get(f"{API_URL}/simple/meetings/{meeting_id}", headers=headers)
        
        if meeting_response.status_code != 200:
            logger.error(f"Erreur lors de la vérification: {meeting_response.status_code} - {meeting_response.text}")
            continue
        
        meeting_data = meeting_response.json()
        status = meeting_data.get('transcript_status')
        transcript_id = meeting_data.get('transcript_id')
        
        logger.info(f"Statut actuel: {status}")
        logger.info(f"ID de transcription: {transcript_id}")
        
        # Si la transcription est terminée ou en erreur
        if status == 'completed':
            logger.info("Transcription terminée avec succès!")
            transcript_text = meeting_data.get('transcript_text', '')
            logger.info(f"\nExtrait de la transcription:\n{transcript_text[:500]}..." if len(transcript_text) > 500 else f"\nTranscription:\n{transcript_text}")
            return True
        elif status == 'error':
            logger.error(f"Erreur lors de la transcription: {meeting_data.get('transcript_text')}")
            return False
        
        # Si toujours en cours, attendre avant la prochaine vérification
        logger.info(f"En attente de la transcription... (prochaine vérification dans {CHECK_INTERVAL}s)")
        time.sleep(CHECK_INTERVAL)
    
    logger.warning(f"Nombre maximal de vérifications atteint ({MAX_CHECKS}). La transcription est peut-être toujours en cours.")
    return False

# Test de robustesse - Essayer plusieurs fois avec des intervalles croissants
def test_robustness(audio_file_path, max_attempts=3):
    """Test de robustesse avec plusieurs tentatives"""
    for attempt in range(1, max_attempts + 1):
        logger.info(f"\n=== TENTATIVE {attempt}/{max_attempts} ===")
        
        try:
            result = test_transcription(audio_file_path)
            if result:
                logger.info(f"\n✅ Test réussi à la tentative {attempt}")
                return True
            else:
                logger.warning(f"\n❌ Échec à la tentative {attempt}")
        except Exception as e:
            logger.error(f"Exception lors de la tentative {attempt}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Attendre plus longtemps entre chaque tentative
        if attempt < max_attempts:
            wait_time = 30 * attempt  # 30s, 60s, 90s, etc.
            logger.info(f"Attente de {wait_time}s avant la prochaine tentative...")
            time.sleep(wait_time)
    
    logger.error(f"\n❌ Échec après {max_attempts} tentatives")
    return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
    else:
        audio_file = "Audio7min.mp3"  # Fichier par défaut
    
    logger.info(f"Test de robustesse avec le fichier: {audio_file}")
    test_robustness(audio_file)
