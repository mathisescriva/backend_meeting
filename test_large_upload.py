import requests
import os
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8001"
AUDIO_FILE_PATH = "/Users/mathisescriva/CascadeProjects/MeetingTranscriberBackend/audio_3h.mp3"
LOG_FILE = f"test_logs/large_upload_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Créer le dossier de logs s'il n'existe pas
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def log(message, level="INFO"):
    """Écrire un message dans le fichier de log et l'afficher dans la console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] [{level}] {message}"
    print(formatted_message)
    
    with open(LOG_FILE, "a") as f:
        f.write(formatted_message + "\n")

def login():
    """Se connecter à l'API et récupérer un token"""
    log("\n===== AUTHENTIFICATION =====")
    
    url = f"{BASE_URL}/auth/login/json"
    data = {
        "email": "test@example.com",
        "password": "password123"
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        response_data = response.json()
        
        log(f"Status code: {response.status_code}")
        log(f"Response: {json.dumps(response_data, indent=2)}")
        
        if response.status_code == 200 and "access_token" in response_data:
            log("✅ Authentification réussie")
            return response_data["access_token"]
        else:
            log("❌ Échec d'authentification", "ERROR")
            return None
    except Exception as e:
        log(f"❌ Erreur lors de l'authentification: {str(e)}", "ERROR")
        return None

def upload_large_audio(token):
    """Tester l'upload d'un fichier audio volumineux"""
    log("\n===== TEST D'UPLOAD D'UN FICHIER AUDIO VOLUMINEUX =====")
    log(f"Fichier: {AUDIO_FILE_PATH}")
    log(f"Taille: {os.path.getsize(AUDIO_FILE_PATH) / (1024 * 1024):.2f} Mo")
    
    url = f"{BASE_URL}/simple/meetings/upload"
    headers = {"Authorization": f"Bearer {token}"}
    
    start_time = time.time()
    
    try:
        with open(AUDIO_FILE_PATH, "rb") as f:
            files = {"file": (os.path.basename(AUDIO_FILE_PATH), f)}
            log("Début de l'upload...")
            response = requests.post(url, files=files, headers=headers, timeout=300)  # Timeout plus long pour les gros fichiers
        
        end_time = time.time()
        duration = end_time - start_time
        log(f"Durée de l'upload: {duration:.2f} secondes")
        
        response_data = response.json()
        log(f"Status code: {response.status_code}")
        log(f"Response: {json.dumps(response_data, indent=2)}")
        
        success = response.status_code == 200 and "id" in response_data
        if success:
            log("✅ Upload réussi")
            meeting_id = response_data["id"]
            log(f"ID de la réunion créée: {meeting_id}")
            return meeting_id, response_data
        else:
            log("❌ Échec de l'upload", "ERROR")
            return None, response_data
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        log(f"Durée avant erreur: {duration:.2f} secondes")
        log(f"❌ Erreur lors de l'upload: {str(e)}", "ERROR")
        return None, {"error": str(e)}

def check_meeting_status(token, meeting_id, max_checks=10, interval=30):
    """Vérifier le statut de la transcription d'une réunion"""
    log(f"\n===== SUIVI DU STATUT DE LA TRANSCRIPTION (ID: {meeting_id}) =====")
    
    url = f"{BASE_URL}/simple/meetings/{meeting_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    for i in range(max_checks):
        try:
            log(f"Vérification {i+1}/{max_checks}...")
            response = requests.get(url, headers=headers, timeout=10)
            response_data = response.json()
            
            status = response_data.get("transcript_status", "unknown")
            log(f"Statut actuel: {status}")
            log(f"Détails: {json.dumps({k: v for k, v in response_data.items() if k in ['transcript_status', 'transcription_status', 'duration_seconds', 'speakers_count']}, indent=2)}")
            
            if status in ["completed", "error"]:
                log(f"Statut final: {status}")
                return status, response_data
            
            if i < max_checks - 1:
                log(f"Attente de {interval} secondes avant la prochaine vérification...")
                time.sleep(interval)
        except Exception as e:
            log(f"❌ Erreur lors de la vérification du statut: {str(e)}", "ERROR")
    
    log("Nombre maximum de vérifications atteint sans statut final", "WARNING")
    return "timeout", None

def main():
    # Démarrer le test
    log(f"\n{'='*50}")
    log(f"DÉBUT DU TEST D'UPLOAD DE FICHIER VOLUMINEUX - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"{'='*50}\n")
    
    # Vérifier que le fichier audio existe
    if not os.path.exists(AUDIO_FILE_PATH):
        log(f"❌ Fichier audio non trouvé: {AUDIO_FILE_PATH}", "ERROR")
        return
    
    # Se connecter
    token = login()
    if not token:
        log("Impossible de continuer sans token d'authentification", "ERROR")
        return
    
    # Uploader le fichier audio
    meeting_id, upload_data = upload_large_audio(token)
    if not meeting_id:
        log("Impossible de continuer sans ID de réunion", "ERROR")
        return
    
    # Vérifier le statut de la transcription
    status, meeting_data = check_meeting_status(token, meeting_id, max_checks=20, interval=60)
    
    # Résumé du test
    log(f"\n{'='*50}")
    log(f"RÉSUMÉ DU TEST:")
    log(f"  Fichier: {os.path.basename(AUDIO_FILE_PATH)}")
    log(f"  Taille: {os.path.getsize(AUDIO_FILE_PATH) / (1024 * 1024):.2f} Mo")
    log(f"  ID de réunion: {meeting_id}")
    log(f"  Statut final: {status}")
    if meeting_data and "duration_seconds" in meeting_data:
        log(f"  Durée détectée: {meeting_data['duration_seconds']} secondes ({meeting_data['duration_seconds']/60:.1f} minutes)")
    if meeting_data and "speakers_count" in meeting_data:
        log(f"  Nombre de locuteurs: {meeting_data['speakers_count']}")
    log(f"{'='*50}\n")
    
    log(f"Rapport détaillé: {LOG_FILE}")

if __name__ == "__main__":
    main()
